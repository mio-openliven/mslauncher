# Nukem preset: передача клиенту

Этот preset нужен, чтобы быстро собрать лаунчер под проект Nukem:

```powershell
.\release\prepare_release.ps1 -Preset nukem
```

## Что уже настроено

`release/launcher_config.nukem.template.json` уже подготовлен для текущего Nukem fallback-релиза:

- `panel.enabled: true` и `panel.base_url` указывают на текущую панель MSLaunch;
- fallback `source_key` указывает на публичный `MSNukem` raw `build.json`;
- password gate включен и хранит только SHA-256 hash;
- видны YouTube, Discord, VK и RuTube ссылки Nukem.

Перед сборкой меняйте только то, что реально изменилось:

- `minecraft_version`, если клиентская сборка перешла на другую версию;
- `server` и `port`, если лаунчер должен сразу подключать сервер;
- `password_hash_sha256` и `project_access.nukem.build_passwords.main`, если меняется пароль сборки.

Текущий fallback `source_key`:

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
    "password_hash_sha256": "<sha256>",
    "build_passwords": {
      "main": "<same sha256>"
    },
    "password_hint": "Ask the project admin for the access password."
  }
}
```

Не храните plaintext пароль в конфиге. Вписывайте только SHA-256 hash.

Важно: публичный GitHub не скрывает файлы. Если человек получил raw-ссылку, он сможет скачать файлы напрямую. Password gate только блокирует скачивание через UI лаунчера. Настоящая защита требует private repo, backend, token или signed URLs.

## Проверка перед отдачей

- В сборке выбран `client_mode: nukem`.
- Видны YouTube, Discord, VK и RuTube кнопки Nukem.
- `source_key` указывает на raw GitHub `build.json`.
- `minecraft_version` заполнен.
- `password_hash_sha256` заполнен, если password gate включен.
- `project_access.nukem.build_passwords.main` совпадает с основным hash.
- `.\release\prepare_release.ps1 -Preset nukem` собирает `dist\MSLauncher`.

Игрокам отдавайте всю папку `dist\MSLauncher`, не один `.exe`.
