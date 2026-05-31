# Release Checklist

Перед передачей клиенту проверьте:

- [ ] В `launcher_config.json` заполнен `source_key`.
- [ ] Если сборка лежит на GitHub, используется полный raw `source_key`.
- [ ] Если включен password gate, клиент понимает: публичный GitHub не скрывает файлы, это только UI-барьер.
- [ ] Сервер открывает `https://.../mslauncher/build.json`.
- [ ] `manifest.json` открывается в браузере.
- [ ] Все файлы из `manifest.json` скачиваются по HTTPS.
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
