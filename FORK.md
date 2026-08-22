# Why this fork exists

`martinemde/magic-areas` tracks `jseidl/magic-areas` and carries the patches
needed to run the integration on this Home Assistant instance.

Upstream's last release is **4.4.1 (Sept 2025)**, but `main` has since
accumulated fixes that are merged and unreleased — so this fork is based on
upstream **`main`**, not on the 4.4.1 tag.

Home Assistant is installed from this fork rather than upstream because a HACS
update from upstream silently reverts every local patch, and one of them
previously stopped Magic Areas turning lights on anywhere.

## Patches carried

| patch | files | upstream |
|---|---|---|
| dispatcher subscriptions leaked on reload | `light.py`, `binary_sensor/presence.py` | PR #635 — **open** |
| climate preset not applied on startup | `switch/climate_control.py` | not submitted |

Carried previously and **now dropped**, because upstream fixed it on `main`:

| dropped patch | fixed upstream by |
|---|---|
| threshold sensor `hass` kwarg on HA 2026.8 | #632, which removed the kwarg outright after PR #630 was closed unmerged |

## Upstream fixes this build is here to pick up

Both are on `main` and in no upstream release:

- **#632** — threshold sensor creation on HA 2026.8.
- **#605** — areas stuck occupied after a restart.

## Layout

- `main` tracks upstream and stays clean, so PR branches can be cut from it.
- `patched/main` is the deployed line: upstream `main` plus the patches above,
  one commit each.
- `patched/4.4.x` is the previous line, off the `4.4.1` tag. Superseded.
- Releases are cut from `patched/main`. Versions `4.4.2` / `4.4.3` are this
  fork's, not upstream's — upstream `main` still declares 4.4.1.

## Rebasing onto newer upstream

```bash
git fetch upstream --tags
git checkout -b patched/<new> upstream/main     # or a new upstream tag
git cherry-pick <the patch commits from patched/main>
```

Then bump `custom_components/magic_areas/manifest.json`, tag, and release.
Check #635 first — if it has landed, drop that commit rather than carrying it.

## Verifying a deploy

Fastest check after any HACS update:

```bash
grep -c async_on_remove custom_components/magic_areas/light.py                    # >=2
grep -c async_on_remove custom_components/magic_areas/binary_sensor/presence.py   # >=5
grep -c _applied_preset custom_components/magic_areas/switch/climate_control.py   # 6
```

Upstream fixes this build depends on, which should survive any rebase:

```bash
grep -c _validate_state_consistency custom_components/magic_areas/binary_sensor/presence.py  # 2  (#605)
sed -n '125,140p' custom_components/magic_areas/threshold.py | grep -c hass=hass             # 0  (#632)
```
