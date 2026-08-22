"""Climate control feature switch."""

import logging

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.const import ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    CONF_CLIMATE_CONTROL_ENTITY_ID,
    CONF_CLIMATE_CONTROL_PRESET_CLEAR,
    CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
    CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
    CONF_CLIMATE_CONTROL_PRESET_SLEEP,
    DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR,
    DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
    DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
    DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP,
    AreaStates,
    MagicAreasEvents,
    MagicAreasFeatureInfoClimateControl,
    MagicAreasFeatures,
)
from custom_components.magic_areas.switch.base import SwitchBase

_LOGGER = logging.getLogger(__name__)


class ClimateControlSwitch(SwitchBase):
    """Switch to enable/disable climate control."""

    feature_info = MagicAreasFeatureInfoClimateControl()
    _attr_entity_category = EntityCategory.CONFIG

    preset_map: dict[str, str]
    climate_entity_id: str | None
    _applied_preset: str | None

    def __init__(self, area: MagicArea) -> None:
        """Initialize the Climate control switch."""

        SwitchBase.__init__(self, area)

        # The preset this switch last commanded. We only push a new preset when
        # the target for the current area state differs from this, which both
        # preserves a preset the user set by hand and applies the right one at
        # startup. None means we have not applied anything yet.
        self._applied_preset = None

        self.climate_entity_id = self.area.feature_config(
            MagicAreasFeatures.CLIMATE_CONTROL
        ).get(CONF_CLIMATE_CONTROL_ENTITY_ID, None)

        if not self.climate_entity_id:
            raise ValueError("Climate entity not set")

        self.preset_map = {
            AreaStates.CLEAR: self.area.feature_config(
                MagicAreasFeatures.CLIMATE_CONTROL
            ).get(
                CONF_CLIMATE_CONTROL_PRESET_CLEAR, DEFAULT_CLIMATE_CONTROL_PRESET_CLEAR
            ),
            AreaStates.OCCUPIED: self.area.feature_config(
                MagicAreasFeatures.CLIMATE_CONTROL
            ).get(
                CONF_CLIMATE_CONTROL_PRESET_OCCUPIED,
                DEFAULT_CLIMATE_CONTROL_PRESET_OCCUPIED,
            ),
            AreaStates.SLEEP: self.area.feature_config(
                MagicAreasFeatures.CLIMATE_CONTROL
            ).get(
                CONF_CLIMATE_CONTROL_PRESET_SLEEP, DEFAULT_CLIMATE_CONTROL_PRESET_SLEEP
            ),
            AreaStates.EXTENDED: self.area.feature_config(
                MagicAreasFeatures.CLIMATE_CONTROL
            ).get(
                CONF_CLIMATE_CONTROL_PRESET_EXTENDED,
                DEFAULT_CLIMATE_CONTROL_PRESET_EXTENDED,
            ),
        }

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, self.area_state_changed
            )
        )

        # Apply the current state's preset once we are added. After a restart
        # Magic Areas restores the area as occupied and fires a single
        # AREA_STATE_CHANGED with an empty delta (nothing transitioned), so the
        # switch never sees a clear->occupied edge; without this catch-up the
        # climate would stay on its pre-restart preset (e.g. away) indefinitely.
        # Deferred a tick so the presence sensor has restored area.states first;
        # the event handler is the backstop if the area state isn't ready yet.
        self.hass.loop.call_soon_threadsafe(self._schedule_apply_current_state)

    @callback
    def _schedule_apply_current_state(self, *args) -> None:
        """Schedule an async application of the current area state's preset."""
        self.hass.async_create_task(
            self.apply_current_state(), "magic_areas climate control initial preset"
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable control and immediately apply the current state's preset."""
        await super().async_turn_on(**kwargs)
        await self.apply_current_state()

    async def area_state_changed(self, area_id, states_tuple):
        """Handle area state change event."""

        if not self.is_on:
            self.logger.debug("%s: Control disabled. Skipping.", self.name)
            return

        if area_id != self.area.id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (event: %s/self: %s)",
                self.name,
                area_id,
                self.area.id,
            )
            return

        await self.apply_current_state()

    async def apply_current_state(self) -> None:
        """Apply the preset for the area's current state, if it changed.

        Magic Areas fires AREA_STATE_CHANGED on every tracked-sensor update,
        usually with an empty delta while the area stays occupied. Rather than
        keying off the delta, we track the preset this switch last commanded
        (`_applied_preset`) and only push a new one when the target for the
        current area state actually differs. That preserves a preset the user set
        by hand -- no-op events resolve to the same target we already applied, so
        we do nothing -- while still applying the right preset on genuine
        transitions and once at startup (when `_applied_preset` is still None).
        """

        if not self.is_on:
            return

        target_state = self._target_state()
        if target_state is None:
            return

        target_preset = self.preset_map[target_state]
        if not target_preset:
            return

        if target_preset == self._applied_preset:
            self.logger.debug(
                "%s: Preset already %s, leaving climate untouched.",
                self.name,
                target_preset,
            )
            return

        await self.apply_preset(target_state)

    def _target_state(self) -> str | None:
        """Return the area state whose preset should apply now, or None."""

        # Area clear takes precedence; the occupancy states don't matter then.
        if self.area.has_state(AreaStates.CLEAR):
            return AreaStates.CLEAR

        # Highest priority state that is active and has a preset configured.
        for p_state in (AreaStates.SLEEP, AreaStates.EXTENDED, AreaStates.OCCUPIED):
            if self.area.has_state(p_state) and self.preset_map[p_state]:
                return p_state

        return None

    async def apply_preset(self, state_name: str):
        """Set climate entity to given preset."""

        selected_preset: str = self.preset_map[state_name]

        try:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_PRESET_MODE,
                {
                    ATTR_ENTITY_ID: self.climate_entity_id,
                    ATTR_PRESET_MODE: selected_preset,
                },
            )
            self._applied_preset = selected_preset
        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            self.logger.error("%s: Error applying preset: %s", self.name, str(e))
