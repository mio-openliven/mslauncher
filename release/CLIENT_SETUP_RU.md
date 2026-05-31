# Быстрая настройка клиента

## 1. Заполнить конфиг лаунчера

Откройте `launcher_config.json` или `release/launcher_config.template.json`.

Замените placeholders:

- `source_key`: домен, где лежит `https://ВАШ-ДОМЕН/mslauncher/build.json`.
- `server`: IP или домен Minecraft-сервера.
- `port`: порт Minecraft-сервера.
- `minecraft_version`: версия сборки, например `1.20.1`.
- `loader`: `fabric` или `vanilla`.

Если файлы лежат так:

```text
https://domain.com/mslauncher/build.json
```

то можно указать коротко:

```json
"source_key": "domain.com"
```

## 2. Подготовить сборку

Положите файлы сюда:

- моды: `server_pack/mods`
- конфиги: `server_pack/config`
- ресурспаки, модельки, текстуры: `server_pack/resourcepacks`

Сгенерируйте `manifest.json` и `build.json`:

```powershell
python generate_manifest.py --base-dir server_pack --base-url https://domain.com/mslauncher --minecraft-version 1.20.1 --loader fabric --server play.domain.com --port 25565
```

Загрузите содержимое `server_pack` на хостинг так, чтобы открывались:

```text
https://domain.com/mslauncher/build.json
https://domain.com/mslauncher/manifest.json
https://domain.com/mslauncher/mods/...
```

## 3. Собрать лаунчер

```powershell
.\build_exe.ps1
```

Готовая папка:

```text
dist\MSLauncher
```

## 4. Что отдать игрокам

Отдайте игрокам всю папку `dist\MSLauncher`.

Игрок запускает:

```text
MSLauncher.exe
```

Python игрокам не нужен.
