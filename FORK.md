# Why this fork exists

`martinemde/magic-areas` tracks `jseidl/magic-areas` and carries three patches
that are needed to run the integration on current Home Assistant. Upstream's
last release is 4.4.1 (Sept 2025).

Home Assistant is installed from *this* fork rather than upstream because a
HACS update from upstream silently reverts all three, and the first one stops
Magic Areas turning lights on anywhere.

| patch | files | upstream |
|---|---|---|
| threshold sensor `hass` kwarg on HA 2026.8 | `threshold.py` | PR #630 — **closed unmerged** |
| dispatcher subscriptions leaked on reload | `light.py`, `binary_sensor/presence.py` | PR #635 — **open** |
| climate preset not applied on startup | `switch/climate_control.py` | not submitted |

## Layout

- `main` tracks upstream and stays clean, so PR branches can be cut from it.
- `patched/4.4.x` is the deployed line: upstream's `4.4.1` tag plus the three
  patches as one commit each.
- Releases are cut from `patched/4.4.x`. Version `4.4.2` is this fork's, not
  upstream's.

## Rebasing onto a new upstream release

```bash
git fetch upstream --tags
git checkout -b patched/<new> <new-upstream-tag>
git cherry-pick <the three commits from patched/4.4.x>
```

Then bump `custom_components/magic_areas/manifest.json`, tag, and release.
Drop any patch whose PR has landed upstream — check #630 and #635 first.

## Verifying a deploy

The patches are grepable, which is the fastest check after any HACS update:

```bash
grep -c _THRESHOLD_ACCEPTS_HASS custom_components/magic_areas/threshold.py   # 2
grep -c async_on_remove          custom_components/magic_areas/light.py      # >=2
grep -c _applied_preset custom_components/magic_areas/switch/climate_control.py  # 6
```
