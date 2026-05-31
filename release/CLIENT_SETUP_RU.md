# Инструкция для администратора MSLaunch

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

## Если клиент прислал архив без версии

Сначала проанализируйте архив, не копируя его в `server_pack`:

```powershell
python tools\inspect_client_pack.py --archive "C:\Users\Li2Fox\Downloads\mods.rar" --output release\client_pack_report.md
```

Инструмент не запускает Minecraft и не исполняет `.jar`. Он только распаковывает архив во временную папку и читает metadata модов.

Если нужно аккуратно перенести найденные `mods`, `config`, `resourcepacks` в `server_pack`:

```powershell
python tools\inspect_client_pack.py --archive "C:\Users\Li2Fox\Downloads\mods.rar" --output release\client_pack_report.md --extract-to server_pack
```

Флаг `--clean` используйте только если специально хотите очистить `server_pack/mods`, `server_pack/config`, `server_pack/resourcepacks` перед копированием.

Если `.rar` не открылся, установите 7-Zip/WinRAR/UnRAR или попросите клиента прислать `.zip`.

Если версия или loader остались `unknown`, спросите у клиента:

- точную версию Minecraft;
- loader: Fabric, Forge, NeoForge или vanilla;
- нужен ли Fabric API.

После анализа можно подготовить `server_pack` из архива:

```powershell
python tools\prepare_client_server_pack.py --archive "C:\Users\Li2Fox\Downloads\mods.rar" --output-dir server_pack --base-url https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher --build-name "Nukem Project" --server play.domain.com --port 25565
```

Если версия или loader не определились уверенно, укажите их только после подтверждения клиента:

```powershell
python tools\prepare_client_server_pack.py --archive "C:\Users\Li2Fox\Downloads\mods.rar" --output-dir server_pack --base-url https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher --minecraft-version 1.20.1 --loader fabric --build-name "Nukem Project"
```

Текущий релиз лаунчера поддерживает подготовку релиза только для `vanilla` и `fabric`. Если архив похож на Forge или NeoForge, не выпускайте сборку без отдельного прохода разработки.

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

## GitHub-хостинг сборки

Рекомендуемый вариант для клиента: отдельный публичный GitHub-репозиторий только под сборку:

```text
mslauncher/
  build.json
  manifest.json
  mods/
  config/
  resourcepacks/
```

Для GitHub используйте raw-ссылку:

```powershell
python generate_manifest.py --base-dir server_pack --base-url https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher --minecraft-version 1.20.1 --loader fabric --server play.domain.com --port 25565
```

В `launcher_config.json` лучше указать полный raw `source_key`:

```json
"source_key": "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json"
```

Короткий вариант `"source_key": "domain.com"` для GitHub не подходит. Он нужен для обычного хостинга, где `build.json` лежит ровно по адресу `https://domain.com/mslauncher/build.json`.

Теоретический риск: публичный GitHub не скрывает файлы. Если человек получит raw-ссылку, он сможет скачать файлы напрямую. Пароль в лаунчере - это только client-side барьер в UI, чтобы случайные пользователи не скачивали сборку через кнопку лаунчера. Настоящая защита требует private repo, backend, token или signed URLs.

## Уведомление об обновлении лаунчера

В remote `build.json` можно добавить поля:

```json
{
  "launcher_version": "1.9.1",
  "launcher_download_url": "https://github.com/OWNER/REPO/releases/download/v1.9.1/MSLauncher.zip",
  "launcher_sha256": "optional_64_hex_sha256",
  "launcher_notes": "Short update note"
}
```

Если `launcher_version` больше текущей версии лаунчера, игрок увидит сообщение “Вышло обновление” и кнопку скачивания.

Важно:

- автообновления пока нет;
- лаунчер не скачивает `.exe` в фоне;
- игрок скачивает новую версию вручную;
- `launcher_download_url` должен быть HTTPS;
- `launcher_sha256` пока reserved/informational, но если поле заполнено, оно должно быть 64 hex-символа.

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

## Режим лаунчера и кнопки ссылок

По умолчанию лаунчер запускается как независимый:

```json
"client_mode": "independent"
```

В этом режиме ссылки проекта не показываются.

Для режима заказчика можно указать:

```json
"client_mode": "nukem",
"social_links": {
  "nukem": {
    "youtube": "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98",
    "discord": "https://discord.com/invite/P35nvXQ"
  }
}
```

Пустые ссылки не отображаются. Если ссылка не нужна, оставьте ее пустой или удалите строку.

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
