# Инструкция для администратора MSLauncher

## Что делает лаунчер

Лаунчер не угадывает моды сам. Он читает `build.json`, получает из него ссылку на `manifest.json`, а потом сверяет файлы игрока по SHA-256.

Если файл устарел или отсутствует, лаунчер скачает его. Лишние моды в серверном профиле удаляются только после успешной проверки и загрузки нужных файлов.

## Папка сборки

Рабочая папка для обновления сборки:

```text
server_pack/
  mods/
  config/
  resourcepacks/
```

Куда класть файлы:

- моды `.jar` -> `server_pack/mods/`
- конфиги -> `server_pack/config/`
- ресурспаки, модельки, текстуры -> `server_pack/resourcepacks/`

## Как обновить моды

1. Положите новые моды в `server_pack/mods/`.
2. Положите конфиги в `server_pack/config/`.
3. Положите ресурспаки/модельки в `server_pack/resourcepacks/`.
4. Запустите команду генерации `manifest.json` и `build.json`.
5. Загрузите содержимое `server_pack` на сервер или хостинг.
6. Проверьте в браузере, что `build.json` и `manifest.json` открываются.

После каждого изменения файлов сборки команду генерации нужно запускать заново.

## Команда генерации

Пример:

```powershell
python generate_manifest.py --base-dir server_pack --base-url https://domain.com/mslauncher --minecraft-version 1.20.1 --loader fabric --server play.domain.com --port 25565
```

Что заменить:

- `https://domain.com/mslauncher` -> ссылка на папку сборки на вашем хостинге;
- `1.20.1` -> версия Minecraft;
- `fabric` -> `fabric` или `vanilla`;
- `play.domain.com` -> адрес Minecraft-сервера;
- `25565` -> порт сервера.

## Что должно открываться в браузере

После загрузки на хостинг должны открываться:

```text
https://domain.com/mslauncher/build.json
https://domain.com/mslauncher/manifest.json
https://domain.com/mslauncher/mods/...
https://domain.com/mslauncher/config/...
https://domain.com/mslauncher/resourcepacks/...
```

Важно: production-ссылки должны быть HTTPS. HTTP лаунчер не принимает.

## Что указать в launcher_config.json

Если сборка лежит здесь:

```text
https://domain.com/mslauncher/build.json
```

то в `launcher_config.json` достаточно указать:

```json
"source_key": "domain.com"
```

Лаунчер сам превратит это в:

```text
https://domain.com/mslauncher/build.json
```

Моды вручную в `launcher_config.json` прописывать не нужно.

## Как собрать exe

```powershell
.\build_exe.ps1
```

Готовая папка появится здесь:

```text
dist\MSLauncher
```

## Что отдать игрокам

Игрокам нужно отдать всю папку:

```text
dist\MSLauncher
```

Не отдавайте один `MSLauncher.exe` отдельно. Рядом с ним нужны служебные файлы, `assets`, `launcher_config.json` и папка `docs`.

## Частые ошибки

- `build.json` не открывается в браузере: проверьте домен, путь `/mslauncher/build.json` и загрузку файлов на хостинг.
- HTTP вместо HTTPS: используйте только `https://`.
- Забыли перегенерировать `manifest.json`: после изменения модов/конфигов запустите `generate_manifest.py` заново.
- Файл из `manifest.json` не скачивается: проверьте, что ссылка на конкретный файл открывается в браузере.
- Hash mismatch: файл на хостинге отличается от того, что был при генерации manifest. Перегенерируйте manifest и загрузите файлы заново.
- Не установлена Java: лаунчер попробует найти Java сам, но на чистой Windows может понадобиться установить Java или указать путь к `java.exe` в настройках.

## Быстрая проверка перед передачей

```powershell
python tools\qa_clean_sync_flow.py
```

Этот тест не запускает Minecraft. Он проверяет только генерацию серверной сборки, скачивание файлов и безопасную синхронизацию.
