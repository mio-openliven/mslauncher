# MSLaunch Team Sync

Date: 2026-06-05

Purpose: keep both teams from doing the same work or blocking each other.

## Active Teams

- Team 1: launcher visual/UI polish.
- Team 2: release coordination, task board, GitHub/installer/handoff safety.

## Team 1 Scope

Team 1 may work on launcher appearance only:

- `gui.py`
- visual assets under `assets/`
- launcher UI smoke checks
- UI notes or mockups when needed

Before changing shared launcher behavior, Team 1 must route through Agent 0.

## Team 2 Scope

Team 2 owns:

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
2. Write the intended change and file list here or in GitHub issue #16.
3. Wait for Agent 0 to route ownership.

## Current State

- Repository: `mio-openliven/mslauncher`
- Main release worktree on this PC: `C:\Users\Li2Fox\Documents\Лаунчер_integration_host`
- Progress: 95%/100
- `main` includes PR #30 host upload safety, PR #31 source label/version sync, PR #35 Nukem password sync, and the active `Release Beta 1.9.8` follow-up.
- Open PR list was empty at the last Agent 0 release check.
- Public release path is `v1.9.8` and currently accepts GitHub fallback.
- Prepared `/downloads/bootstrap.json` SHA-256: `e066b63f350d444b656863433a7ed98fa8275aed845851bcc7e97c134d152392`
- Prepared `/downloads/MSLaunchSetup.exe` SHA-256: `7d2ae7c9cec048a9d2cf287445533162b458a9c865677193cf7ba827e983695c`
- Prepared `/downloads/MSLaunchPayload.dat` SHA-256: `91835ffbd508827ccdcc3bf66a37d9e06a6838a48c9ce304100f043c2e31b656`
- Public `/api/launcher/update` must point to version `1.9.8` and setup SHA `7d2ae7c9cec048a9d2cf287445533162b458a9c865677193cf7ba827e983695c` after host upload.
- Public `/api/projects/nukem/active-build` still returns `404 No active build`; this is accepted for the current GitHub fallback release and remains P-007 follow-up work.
- Supported launcher loaders in the current code stack: `vanilla`, `fabric`, `quilt`, `neoforge`. Forge remains outside release scope until separately approved.
- Mascot remains parked until post-MVP approval.

## Release Guardrail

Do not rebuild or deploy only one public artifact for a cosmetic label change.

If the visible downloaded client must change, route a full artifact-sync pass:

1. Rebuild `dist/MSLauncher`.
2. Rebuild `MSLaunchPayload.dat` and record its SHA-256.
3. Update the setup bootstrapper embedded payload SHA.
4. Rebuild `MSLaunchSetup.exe` and record its SHA-256.
5. Regenerate `bootstrap.json`.
6. Upload host artifacts.
7. Update GitHub release fallback assets or create the next release.
8. Verify `/downloads/*`, `/api/launcher/update`, and GitHub fallback hashes.

## Next Coordination Step

Team 2 should focus on true release blockers only:

- P-007 panel-managed active build publishing;
- launcher update/report stability;
- host/live endpoint drift;
- release package/hash consistency.

Team 1 should not start new visual work unless Agent 0 routes a specific MVP blocker.
