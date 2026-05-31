# Финальный аудит MSLaunch

Дата: 2026-05-31 17:21:17 +02:00

Commit: `3823175 Verify Nukem release build`

Release folder: `C:\Users\Li2Fox\Documents\Лаунчер\dist\MSLauncher`

Release zip: `C:\Users\Li2Fox\Documents\Лаунчер\release\MSLaunch_Nukem_TestBuild.zip`

## Verdict

Demo/tester handoff: YES, как тестовая сборка с обязательной настройкой `source_key` и `password_hash_sha256` перед реальной проверкой сервера.

Commercial release: NO.

Progress: 100/100 по текущему 10-pass demo/release scope.

## Critical

- Нет critical blocker для передачи тестерам как demo/test package.
- Для реального серверного теста текущий packaged config еще не готов: `source_key` содержит placeholder `https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json`, а `password_hash_sha256` пустой. Это не баг сборки, но это blocker для plug-and-play запуска серверной сборки.

## High

- Реальный запуск Minecraft/Fabric не проверялся в этом финальном аудите. Без этого нельзя обещать production-ready запуск на машине клиента.
- Чистая Windows VM без Python не проверялась. PyInstaller folder build есть, но совместимость с чистой системой и антивирусами остается ручной проверкой.
- Password gate является client-side барьером. Его можно обойти при доступе к файлам/конфигу клиента.
- Public GitHub raw hosting не скрывает моды: любой человек с raw URL сможет скачать файлы напрямую.

## Medium

- `password_hash_sha256` в Nukem template пустой. При включенном password gate Play/Mods будут заблокированы до заполнения hash администратором.
- `launcher_download_url`/auto-update flow не является автообновлением. Реализовано только уведомление и ручная ссылка на скачивание.
- Java не поставляется вместе с лаунчером. На чистой Windows может потребоваться установка Java вручную или указание `java.exe`.
- Manual GUI clicks не были полностью пройдены в этом аудите: wrong-password dialog/settings/help panel визуально не кликались через автоматизацию.

## Low

- В Git status остаются локальные изменения `server_pack/build.json` и `server_pack/manifest.json`. Это generated modpack output, не исходники лаунчера; они намеренно не коммитятся в launcher repo.
- `dist/` и release zip не коммитятся. Это нормально: артефакты сборки лежат локально.

## Theoretical Risks

- theoretical: пользователь может изменить локальный config, отключить password gate или достать raw-ссылки из файлов.
- theoretical: публичные GitHub файлы могут быть скачаны сторонними людьми, если ссылка утечет.
- theoretical: Windows Defender/сторонние антивирусы могут ругаться на PyInstaller `.exe` без подписи.
- theoretical: отдельные Minecraft/Fabric версии могут требовать нюансы Java/loader, которые не покрыты smoke-тестами.
- theoretical: crash advisor может не распознать редкий конфликт модов и попросит отправить `latest.log`/crash report админу.

## What Was Verified

- `git status --short`: исходники чистые, кроме generated `server_pack/build.json` и `server_pack/manifest.json`.
- `git log -1 --oneline`: `3823175 Verify Nukem release build`.
- `python -m py_compile gui.py`: OK.
- Все `tools/smoke_test_*.py`: OK.
- `rg -n "[А-Яа-яЁё]" gui.py`: прямой кириллицы нет.
- Release folder содержит:
  - `dist\MSLauncher\MSLauncher.exe`;
  - `dist\MSLauncher\assets`;
  - `dist\MSLauncher\launcher_config.json`;
  - `dist\MSLauncher\docs`.
- Docs в release folder содержат:
  - `CLIENT_SETUP_RU.md`;
  - `PLAYER_README_RU.txt`;
  - `RELEASE_CHECKLIST_RU.md`;
  - `NUKEM_SETUP_RU.md`;
  - `POST_RELEASE_BACKLOG_RU.md`;
  - `LAST_BUILD_REPORT_RU.md`.
- Packaged config:
  - `client_mode = nukem`;
  - YouTube link заполнен;
  - Discord link заполнен;
  - plaintext password отсутствует;
  - `password_hash_sha256` пустой placeholder;
  - `source_key` HTTPS raw GitHub placeholder;
  - `http://` не найден;
  - GitHub token/secret markers не найдены.
- `MSLauncher.exe` был запущен smoke-style с отдельным `MSLAUNCHER_USER_DATA_ROOT`.
- Smoke-run создал user config с `client_mode=nukem`.
- Minecraft во время аудита не запускался.

## What Was Not Verified

- Реальный запуск Minecraft.
- Реальный Fabric launch на сборке клиента.
- Реальная синхронизация с будущим VDS/GitHub modpack repo клиента.
- Проверка на чистой Windows VM без Python.
- Поведение антивирусов и SmartScreen.
- Полный ручной GUI click-through в собранном `.exe`.
- Wrong-password dialog в packaged `.exe` с реальным hash, потому hash в тестовом config намеренно пустой.
- Microsoft auth/online-mode, потому эта функция не реализована.
- Bundled Java, потому Java не поставляется.

## Must Do Before Public Release

- Заменить placeholder `source_key` на реальный raw GitHub URL клиента.
- Заполнить `project_access.nukem.password_hash_sha256`, если password gate нужен.
- Проверить, что `build.json`, `manifest.json` и файлы из manifest открываются по HTTPS.
- Прогнать `python tools\qa_clean_sync_flow.py`.
- Проверить `.exe` на чистой Windows VM без Python.
- Проверить реальный запуск Minecraft/Fabric.
- Проверить сценарии: нет Java, hash mismatch, нет интернета, crash report после вылета.
- Решить вопрос подписи `.exe`, если сборка пойдет шире узкого теста.
- Не обещать скрытие модов при публичном GitHub hosting.

## Safe Handoff Instructions

- Тестерам отдавать всю папку `dist\MSLauncher` или архив `release\MSLaunch_Nukem_TestBuild.zip`, не один `.exe`.
- Перед реальным тестом сервера заполнить `source_key` и `password_hash_sha256`.
- Объяснить клиенту: публичный GitHub не защищает файлы, password gate только ограничивает случайное скачивание через UI.
- Для отчетов об ошибках просить игрока открыть logs/crash reports и отправить файл админу.
- Для production не обещать автообновление, Microsoft auth, встроенную Java или античит.
