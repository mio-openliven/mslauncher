# Release Checklist

Перед передачей клиенту проверьте:

- [ ] В `launcher_config.json` заполнен `source_key`.
- [ ] Сервер открывает `https://.../mslauncher/build.json`.
- [ ] `manifest.json` открывается в браузере.
- [ ] Все файлы из `manifest.json` скачиваются по HTTPS.
- [ ] Лаунчер скачивает чистую сборку в server-профиль.
- [ ] Minecraft запускается.
- [ ] Кнопка crash-reports открывает папку отчетов.
- [ ] Проверено на Windows без Python.
- [ ] Игрокам передается вся папка `dist\MSLauncher`, а не один `.exe`.
