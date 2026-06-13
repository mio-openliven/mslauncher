# Release Checklist: public MSNukem client

Этот чеклист нужен перед передачей публичного MSNukem-клиента. Он не заменяет ревью Agent 1 / Ревизор и не переводит задачу в Done.

## 1. Исходные условия

- [ ] Выбран task ID релиза: `R-001` или следующий `R-*`, назначенный Agent 1.
- [ ] Релиз собирается как Nukem preset, не как generic MSLaunch.
- [ ] MVP/release lock активен: новые функции, mascot и UI-идеи не добавляются.
- [ ] `server_pack/build.json` и `server_pack/manifest.json` не менялись вручную.
- [ ] В релиз не попали plaintext passwords, API tokens, signing keys, VPS keys или customer secrets.
- [ ] Если клиент прислал архив, версия Minecraft и loader подтверждены через отчет или клиентом.
- [ ] Если архив похож на Forge/NeoForge, релиз остановлен до отдельного approved task ID.

## 2. GitHub hosting для modpack

- [ ] Для modpack используется отдельный публичный GitHub repository только с клиентскими файлами.
- [ ] В repository нет секретов, приватных ключей, реальных `.env` и личных аккаунтов.
- [ ] Структура repository:

```text
mslauncher/
  build.json
  manifest.json
  mods/
  config/
  resourcepacks/
```

- [ ] `build.json` открывается по raw HTTPS URL.
- [ ] `manifest.json` открывается по raw HTTPS URL.
- [ ] Файлы из `mods`, `config`, `resourcepacks` открываются по HTTPS URL из manifest.
- [ ] `source_key` в Nukem config указывает на полный raw URL:

```text
https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json
```

- [ ] Короткий `source_key` вида `domain.com` не используется для GitHub.
- [ ] Клиент понимает риск: public GitHub не скрывает файлы, password gate только блокирует скачивание через UI лаунчера.
- [ ] Если нужна настоящая защита файлов, релиз через public GitHub остановлен и отправлен Agent 0 / Штурман на решение.

## 3. Nukem config

- [ ] Для сборки используется `release/launcher_config.nukem.template.json`.
- [ ] `client_mode` равен `nukem`.
- [ ] `default_build` указывает на Nukem build.
- [ ] `builds[0].id` и `default_build` согласованы.
- [ ] `minecraft_version` заполнен.
- [ ] `loader` равен `fabric` или `vanilla`.
- [ ] `source_key` заменен с `OWNER/REPO/BRANCH` на реальный raw URL.
- [ ] Для R-004 `source_key` равен `https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json`.
- [ ] Для R-004 `panel.enabled` выключен в Nukem release template, чтобы player path не зависел от hosted active-build.
- [ ] `server` и `port` заполнены, если лаунчер должен подключать сервер.
- [ ] Nukem YouTube/Discord ссылки заполнены или намеренно оставлены пустыми.
- [ ] Если password gate включен, заполнен только SHA-256 hash, не plaintext password.
- [ ] Для R-004 начальный build password `NUKEN` представлен только SHA-256 hash `99c3a29b690abad0a97dd39f6ed9e783f42abb07050df51897cd907968adb1ce`.
- [ ] Если используются build-specific passwords, каждый build имеет свой hash.
- [ ] `admin_password_hash_sha256` не содержит plaintext password.

## 4. Installer/package checklist

- [ ] Перед сборкой проверено, что `launcher_config.json` будет заменен Nukem preset намеренно.
- [ ] Сборка запускается командой:

```powershell
.\release\prepare_release.ps1 -Preset nukem
```

- [ ] Скрипт создает папку:

```text
dist\MSLauncher
```

- [ ] В release folder есть `MSLauncher.exe`.
- [ ] В release folder есть `launcher_config.json`.
- [ ] В release folder есть `assets`.
- [ ] В release folder есть `docs`.
- [ ] В `docs` попали инструкции для клиента и игрока.
- [ ] Игрокам передается вся папка `dist\MSLauncher`, а не один `.exe`.
- [ ] Если создается `.zip`, архив содержит папку целиком и не теряет соседние файлы exe.
- [ ] Если публикуется launcher update notice, `launcher_download_url` ведет на HTTPS zip/package.
- [ ] Если указан `launcher_sha256`, он равен SHA-256 опубликованного zip/package и содержит 64 hex-символа.
- [ ] SmartScreen/Defender предупреждения ожидаемы для unsigned exe и не обходятся кодовыми трюками.

## 5. Documentation review only

Для `R-001` достаточно documentation review, если packaging files не менялись.

- [ ] `README.md` не противоречит этому checklist.
- [ ] `release/NUKEM_SETUP_RU.md` не противоречит этому checklist.
- [ ] `release/CLIENT_SETUP_RU.md` не противоречит этому checklist.
- [ ] `release/PLAYER_README_RU.txt` не обещает автозагрузку Java.
- [ ] `release/POST_RELEASE_BACKLOG_RU.md` остается post-release, не MVP work.

## 6. Smoke checks без Minecraft

- [ ] Во время автоматических проверок Minecraft не запускался.
- [ ] `.exe` был открыт только smoke-style без Play launch.
- [ ] Проверено, что Nukem mode загружается.
- [ ] Проверено, что Play/Mods требует пароль, если password gate включен.
- [ ] Проверено, что Settings/Help открываются без ошибки.
- [ ] Проверено, что кнопки YouTube/Discord видны только в Nukem mode.
- [ ] Проверено, что ошибка без Java понятна игроку.
- [ ] Проверено, что ошибка плохого `source_key` короткая и пишет technical report.
- [ ] Проверено, что failed sync не портит уже существующие файлы.
- [ ] Проверено, что hash mismatch показывает проблемный файл.

## 7. Чистая Windows / клиентская приемка

- [ ] Проверено на Windows без установленного Python.
- [ ] Java requirement подтвержден для выбранной версии Minecraft.
- [ ] На чистой машине лаунчер открывается из install-like папки.
- [ ] Runtime data создается вне install folder, если portable mode не включен.
- [ ] Portable mode проверен только если клиенту реально нужен `.portable`.
- [ ] Реальный запуск Minecraft/Fabric отмечен как manual check, не automation.
- [ ] Crash reports folder доступен через кнопку лаунчера после manual crash test.

## 8. Передача клиенту

- [ ] Клиент получает `dist\MSLauncher` или zip с этой папкой целиком.
- [ ] Клиент получает `docs\PLAYER_README_RU.txt`.
- [ ] Клиент получает объяснение, что public GitHub files are public.
- [ ] Клиент знает, что пароль надо хранить вне GitHub, а в config держать только hash.
- [ ] Клиент знает, что update notice не является auto-update.
- [ ] Последний отчет сборки обновлен, если был реальный release build.
- [ ] После handoff работа идет в Agent 1 / Ревизор на Review, не в Done.
