# MSLaunch Owner Handoff

Дата: 2026-06-05

Этот файл можно использовать как чеклист выдачи доступа. Он не содержит паролей.

## Карта доступов

| Кому | Что дать | Откуда брать значение |
| --- | --- | --- |
| Актеры / игроки | client/setup link + пароль сборки Nukem | Link ниже; пароль Nukem назначен владельцем проекта и передается приватно |
| Заказчик / Скелет | panel login + panel password | Owner/admin создает или reset-ит аккаунт в `/admins` |
| Владелец | owner/admin panel login | Существующий owner login панели; если потерян, восстановить серверным maintenance-действием |
| Будущая команда фиксов | private GitHub repo access | Добавить GitHub account в collaborators, без паролей панели/SSH |

Agent 0 в текущем release pass:

- не менял пароль Nukem;
- не создавал и не менял panel-login Скелета;
- не печатал и не коммитил реальные пароли;
- менял только live update metadata/hash и серверные файлы панели после 502.

## Актерам / игрокам

Дать:

- Страница клиента: `https://mslaunch.186.246.12.238.sslip.io/client`
- Прямая загрузка setup: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`
- Проект: `MS Nuckem`
- Пароль сборки: текущий пароль Nukem, передать приватно, не через GitHub и не в публичных чатах.

Ожидаемое поведение:

- Если лаунчер уже версии `1.9.7`, он может показать `Обновлений нет`; это нормально.
- Download Mods / Play для Nukem идет через password gate и sync.
- Если панель активной сборки еще не настроена, текущий release path использует GitHub fallback.

## Заказчику / Скелету

Дать:

- Вход в панель: `https://mslaunch.186.246.12.238.sslip.io/login`
- Управление сборками: `https://mslaunch.186.246.12.238.sslip.io/builds`
- Отчеты игроков: `https://mslaunch.186.246.12.238.sslip.io/reports`
- Админы панели: `https://mslaunch.186.246.12.238.sslip.io/admins`
- Логин панели: передать приватно.
- Пароль панели: передать приватно.

Важно:

- Agent 0 не менял пароль панели в текущем release pass.
- Agent 0 не печатает и не коммитит реальные пароли.
- Если нужен новый пароль для заказчика, владелец или owner-admin должен создать/reset admin в панели или отдельным серверным maintenance-действием.
- Если owner-login панели потерян, Team 2 должна делать только серверный admin reset через `python -m admin_panel.cli create-user --username <owner> --role owner` с вводом пароля в скрытый prompt. Не использовать `--print-password` и не писать пароль в GitHub.

## Владельцу

Проверить центральную панель:

1. Открыть `https://mslaunch.186.246.12.238.sslip.io/login`.
2. Войти owner/admin-логином.
3. Проверить `/builds`: создание/активация сборки.
4. Проверить `/reports`: приходят ли отчеты игроков.
5. Проверить `/admins`: есть ли нужный аккаунт заказчика.
6. Если аккаунта заказчика нет: создать `project_admin` для проекта `nukem`, задать пароль и передать его Скелету приватно.
7. Если актеры должны качать через панельную активную сборку, создать build в `/builds`, указать Minecraft version, loader, ZIP модов или ссылку, build password, затем активировать build.

## Будущей команде фиксов

Работать через приватный GitHub-репозиторий:

- Repo: `https://github.com/mio-openliven/mslauncher`
- Team sync / текущая правда: `TEAM_SYNC_MSLAUNCH.md`
- Release handoff: `release/OWNER_HANDOFF_RU.md`
- Release audit: `release/FINAL_HANDOFF_AUDIT_RU.md`
- Team 2 issue: `https://github.com/mio-openliven/mslauncher/issues/16`

Правила старта для новой команды:

- Начинать с fresh `main`, не со старых локальных папок.
- Сначала читать `README.md`, `TEAM_SYNC_MSLAUNCH.md`, `release/OWNER_HANDOFF_RU.md`, `release/FINAL_HANDOFF_AUDIT_RU.md`.
- Любой баг оформлять в GitHub issue/PR с task ID.
- Не класть реальные пароли, SSH, токены, `.env`, ключи или customer secrets в GitHub.
- Не трогать `server_pack/build.json` и `server_pack/manifest.json` без отдельного решения владельца.
- Не пересобирать один публичный artifact отдельно от всей release chain.
- Не запускать Minecraft в автоматических agent-checks; реальный запуск остается ручной owner/customer acceptance.

Что чинить в будущем:

- player bug reports from `/reports`;
- endpoint drift;
- update/report breakage;
- P-007 panel-managed active build publishing, если владелец переводит Nukem с GitHub fallback на панельные сборки.

## Текущая публичная релизная цепочка

- Version: `1.9.7`
- Public client: `https://mslaunch.186.246.12.238.sslip.io/client`
- Direct setup: `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`
- Setup SHA-256: `166e36d6075787fe310fa45af1431e16dc7cb452133a54cd0d06c4d2922b04a3`
- Payload SHA-256: `c859a9338100f74d1a1f420c2f22209a4f0c4271f7b86170398dc08adb341c37`
- Bootstrap SHA-256: `38e21ae303a524f616fa39a2d8bdcae1ea9ca350739b5f313775780bb46f2971`

## Что не делать

- Не отправлять пароли в GitHub issue, PR, commit, публичный чат или общий файл.
- Не пересобирать один публичный артефакт отдельно от bootstrap/setup/payload цепочки.
- Не трогать `server_pack/build.json` и `server_pack/manifest.json` без отдельного решения.
