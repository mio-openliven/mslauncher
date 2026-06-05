# Последний отчет релизной сборки MSLaunch

Дата: 2026-06-05

Версия: `1.9.8`

Текущий release path: hosted setup + GitHub fallback.

## Публичные артефакты

- Public client: `https://mslaunch.186.246.12.238.sslip.io/client`
- Direct setup: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`
- Bootstrap: `https://mslaunch.186.246.12.238.sslip.io/downloads/bootstrap.json`
- Payload: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchPayload.dat`

## SHA-256

- `bootstrap.json`: `e066b63f350d444b656863433a7ed98fa8275aed845851bcc7e97c134d152392`
- `MSLaunchSetup.exe`: `7d2ae7c9cec048a9d2cf287445533162b458a9c865677193cf7ba827e983695c`
- `MSLaunchPayload.dat`: `91835ffbd508827ccdcc3bf66a37d9e06a6838a48c9ce304100f043c2e31b656`

## GitHub fallback

GitHub release: `mio-openliven/MSNukem`, tag `v1.9.8`.

The host and GitHub fallback assets must stay hash-consistent. Do not replace only one asset.

## Source state

- `main` includes PR #30 host upload safety.
- `main` includes PR #31 source label/version sync.
- `main` includes PR #32 team sync guardrails.
- Open PR list was empty at the last Agent 0 check.

## Checks

- `python tools\smoke_test_gui_offscreen.py`: OK
- `python tools\smoke_test_admin_panel.py`: OK
- `python tools\smoke_test_launcher_update.py`: OK
- `python tools\smoke_test_release_package.py`: OK
- Public `/client`: 200
- Public `/api/launcher/update`: must point to setup SHA `7d2ae7c9cec048a9d2cf287445533162b458a9c865677193cf7ba827e983695c` after host upload.
- Public `/api/projects/nukem/active-build`: 404, accepted for current fallback release.

## Not checked by automation

- Minecraft launch.
- Clean Windows/no-Python install.
- Antivirus/SmartScreen behavior.

## Do not use

Old `MSLaunch_Nukem_TestBuild.zip` reports from 2026-05-31 are historical and not current handoff truth.
