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

- `bootstrap.json`: `68de708d0e4403fc6729f310fc66284011bd5dcd19f94caf76598acc954eae66`
- `MSLaunchSetup.exe`: `7f2897f5eb7a93b6d707bac3d58546b56cf11e246a9e202bfdca77d1f2e82977`
- `MSLaunchPayload.dat`: `5247144f2df8657320524a2f0e3664ed388a7e1d25afcb9bd310ac1686fa7931`

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
- Public `/api/launcher/update`: must point to setup SHA `7f2897f5eb7a93b6d707bac3d58546b56cf11e246a9e202bfdca77d1f2e82977` after host upload.
- Public `/api/projects/nukem/active-build`: 404, accepted for current fallback release.

## Not checked by automation

- Minecraft launch.
- Clean Windows/no-Python install.
- Antivirus/SmartScreen behavior.

## Do not use

Old `MSLaunch_Nukem_TestBuild.zip` reports from 2026-05-31 are historical and not current handoff truth.
