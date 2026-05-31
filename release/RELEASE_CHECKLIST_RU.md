# Release Checklist

Перед передачей клиенту проверьте:

- [ ] В `launcher_config.json` заполнен `source_key`.
- [ ] Если сборка лежит на GitHub, используется полный raw `source_key`.
- [ ] Если включен password gate, клиент понимает: публичный GitHub не скрывает файлы, это только UI-барьер.
- [ ] Сервер открывает `https://.../mslauncher/build.json`.
- [ ] `manifest.json` открывается в браузере.
- [ ] Все файлы из `manifest.json` скачиваются по HTTPS.
- [ ] Если клиент прислал архив без версии, создан `release\client_pack_report.md` через `python tools\inspect_client_pack.py`.
- [ ] Если сборка готовится из архива клиента, создан `release\client_pack_prepare_report.md` через `python tools\prepare_client_server_pack.py`.
- [ ] Если analyzer показал Forge/NeoForge, релиз остановлен до отдельного прохода поддержки.
- [ ] Если используется notice обновления, `build.json` содержит HTTPS `launcher_download_url`.
- [ ] Проверено: новая `launcher_version` показывает кнопку скачивания, старая/равная версия ничего не показывает.
- [ ] Для Nukem-релиза выбран `release/launcher_config.nukem.template.json`.
- [ ] Для Nukem-релиза заполнен `project_access.nukem.password_hash_sha256`, если password gate включен.
- [ ] Для Nukem-релиза raw GitHub `source_key` открывается в браузере.
- [ ] YouTube/Discord кнопки видны только в Nukem mode.
- [ ] Release folder проверен: `dist\MSLauncher\MSLauncher.exe`, `assets`, `launcher_config.json`, `docs`.
- [ ] Packaged config проверен: Nukem mode, social links, password gate, без plaintext password.
- [ ] `.exe` был запущен smoke-style без запуска Minecraft.
- [ ] Во время packaging check Minecraft не запускался.
- [ ] QA sync проходит без Minecraft:
  `python tools\qa_clean_sync_flow.py`.
- [ ] Лаунчер скачивает чистую сборку в server-профиль.
- [ ] Ошибка без интернета/source_key показывает короткое сообщение и создает technical report.
- [ ] Ошибка без Java понятно говорит, какую Java поставить или где указать `java.exe`.
- [ ] Hash mismatch не портит старые файлы и показывает имя проблемного файла.
- [ ] Minecraft запускается.
- [ ] Кнопка crash-reports открывает папку отчетов.
- [ ] Проверено на Windows без Python.
- [ ] Игрокам передается вся папка `dist\MSLauncher`, а не один `.exe`.
- [ ] После передачи: открыть `POST_RELEASE_BACKLOG_RU.md` и выбрать следующий этап.
