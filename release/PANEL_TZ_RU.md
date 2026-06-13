# MSLaunch Admin Panel: ТЗ и контракт

## Цель

Панель нужна как главный источник сборок и обновлений для MSLaunch/MS Nuckem. Игрок в лаунчере не выбирает версию Minecraft и не думает о составе модов: он вводит ник, проходит Nukem password gate, нажимает скачать моды и запуск. Панель решает, какая сборка активна сегодня.

## Роли

- `owner` (`li2fly`): видит все проекты, отчеты игроков, обновления лаунчера и управляет админами.
- `project_admin` (`SKELET` для MS Nuckem): управляет сборками своего проекта, загружает моды/config/resourcepacks, активирует нужную сборку.
- `viewer`: может смотреть статус, но не менять данные.

Пароли админов не хранятся открытым текстом. Первый админ создается локальной CLI-командой или через env, секреты в Git не попадают.

## Приоритет источников

1. Panel API.
2. GitHub fallback (`source_key`, GitHub release).

Для модов лаунчер сначала запрашивает активную сборку панели. Если панель выключена, недоступна или активной сборки нет, он использует текущий GitHub `source_key`.

Пароль не блокирует визуальный режим MS Nuckem. Игрок может выбрать Nukem и видеть дизайн/соцссылки, но секретные моды скачиваются только после нажатия `Скачать моды` и ввода кода конкретной активной сборки. `Играть` не должен тихо скачивать секретные файлы без кода.

Для обновления самого лаунчера логика такая же: panel update notice, затем fallback из build config/GitHub.

## API для лаунчера

Все ответы API отдаются как JSON. MVP-клиент использует только поля ниже; новые поля могут игнорироваться старым лаунчером. Если панель недоступна, возвращает `404` для активной сборки или отдает невалидный контракт, лаунчер должен перейти на GitHub fallback без запуска Minecraft.

### `GET /api/projects/{project}/active-build`

Возвращает активную сборку:

```json
{
  "project": "nukem",
  "build_id": "nukem-1-20-1",
  "name": "MS Nuckem 1.20.1",
  "minecraft_version": "1.20.1",
  "loader": "fabric",
  "loader_version": "latest",
  "manifest_url": "https://panel.example/api/projects/nukem/builds/nukem-1-20-1/manifest.json",
  "server": "",
  "port": "",
  "access_required": true,
  "launcher_version": "",
  "launcher_download_url": "",
  "launcher_sha256": "",
  "launcher_notes": ""
}
```

Модель активной сборки:

- `project`: slug проекта, например `nukem`.
- `build_id` / `id`: один и тот же ID сборки; `id` оставлен для совместимости с лаунчером.
- `name`: имя сборки для UI.
- `minecraft_version`: версия Minecraft.
- `loader`: только `vanilla` или `fabric`.
- `loader_version`: версия загрузчика или `latest`.
- `manifest_url`: ссылка на manifest; для закрытой сборки лаунчер использует ее только после password gate.
- `server`, `port`: опциональные параметры сервера.
- `access_required`: boolean, `true` если нужен пароль сборки.
- `source`: `panel`.
- `launcher_version`, `launcher_download_url`, `launcher_sha256`, `launcher_notes`: notice обновления лаунчера, пустые строки если notice нет.

Если активной сборки нет, API возвращает `404`, а лаунчер переключается на GitHub fallback.

### `POST /api/projects/{project}/builds/{build_id}/access`

Проверяет пароль конкретной сборки и возвращает временную ссылку на manifest:

```json
{
  "password": "build-code"
}
```

Ответ:

```json
{
  "manifest_url": "https://panel.example/api/projects/nukem/builds/nukem-1-20-1/manifest.json?access=...",
  "access_token": "..."
}
```

### `GET /api/projects/{project}/builds/{build_id}/manifest.json`

Возвращает manifest в текущем формате MSLaunch:

```json
{
  "version": 1,
  "generated_at": "2026-06-01T00:00:00+00:00",
  "files": [
    {
      "path": "mods/example.jar",
      "sha256": "...",
      "size": 123,
      "url": "https://panel.example/files/nukem/nukem-1-20-1/mods/example.jar"
    }
  ]
}
```

### `GET /api/launcher/update`

Возвращает notice обновления:

```json
{
  "enabled": true,
  "version": "1.9.1",
  "download_url": "https://...",
  "sha256": "...",
  "notes": "Что изменилось"
}
```

Если обновление выключено, возвращается `{"enabled": false}`.

### `POST /api/reports`

Лаунчер отправляет отчет игрока:

```json
{
  "project": "nukem",
  "build_id": "nukem-1-20-1",
  "username": "Player",
  "launcher_version": "1.9.0",
  "error_type": "sync_failed",
  "user_message": "Не удалось скачать файлы",
  "technical_details": "..."
}
```

Панель сохраняет отчет для `owner`/админа.

## Модель данных MVP

`users`:

- `username`, `password_hash`, `role`, `project_slug`, `active`, `created_at`.
- Роли: `owner`, `project_admin`, `viewer`.
- `project_admin` и `viewer` ограничены своим `project_slug`.

`projects`:

- `slug`, `name`, `fallback_source_key`, `support_url`, `created_at`.
- На MVP активен `nukem`; `vibecraft` остается placeholder.

`builds`:

- `project_slug`, `build_id`, `name`, `minecraft_version`, `loader`, `loader_version`, `server`, `port`.
- `access_hash_sha256`: SHA-256 от пароля конкретной сборки или пусто.
- `status`: `draft`, `active`, `archived`; активная сборка одна на проект.
- `file_count`, `total_size`, `created_by`, `created_at`, `activated_at`.

`launcher_updates`:

- `version`, `download_url`, `sha256`, `notes`, `enabled`, `created_at`.
- Активным считается последний `enabled=1`.

`reports`:

- `project`, `build_id`, `username`, `launcher_version`, `error_type`, `user_message`, `technical_details`.
- `status`: `open` или `resolved`.

## UI панели MVP

- Login.
- Dashboard: активные сборки, последний manifest, количество отчетов.
- Builds: создать сборку, загрузить `.zip`, активировать, архивировать.
- Updates: включить/выключить обновление лаунчера.
- Reports: список отчетов, просмотр деталей, `open/resolved`.
- Admins: только `owner`, создание/деактивация админов и смена ролей.

Дизайн простой: темная рабочая панель, таблицы, статусы, крупные кнопки. Без маркетингового hero.

## Upload

MVP принимает `.zip` с корнями `mods/`, `config/`, `resourcepacks/`. Файлы вне этих корней, абсолютные пути и `..` отклоняются. `.rar` можно добавить через внешний `7z` позже; сейчас безопасный путь для клиента - распаковать rar в папку и собрать zip с теми же корнями.

## Безопасность

- Админские пароли: bcrypt, если установлен; fallback PBKDF2 для dev.
- Session cookie подписывается секретом `MSLAUNCH_PANEL_SECRET`.
- Upload paths проходят проверку.
- Секреты и локальные пароли пишутся только в ignored local files/env.
- Публичный GitHub fallback не защищает файлы. Настоящая защита - панель/private storage/token/signed URLs.

## Запуск локально

```powershell
pip install -r requirements.txt
$env:MSLAUNCH_PANEL_SECRET="change-me"
python -m admin_panel.cli init-db
python -m admin_panel.cli create-user --username li2fly --role owner
python -m admin_panel.app
```

По умолчанию панель слушает `127.0.0.1:8765`, данные лежат в `panel_data/`.
