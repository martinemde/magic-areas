# Why this fork exists

`martinemde/magic-areas` tracks `jseidl/magic-areas` and carries the patches
needed to run the integration on this Home Assistant instance.

Upstream released **4.4.2** on 2026-08-10; it is upstream `main` with nothing
but a version bump, so this fork's line already contained every line of it.
The fork stays based on upstream **`main`** rather than on a release tag,
because upstream tags lag `main` by months.

Home Assistant is installed from this fork rather than upstream because a HACS
update from upstream silently reverts every local patch, and one of them
previously stopped Magic Areas turning lights on anywhere.

## Patches carried

| patch | files | upstream |
|---|---|---|
| dispatcher subscriptions leaked on reload | `light.py`, `binary_sensor/presence.py` | PR #635 — **open** |
| climate preset not applied on startup | `switch/climate_control.py` | not submitted |
| meta-area features wiped on options update | `const.py` | PR #637 — **open** |

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
- Releases are cut from `patched/main`. Versions `4.4.2` / `4.4.3` / `4.4.4`
  are this fork's, not upstream's.

**Tag collision.** This fork's `4.4.2` tag and upstream's `4.4.2` tag are
different commits, so a fetch of both remotes leaves one of them unfetched:
`git fetch upstream --tags` reports `! [rejected] 4.4.2 (would clobber
existing tag)`. Whichever remote was fetched first wins locally. Read release
tags from GitHub (`gh release view <tag> -R martinemde/magic-areas`) rather
than trusting a local tag of that name. Fork versions from `4.4.3` on do not
collide.

## Rebasing onto newer upstream

```bash
jj git fetch --remote upstream
jj diff --from <patched/main's upstream base> --to <new upstream head> --stat
```

If that diff is empty of code — as upstream's 4.4.2 release was, a pure version
bump — there is nothing to rebase; add patches on top of `patched/main` and cut
a release. Otherwise duplicate the patch commits onto the new upstream head:

```bash
jj duplicate <patch commit> -d <new upstream head>
```

A released commit is immutable in jj and that refusal is correct — never
`--ignore-immutable` to rewrite a line that has already been tagged and
deployed. Cut a new version on top instead.

Then bump `custom_components/magic_areas/manifest.json`, tag, and release.
Check each open PR first — if one has landed upstream, drop that commit rather
than carrying it.

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
