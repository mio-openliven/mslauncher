# Последний отчет сборки MSLaunch

Дата: 2026-05-31 16:26:17 +02:00

Preset: `nukem`

Commit перед сборкой: `62b378e`

## Проверки перед сборкой

- `python -m py_compile gui.py`: OK
- `Get-ChildItem tools -Filter smoke_test_*.py | Sort-Object Name | ForEach-Object { python $_.FullName }`: OK
- `rg -n "[А-Яа-яЁё]" gui.py`: OK, совпадений нет

## Результат сборки

- Build script: `release\prepare_release.ps1 -Preset nukem`
- Release folder: `C:\Users\Li2Fox\Documents\Лаунчер\dist\MSLauncher`
- EXE: `C:\Users\Li2Fox\Documents\Лаунчер\dist\MSLauncher\MSLauncher.exe`
- Zip artifact: `C:\Users\Li2Fox\Documents\Лаунчер\release\MSLaunch_Nukem_TestBuild.zip`

## Проверка release folder

- `dist\MSLauncher\MSLauncher.exe`: OK
- `dist\MSLauncher\assets`: OK
- `dist\MSLauncher\launcher_config.json`: OK
- `dist\MSLauncher\docs`: OK
- `CLIENT_SETUP_RU.md`: OK
- `PLAYER_README_RU.txt`: OK
- `RELEASE_CHECKLIST_RU.md`: OK
- `POST_RELEASE_BACKLOG_RU.md`: OK
- `NUKEM_SETUP_RU.md`: OK

## Packaged config

- `client_mode`: `nukem`
- `social_links.nukem.youtube`: filled
- `social_links.nukem.discord`: filled
- `project_access.nukem.password_enabled`: `true`
- Plaintext password: not present
- `project_access.nukem.password_hash_sha256`: empty placeholder
- `source_key`: `https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json`

Важно: пока `password_hash_sha256` пустой, Nukem password gate будет блокировать Play/Mods и попросит администратора заполнить hash. Это правильно для test build без реального пароля.

## Smoke-run EXE

- `MSLauncher.exe` запущен smoke-style с отдельным `MSLAUNCHER_USER_DATA_ROOT`.
- Временный user config создан.
- Временный user config содержит `client_mode=nukem`.
- Minecraft во время проверки не запускался.

Manual clicks not done by automation:

- визуально подтвердить MSLaunch hero/title;
- проверить YouTube/Discord кнопки;
- нажать Play/Mods и убедиться, что password gate блокирует запуск до настройки hash;
- открыть settings/help;
- закрыть окно без ошибки.

## Ограничения

- Public GitHub files are public: raw links не скрывают моды.
- Password gate is client-side: это UI-барьер, не настоящая серверная защита.
- Java может потребоваться установить вручную.
- Реальный запуск Minecraft/Fabric еще нужно проверить вручную.
- Реальная HTTPS-ссылка клиента еще не указана.
