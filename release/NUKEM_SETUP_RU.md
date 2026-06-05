# Nukem preset: передача клиенту

Этот preset нужен, чтобы быстро собрать лаунчер под проект Nukem:

```powershell
.\release\prepare_release.ps1 -Preset nukem
```

## Что проверить перед сборкой

Откройте `release/launcher_config.nukem.template.json` и проверьте:

- `source_key` уже указывает на `mio-openliven/MSNukem`;
- `minecraft_version` после анализа архива клиента;
- `server` и `port`, если лаунчер должен сразу подключать сервер;
- `password_hash_sha256`, если включен password gate.

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
    "password_hash_sha256": "b49c430845403cc609360a61bf424ce7bd01bad57b1aadb6794c76dcd07be0ef",
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
- `password_hash_sha256` заполнен, если пароль нужен.
- `.\release\prepare_release.ps1 -Preset nukem` собирает `dist\MSLauncher`.

Игрокам отдавайте всю папку `dist\MSLauncher`, не один `.exe`.
