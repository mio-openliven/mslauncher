# Последний отчет релизной сборки MSLaunch

Дата: 2026-06-05

Версия: `1.9.7`

Текущий release path: hosted setup + GitHub fallback.

## Публичные артефакты

- Public client: `https://mslaunch.186.246.12.238.sslip.io/client`
- Direct setup: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`
- Bootstrap: `https://mslaunch.186.246.12.238.sslip.io/downloads/bootstrap.json`
- Payload: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchPayload.dat`

## SHA-256

- `bootstrap.json`: `38e21ae303a524f616fa39a2d8bdcae1ea9ca350739b5f313775780bb46f2971`
- `MSLaunchSetup.exe`: `166e36d6075787fe310fa45af1431e16dc7cb452133a54cd0d06c4d2922b04a3`
- `MSLaunchPayload.dat`: `c859a9338100f74d1a1f420c2f22209a4f0c4271f7b86170398dc08adb341c37`

## GitHub fallback

GitHub release: `mio-openliven/MSNukem`, tag `v1.9.7`.

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
- Public `/api/launcher/update`: 200, points to setup SHA `166e36d6075787fe310fa45af1431e16dc7cb452133a54cd0d06c4d2922b04a3`
- Public `/api/projects/nukem/active-build`: 404, accepted for current fallback release.

## Not checked by automation

- Minecraft launch.
- Clean Windows/no-Python install.
- Antivirus/SmartScreen behavior.

## Do not use

Old `MSLaunch_Nukem_TestBuild.zip` reports from 2026-05-31 are historical and not current handoff truth.
