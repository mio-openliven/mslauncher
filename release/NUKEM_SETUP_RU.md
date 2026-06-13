# Nukem preset: передача клиенту

Этот preset нужен, чтобы быстро собрать лаунчер под проект Nukem:

```powershell
.\release\prepare_release.ps1 -Preset nukem
```

## Что заменить перед сборкой

Для текущего R-004 GitHub fallback release в `release/launcher_config.nukem.template.json` уже заполнены:

- `source_key`: `https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json`;
- `minecraft_version`: `1.20.1`;
- `loader`: `fabric`;
- `password_hash_sha256`: SHA-256 для начального пароля `NUKEN`;
- `panel.enabled`: `false`, чтобы путь игрока шел напрямую через GitHub fallback.

Если меняется клиентская сборка, замените только подтвержденные release inputs:

- `source_key`;
- `minecraft_version`;
- `server` и `port`, если лаунчер должен сразу подключать сервер;
- `password_hash_sha256` и `build_passwords`, если меняется пароль.

Пример `source_key`:

```json
"source_key": "https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json"
```

Проверьте в браузере, что открывается:

```text
https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json
```

## Password gate

В preset есть блок:

```json
"project_access": {
  "nukem": {
    "password_enabled": true,
    "password_hash_sha256": "",
    "password_hint": "Ask the project admin for the access password."
  }
}
```

Не храните plaintext пароль в конфиге. Вписывайте только SHA-256 hash.

Важно: публичный GitHub не скрывает файлы. Если человек получил raw-ссылку, он сможет скачать файлы напрямую. Password gate только блокирует скачивание через UI лаунчера. Настоящая защита требует private repo, backend, token или signed URLs.

## Проверка перед отдачей

- В сборке выбран `client_mode: nukem`.
- Видны YouTube и Discord кнопки Nukem.
- `source_key` указывает на raw GitHub `build.json`.
- `minecraft_version` заполнен.
- `password_hash_sha256` и `build_passwords.nukem` заполнены для начального пароля `NUKEN`.
- `panel.enabled` выключен для player path; hosted panel active-build не нужен для первого actor test.
- `.\release\prepare_release.ps1 -Preset nukem` собирает `dist\MSLauncher`.

Игрокам отдавайте всю папку `dist\MSLauncher`, не один `.exe`.
