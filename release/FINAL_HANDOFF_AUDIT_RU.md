# Финальный аудит MSLaunch

Дата: 2026-06-05

Source truth: `main` после PR #30, #31, #32 и #34.

Текущий release path: hosted setup + GitHub fallback, версия `1.9.7`.

## Verdict

First-client handoff: YES, для текущего GitHub fallback release path.

Commercial wide release: NOT YET, пока не пройдены ручные проверки на чистой Windows и реальный запуск Minecraft/Fabric.

Progress: 95/100.

## Current Public Truth

- Public client: `https://mslaunch.186.246.12.238.sslip.io/client`
- Direct setup: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`
- Bootstrap SHA-256: `68de708d0e4403fc6729f310fc66284011bd5dcd19f94caf76598acc954eae66`
- Setup SHA-256: `7f2897f5eb7a93b6d707bac3d58546b56cf11e246a9e202bfdca77d1f2e82977`
- Payload SHA-256: `5247144f2df8657320524a2f0e3664ed388a7e1d25afcb9bd310ac1686fa7931`
- `/api/launcher/update`: must point to version `1.9.7` and setup SHA `7f2897f5eb7a93b6d707bac3d58546b56cf11e246a9e202bfdca77d1f2e82977` after host upload.
- `/api/projects/nukem/active-build`: `404 No active build`; accepted for the current fallback release path.

## Current Source Truth

- `launcher_update.APP_VERSION = "1.9.7"`.
- Launcher source label is `Release Beta 1.9.7`.
- Public panel eyebrow is `MS Nuckem Release Beta`.
- `TEAM_SYNC_MSLAUNCH.md` contains the current team route and release guardrail.
- Supported loaders in source/docs: `vanilla`, `fabric`, `quilt`, `neoforge`.

## Release Guardrails

- Do not rebuild or deploy only one public artifact for a cosmetic label change.
- If visible downloaded client label must change, route a full artifact-sync pass:
  payload rebuild, setup embedded SHA update, setup rebuild, bootstrap regeneration, host upload, GitHub fallback asset update, and hash verification.
- Do not touch `server_pack/build.json` or `server_pack/manifest.json` during release cleanup.
- Do not launch Minecraft in automated checks.
- Do not print or store secrets in GitHub or reports.

## What Was Verified

- `git status --short --branch`: clean `main`.
- Open GitHub PR list: empty.
- Public `/client`: 200.
- Public hosted setup/payload/bootstrap hashes match the release constants.
- `/api/launcher/update` no longer advertises the stale `d94...` setup hash.
- Local smoke checks on `main` passed:
  - `python tools\smoke_test_gui_offscreen.py`
  - `python tools\smoke_test_admin_panel.py`
  - `python tools\smoke_test_launcher_update.py`
  - `python tools\smoke_test_release_package.py`

## What Was Not Verified

- Real Minecraft launch.
- Real Fabric launch with the client's machine state.
- Clean Windows/no-Python install smoke.
- Antivirus/SmartScreen behavior.
- Panel-managed active build publishing through owner UI.

## Remaining Before Final Owner Sign-off

- Owner/customer manually tests install and launch on the target Windows machine.
- Team 2 watches only true release risks:
  - live endpoint drift;
  - update/report breakage;
  - package/hash mismatch;
  - P-007 if panel-managed active builds become required before handoff.

## Historical Notes

Older reports from 2026-05-31 described a demo zip with placeholder `source_key` and empty password hash. That is no longer the current release truth. Use this file and `TEAM_SYNC_MSLAUNCH.md` for current routing.
