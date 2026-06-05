# Финальный аудит MSLaunch

Дата: 2026-06-05

Source truth: `main` после PR #30, #31 и #32.

Текущий release path: hosted setup + GitHub fallback, версия `1.9.7`.

## Verdict

First-client handoff: YES, для текущего GitHub fallback release path.

Commercial wide release: NOT YET, пока не пройдены ручные проверки на чистой Windows и реальный запуск Minecraft/Fabric.

Progress: 94/100.

## Current Public Truth

- Public client: `https://mslaunch.186.246.12.238.sslip.io/client`
- Direct setup: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`
- Bootstrap SHA-256: `38e21ae303a524f616fa39a2d8bdcae1ea9ca350739b5f313775780bb46f2971`
- Setup SHA-256: `166e36d6075787fe310fa45af1431e16dc7cb452133a54cd0d06c4d2922b04a3`
- Payload SHA-256: `c859a9338100f74d1a1f420c2f22209a4f0c4271f7b86170398dc08adb341c37`
- `/api/launcher/update`: `200`, version `1.9.7`, setup SHA matches current public setup.
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
