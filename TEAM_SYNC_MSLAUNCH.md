# MSLaunch Team Sync

Date: 2026-06-04

Purpose: keep two teams from doing the same work or blocking each other.

## Active Teams

- Team 1: launcher visual/UI polish.
- Team 2: release coordination, task board, GitHub/installer/handoff safety.

## Team 1 Scope

Team 1 may work on launcher appearance only:

- `gui.py`
- visual assets under `assets/`
- launcher UI smoke checks
- UI notes or mockups when needed

Before changing shared launcher behavior, Team 1 should write a short note in this file or route through Agent 0 / Navigator.

## Team 2 Scope

Team 2 owns:

- `AGENTS.md`
- `tasks.md`
- release and handoff coordination
- GitHub/installer/package checks
- panel or hosting routing only when explicitly approved

## Do Not Touch Without Explicit Approval

- `server_pack/build.json`
- `server_pack/manifest.json`
- production hosting
- SSH, passwords, tokens, keys, certificates, `.env`
- Minecraft launch
- commit, push, publish, or deploy actions outside the current approved task

## Conflict Rule

If both teams need the same file:

1. Stop before editing.
2. Write the intended change and file list here.
3. Wait for Agent 0 / Navigator to route ownership.

## Current State

- Repository: `mio-openliven/mslauncher`
- Main project path on this PC: `C:\Users\Li2Fox\Documents\Лаунчер`
- Progress: 76%/100
- Current release path accepts GitHub fallback.
- Panel-managed active-build remains quarantined until authorized admin/hosting action.
- Mascot remains parked until post-MVP approval.

## Next Coordination Step

Team 1 should report:

- exact files they plan to edit;
- whether they need only visual polish or behavior changes;
- checks they can run without launching Minecraft.
