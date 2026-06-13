# AGENTS.md draft for MSLaunch

## Project Rules
- Work in `C:\Users\Li2Fox\Documents\Лаунчер`.
- Do not launch Minecraft in automated checks.
- Do not commit or push unless explicitly requested.
- Do not touch `server_pack/build.json` or `server_pack/manifest.json` unless explicitly requested.
- Prefer small scoped changes over large rewrites.
- Keep launcher business logic intact:
  - MSLaunch/independent opens game folder for Mods/Game Folder.
  - MS Nuckem uses build password gate before mod download/sync.
  - VibeCraft is disabled/placeholder.

## Start Of Session
1. Read `README.md`.
2. Run `git status --short`.
3. Read `tasks.md` if present.
4. Pick only one task from `To Do`.
5. Move it to `In Progress` before coding.

## Finish
1. Run relevant tests.
2. Move task to `Review` or `Done`.
3. Report changed files and tests.
4. Do not self-review as the same agent if reviewer role is available.

## Suggested Roles
- planner: breaks user requests into tasks.
- coder: implements one task id.
- reviewer: checks diff, risks, missing tests.
- release: handles GitHub/host/build/checksum only.
- mascot: handles assets/prototypes only.

