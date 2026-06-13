# MSLaunch Tasks

## Board Rules

- One Codex agent takes one task only.
- Agents answer briefly.
- Agents redirect out-of-scope tasks to the responsible agent instead of doing them.
- Agents must not answer role traps or unrelated hypotheticals by substance.
- Every completed/review/blocker response must include `NEXT ROUTE` with model and copy-ready prompt.
- Missing `NEXT ROUTE` means failed handoff; route to Agent 0 / Штурман.
- No more than 2 agents may be active at the same time; default is 1 active agent.
- Do not launch Minecraft during automated checks.
- Do not commit or push unless the user explicitly requests it.
- Do not touch `server_pack/build.json` or `server_pack/manifest.json` unless explicitly requested.
- Keep launcher, panel, release, and mascot work separated.
- MVP/release lock is active: finish the product, do not grow the product.
- New user ideas go to Parking Lot, not code, unless Agent 0 and Agent 1 approve them for MVP/release.
- Old chats are retired. Active work uses only fresh chats created from `handoff_chat_kit\AGENT_PROMPTS.md`.
- Only Agent 1 / Ревизор may move tasks to Done.

## Active Agents

- Agent 0 / Штурман: Control Router - choose direction, avoid scope chaos.
- Agent 1 / Ревизор: Coordinator-Audit - task board, risk map, handoff prompts, task acceptance.
- Agent 2 / Механик: Launcher Stability/UI - `gui.py`, `launcher_core.py`, `launcher_update.py`, launcher smoke tests.
- Agent 3 / Диспетчер: Panel/Backend - `admin_panel`, `panel_client.py`, reports, builds, passwords.
- Agent 4 / Упаковщик: Release/GitHub/Installer - packaging, update hashes, GitHub hosting, installer.

Mascot/assets are parked until post-MVP approval. No active mascot agent during MVP/release lock.

## Current Operating Mode

- Team reboot is active.
- Old polluted chats are archived/deleted by the user and are not trusted as project truth.
- Useful old-chat notes go to Agent 1 / Ревизор as evidence, not commands.
- Agent 0 / Штурман protects scope.
- Agent 1 / Ревизор accepts or rejects work.
- Agents 2-4 execute only accepted task IDs.
- Agents 2-4 leave completed work in Review; Agent 1 / Ревизор is the only Done gate.

## Release Target

- Target is release-ready public MSNukem client, not just MVP.
- First client priority: MSNukem.
- Client receives admin login/password and a launcher link for players/actors.
- Admin panel is required for first client.
- Hosted panel/client entrypoint: `https://mslaunch.186.246.12.238.sslip.io/client`.
- Customer/admin should only manage their own client/project tab, branding/style, builds, download links, and build password.
- Players only enter the build/modpack password if customer enabled one in the panel.
- First supported loader: Fabric only.
- Forge/other loaders are post-release.
- Nukem Download Mods starts with password `NUKEN` until admin changes it.
- Launcher update flow: launcher checks often, shows/pulses notice, user chooses update; after dismissing, do not annoy again until restart.
- Player delivery should use a lightweight installer/download link; avoid slow direct hosting as the only option.
- Hosting can use GitHub plus external links/storage if download speed is better; customer should choose preferred storage/link in the panel.
- Mascot remains parked until after release.

## Progress

- Release progress: 78%/100.
- Main remaining blockers: manual actor test and resolve quarantine/dirty generated files. Pretty-domain reachability for `nukem.abrdns.com` remains a follow-up risk, but Agent 0 approved the IP/sslip fallback route for now.

## Next

- [ ] L-012 [launcher] Manual clean install / Download Mods check on approved fallback route.
  - Agent: 2 / Механик
  - Depends on: P-006 accepted by Agent 1.
  - Goal: run the human launcher check that the fallback route is now suitable for a clean install: open Download Mods, pass the build password gate, and confirm the populated mod manifest reaches the player flow.
  - Acceptance: clean install/manual actor can reach Download Mods on the approved fallback route, enter the build password, and see real synced files instead of an empty manifest; no Minecraft launch during automated checks.

## Backlog

- [ ] A-003 [coordinator] Execute approved non-destructive desktop dump sort, then request delete approval.
  - Agent: 1 / Ревизор
  - Depends on: Agent 0 approval of the A-002 source/target plan.
  - Goal: move only approved keep/quarantine items to explicit checked targets; do not delete files.
  - Acceptance: every move has exact source and target; target root is checked before move; unrelated delete candidates stay in quarantine or require explicit user approval; no secrets in report; do not touch `server_pack/build.json` or `server_pack/manifest.json`.

- [ ] A-006 [coordinator] Classify generated `server_pack` files for the release path.
  - Agent: 1 / Ревизор
  - Goal: decide whether `Q-001` stays quarantined, is approved as intended release input evidence, or needs explicit owner action.
  - Rule: classify/report only; do not edit or revert `server_pack/build.json` or `server_pack/manifest.json` without explicit approval.

- [ ] A-007 [coordinator] Reconcile stale GitHub issue state after branch/base audit.
  - Agent: 1 / Ревизор
  - Goal: classify open issues `#4`, `#12`, `#16`, `#23` as still-active, partially resolved, or stale/superseded after the base decision and current hosted evidence.
  - Acceptance: close/split proposals are written first; no issue-closing action until the release path and current base are agreed.

## Quarantine

- [ ] Q-001 [coordinator] Decide what to do with modified generated files.
  - Agent: 1 / Ревизор
  - Files: `server_pack/build.json`, `server_pack/manifest.json`.
  - Release risk: blocking until explicitly approved, quarantined, or confirmed as intended release inputs.
  - Rule: do not edit or revert without explicit user approval.

- [ ] Q-002 [coordinator] Classify untracked prototype and portfolio folders.
  - Agent: 1 / Ревизор
  - Files: `prototypes`, `portfolio_oss_kit`, mascot generated assets.
  - Goal: decide keep, archive, ignore, or move.

## Parking Lot

- [ ] M-001 [mascot] Produce one approved 48-frame mascot loop outside the launcher.
  - Status: parked until post-MVP approval.
  - Scope: mascot source/processed assets and prototype folder only.
  - Forbidden: `gui.py` integration until Agent 0 and Agent 1 explicitly approve it.
  - Checks: visual review only.

## In Progress

## Review

- [ ] L-010 [launcher] Fix manual visual feedback from owner test: report wording and bottom status placement.
  - Agent: Agent 0 / Team 1 visual path.
  - Result: changed bug-only wording to problem wording through translation keys; adjusted feedback copy to cover problem/critique/wish; moved bottom status/progress under the Download Mods block so `Отчёт отправлен` no longer floats between Mods and Play.
  - Scope note: actual typed report/comment form remains code-team behavior in GitHub issue #4 / PR #5 follow-up.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.
  - Not tested: Minecraft launch; code-team PR #5/#7/#8 merge behavior.

- [ ] L-009 [launcher] Fix owner-visible UI defects from latest manual screenshots.
  - Agent: Team 1 / Launcher Design Polish.
  - Status: awaiting owner visual test via `C:\Users\Li2Fox\Desktop\MSLaunch TEST.lnk`.
  - Result: visual-only pass adjusted bottom bar alignment/status placement, dark combo popup styling, noisy label icons, compact status rows, top project/window controls, field padding, and report button neon/warm icon treatment.
  - Scope note: invisible behavior stays in GitHub issue #4 / PR #5 code-team path.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.
  - Not tested: Minecraft launch; real owner manual click-through.

## Done

- [x] P-004 [panel] Activate or verify hosted Nukem active build for panel-managed handoff.
  - Agent: 3 / Диспетчер; accepted by Agent 1 / Ревизор.
  - Result: the approved fallback route now satisfies the original hosted contract. Active build is populated, manifest is no longer empty, and password-gated access works on the fallback hosts.
  - Follow-up risk: pretty-domain recovery remains separate follow-up work unless Agent 0 re-prioritizes it.
  - Checks: public fallback GETs on active-build, manifest, and password-gated access flow.

- [x] A-008 [coordinator] Route hosted panel/VPS-side fix for P-006 blocker.
  - Agent: 0 / Штурман; accepted by Agent 1 / Ревизор.
  - Result: live panel DB was updated on the VPS to activate the populated `nukem-1-20-1-20260606` build, set the Nukem build password hash, and restore the fallback release contract without touching launcher files or `server_pack` generated files.
  - Checks: backup created on VPS before change; public fallback verification of active-build, manifest gating, and launcher update metadata.
  - Not tested: Minecraft launch, manual GUI click-through, pretty-domain `nukem.abrdns.com`, deploy/sync of newer local panel code.

- [x] P-006 [panel] Re-review hosted active-build contract after fallback now returns a real active build.
  - Agent: 3 / Диспетчер; accepted by Agent 1 / Ревизор.
  - Result: live-side hosted panel/VPS sync fixed the fallback release path. Active build now returns `nukem-1-20-1-20260606` with `1.20.1` / `fabric`, `access_required=true`, direct manifest access is gated, wrong-password access is rejected, correct-password access succeeds, and the manifest returns 43 files on the approved fallback hosts.
  - Checks: `python tools\smoke_test_admin_panel.py`; public GET on fallback `active-build`, manifest, and launcher update endpoints.
  - Not tested: Minecraft launch, manual GUI click-through, pretty-domain `nukem.abrdns.com`, code deploy/sync of newer local panel code.

- [x] L-011 [launcher] Reconcile launcher/release drift after A-005 base decision.
  - Agent: 2 / Механик; accepted by Agent 1 / Ревизор.
  - Result: latest `origin/main` launcher truth was restored for the release path, including `APP_VERSION = "1.9.8"`, `launch_defaults.py`, `loader_support.py`, hidden Java console startup handling, fresh-profile Minecraft option seeding, and crash/report helper UI behavior.
  - Scope note: accepted scope stayed within launcher files/support: `gui.py`, `launcher_core.py`, `launcher_update.py`, `launch_defaults.py`, `loader_support.py`. Broad dirty panel/release/generated changes were not accepted as part of L-011.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`; Agent 1 diff review of L-011 scope; Agent 1 confirmed `launch_defaults.py` and `loader_support.py` match `origin/main` content.
  - Not tested: Minecraft launch, packaging, panel/backend/release checks, manual owner/actor click-through.

- [x] A-005 [coordinator] Decide bug-fix base before touching launcher/panel code again.
  - Agent: 1 / Ревизор
  - Result: Agent 0 approved latest `origin/main` / release base as source of truth. Current `codex/owner-ui-polish` stays preserved as a donor branch only for explicitly accepted owner-visible launcher UI changes from `L-009` / `L-010`; broad dirty launcher/panel/release work must not be carried forward wholesale.
  - Guardrails: preserve current local dirty work; do not reset/revert/delete; do not commit/push; do not launch Minecraft; do not touch `server_pack/build.json` or `server_pack/manifest.json`.
  - Next queue effect: `L-011` becomes the next safe builder task; `P-006` stays after `L-011` or parallel only when it does not touch launcher files; manual actor test remains after branch/base and launcher reconcile.

- [x] A-004 [coordinator] Audit current branch/reports and define the first safe bug-fix queue.
  - Agent: 1 / Ревизор
  - Result: before any code fix, the board now treats branch-base selection as the first safe step. Current branch `codex/owner-ui-polish` is synced with its own upstream but `48` commits behind `origin/main`; current branch still reports `APP_VERSION = "1.9.7"` while `origin/main` already has `1.9.8`.
  - Classification:
    - Branch drift: do not accept or extend dirty launcher/panel work until `A-005` chooses whether to preserve current UI work or replay it onto the latest base.
    - `Q-001`: still a real quarantine blocker; classify only, no edits to `server_pack/build.json` or `server_pack/manifest.json`.
    - `P-004`: original blocked `404` evidence is stale; move re-review into `P-006` because hosted fallback now returns active build `nukem1-21-1`.
    - `L-009` / `L-010`: keep in `Review`, but do not mark accepted yet because their review context is stale until the base decision confirms whether they survive/rebase cleanly onto current release truth.
    - Manual actor test: remains the top human validation blocker after the base decision.
    - GitHub issues: `#12` still looks active because current branch diff regresses launch-default work; `#4` still looks only partially resolved; `#16` and `#23` look potentially stale/superseded and should be reconciled under `A-007`, not blindly closed.
  - Prioritized queue: `A-005` -> `L-011` / `P-006` -> manual actor test -> `A-006` / `A-007`.
  - Checks: `git status --short --branch`; `git rev-parse HEAD`; `git rev-list --left-right --count origin/main...HEAD`; `git diff origin/main -- launcher_update.py`; `git diff origin/main -- gui.py launcher_core.py launcher_update.py admin_panel/app.py panel_client.py`; read `release/FINAL_HANDOFF_AUDIT_RU.md`; read `release/LAST_BUILD_REPORT_RU.md`; read `release/client_pack_report.md`; read `handoff_chat_kit/LAROY_AUDIT_REPORT.txt`; `gh api repos/mio-openliven/mslauncher/issues/4`; `gh api repos/mio-openliven/mslauncher/issues/12`; `gh api repos/mio-openliven/mslauncher/issues/16`; `gh api repos/mio-openliven/mslauncher/issues/23`.

- [x] R-007 [release] Restore live Nukem hosting reachability or confirm planned fallback route.
  - Agent: 4 / Упаковщик; accepted by Agent 1 / Ревизор.
  - Result: pretty domain `https://nukem.abrdns.com/` remains unavailable on 443, but Agent 0 approved temporary public fallback via `https://nukem.186.246.12.238.sslip.io/` for the current release path.
  - Verified fallback: `/` returns `200`; `/panel` redirects to login and returns `200`; `/downloads/MSLaunchSetup.exe` returns `200` and downloads `287744` bytes; `/api/launcher/update` returns launcher version `1.9.8`; `/api/projects/nukem/active-build` returns active build `nukem1-21-1`.
  - Hash: downloaded fallback installer SHA-256 `7d2ae7c9cec048a9d2cf287445533162b458a9c865677193cf7ba827e983695c` matches `/api/launcher/update`.
  - Follow-up risk: pretty-domain DNS/VPS recovery remains separate follow-up work unless Agent 0 re-prioritizes it as a release blocker again.
  - Checks: `git status --short --branch`; `git fetch origin --prune`; `git rev-list --left-right --count origin/codex/owner-ui-polish...HEAD`; `gh repo view --json nameWithOwner,defaultBranchRef,url`; `gh pr list --state open --json number,title,headRefName,baseRefName,url`; public HTTP/HTTPS reachability checks for fallback/live endpoints.

- [x] L-008 [launcher] Replace heavy green status-card glyphs with thin blue/cyan treatment.
  - Agent: Team 1 / Launcher Design Polish; accepted by Team 2 / Release Risk & Dirty Work.
  - Result: scoped status-card visual polish accepted: `StatusGlyph` uses thinner blue/cyan strokes with subtle glow, status row icons are smaller and less blocky, check marks are restrained, and status QSS no longer uses the heavy mint/green treatment.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.
  - Not tested: real Windows visual click-through, Minecraft launch.
  - Scope note: unrelated broad dirty `gui.py` mascot/tray/update behavior changes were not accepted as part of L-008.

- [x] L-007 [launcher] Polish bottom control bar icons, alignment, status, and loader dropdown.
  - Agent: Team 1 / Launcher Design Polish; accepted by Team 2 / Release Risk & Dirty Work.
  - Result: scoped bottom control bar polish accepted: consistent Nick/Build/Version/Loader/Download/Play icon treatment, tighter 38px field/button rhythm, intentional status/progress placement, visible combo dropdown affordances, and loader dropdown limited to existing `vanilla`/`fabric` behavior synced with settings.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.
  - Not tested: real Windows visual click-through, Minecraft launch.
  - Scope note: unrelated broad dirty `gui.py` mascot/tray/update behavior changes were not accepted as part of L-007.

- [x] L-006 [launcher] Fix compact control bar overflow at 1040x560.
  - Agent: Team 1 / Launcher Design Polish; accepted by Team 2 / Release Risk & Dirty Work.
  - Result: scoped compact control bar overflow fix accepted for 1040x560 and 1280x720: fields/buttons remain 42px tall, control frame stays within the compact height, separators stay 52px, and smoke geometry assertions verify no overlap between fields, separators, Mods, and Play controls.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.
  - Not tested: real Windows visual click-through, Minecraft launch.
  - Scope note: unrelated broad dirty `gui.py` mascot/tray/update behavior changes were not accepted as part of L-006.

- [x] L-005 [launcher] Align top control bar with approved compact design.
  - Agent: 2 / Механик; accepted by Agent 1 / Ревизор.
  - Result: scoped top control bar changes accepted: compact `controlFrame` geometry, aligned Nickname / Build / Version / loader groups, 42px fields/buttons, 64px groups, 52px separators, and smoke geometry assertions for 1280x720 and 1040x560.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.
  - Not tested: real Windows visual click-through, Minecraft launch.
  - Scope note: broad unrelated dirty mascot/sidebar/update changes in `gui.py` were not accepted as part of L-005.

- [x] R-006 [release] Verify hosted `/client` tester download handoff after panel fix.
  - Agent: 4 / Упаковщик; accepted by Agent 1 / Ревизор.
  - Result: hosted `/client` now points to `https://mslaunch.186.246.12.238.sslip.io/downloads/MSLaunchSetup.exe`; page checksum matches the direct download SHA-256.
  - Hash: `D94ADC6255232FCE681ABAF6A7FE6D4F6E21B2E4C6634A97F19D004CA502B554`.
  - Size: `286720` bytes.
  - Hosted action: Agent 0 deployed accepted P-005 `admin_panel/app.py` to `/opt/mslaunch/app/admin_panel/app.py`, created remote backup `/opt/mslaunch/app/admin_panel/app.py.bak-20260604-130336`, and restarted only `mslaunch-panel.service`; `velocity.service` stayed active and was not touched.
  - Checks: Agent 4 public `/client` HTTP check; Agent 4 direct download hash check; Agent 0 independent public `/client` and direct download hash check; stale `C493...` checksum absent.
  - Not tested: running installer, Minecraft launch, hosted DB/build/admin data.

- [x] P-005 [panel] Fix `/client` checksum/download consistency source.
  - Agent: 3 / Диспетчер
  - Result: local `/client` source now computes the checksum from the actual served `MSLaunchSetup.exe`; exact stale checksum no longer remains in scoped source.
  - Checks: `Get-FileHash dist\MSLaunchSetup.exe`; `python -m py_compile admin_panel\app.py panel_client.py tools\smoke_test_admin_panel.py`; `python tools\smoke_test_admin_panel.py`; scoped `rg` for stale checksum.
  - Not tested by Agent 3: hosted deploy/restart, SSH/secrets, Minecraft, commit/push.
  - Follow-up: hosted public `/client` was verified in R-006 after Agent 0 deploy/restart.

- [x] R-005 [release] Prepare Desktop launcher installer handoff and old MSLaunch cleanup plan.
  - Agent: 4 / Упаковщик
  - Result: Desktop package is ready at `C:\Users\Li2Fox\Desktop\MSLaunch_Nukem_GitHubFallback.zip`; Agent 0 completed approved cleanup of old local install/user-data roots.
  - Hash: `C84D0BAF8D88D8D0760051E28E5763AAAE99245F2AAF1AEF872DE440173A360B`.
  - Cleaned paths verified absent: `C:\Users\Li2Fox\AppData\Local\MSLaunch`; `C:\Users\Li2Fox\AppData\Roaming\MSLauncher`.
  - Checks: `git status --short --branch`; source package SHA-256; Desktop target path check; Desktop copy SHA-256; old install/user-data path inventory; cleaned path absence check.
  - Not tested: Minecraft launch, running launcher from Desktop package, clean Windows actor test, publish/upload/deploy.

- [x] A-002 [coordinator] Audit desktop dump and produce safe sort/quarantine plan.
  - Agent: 1 / Ревизор
  - Result: desktop dump inventory completed without deletion or moves. Release-relevant items are MSLaunch shortcuts/bat/old beta zip/cert and mascot/chat-kit artifacts; image/preset candidates are top-level images plus mascot/generated image folders; unrelated/plugin/server/world/Codex backup items should stay quarantined until Agent 0 approves moves or deletion. R-005 can proceed because Desktop installer handoff does not depend on moving the dump.
  - Safe targets: launcher keep items only to the MSLaunch project if still needed; important image/preset assets to `C:\Users\Li2Fox\Documents\Лаунчер\изображения\тянки раб стола` after creating/checking the parent; risky Codex backup/secrets-like files must not enter GitHub/project reports.
  - Checks: `git status --short --branch`; top-level dump inventory; recursive folder/file type summary; image candidate inventory; target path safety check.

- [x] R-004 [release] Prepare final MSNukem release package using GitHub fallback path.
  - Agent: 4 / Упаковщик
  - Result: final local release package exists at `release\MSLaunch_Nukem_GitHubFallback.zip`; packaged config uses direct GitHub fallback, `panel.enabled=false`, `default_build=nukem`, and SHA-256-only initial `NUKEN` password hash.
  - Hash: `C84D0BAF8D88D8D0760051E28E5763AAAE99245F2AAF1AEF872DE440173A360B`.
  - Checks: `python tools\smoke_test_release_package.py`; `python tools\smoke_test_build_packaging.py`; `python -m py_compile bootstrapper.py launcher_update.py`; `powershell -ExecutionPolicy Bypass -File .\release\prepare_release.ps1 -Preset nukem`; packaged config inspection; zip SHA-256 check.
  - Not tested: Minecraft launch, publish/upload/deploy, clean Windows actor test, hosted panel active-build path.

- [x] A-001 [coordinator] Audit git branch/dirty-tree/refactor risk before final release build.
  - Agent: 1 / Ревизор
  - Result: branch is `main...origin/main`; dirty tree is broad but already separated by ownership. Release-blocking: `server_pack/build.json` and `server_pack/manifest.json` remain quarantined, and final release package/checks are still needed. Not release-blocking for current GitHub fallback path: P-004 stays quarantined. Do not refactor launcher/panel/release code before release.
  - Checks: read `AGENTS.md`, `tasks.md`, `README.md`; `git status --short --branch`.

- [x] C-001 [coordinator] Finalize the recovery task board and propose `tasks.json`.
  - Agent: 1 / Ревизор
  - Result: `tasks.md` now separates windows, next tasks, backlog, and quarantine; `tasks.json` shape was proposed.
  - Checks: `git status --short --branch`.

- [x] L-003 [launcher] Align mascot-disabled launcher behavior with GUI smoke test.
  - Agent: 2 / Механик
  - Result: with `MASCOT_FEATURE_ENABLED = False`, GUI smoke test no longer requires mascot windows/assets.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.

- [x] L-001 [launcher] Stabilize launcher update/install notice states.
  - Agent: 2 / Механик
  - Result: update check now preserves honest `available`, `error`, and `ok` states; failed checks no longer leave the button as `OK`.
  - Checks: `python -m py_compile gui.py launcher_update.py`; `python tools\smoke_test_launcher_update.py`.

- [x] L-002 [launcher] Audit UI layout at 1280x720 and 1040x560.
  - Agent: 2 / Механик
  - Result: found 1040x560 settings/control overlap, update notice title clipping, and lower-panel tight text candidates; project switcher and top-right controls were OK.
  - Checks: `python tools\smoke_test_gui_offscreen.py`.

- [x] L-004 [launcher] Fix scoped layout issues found in L-002.
  - Agent: 2 / Механик
  - Result: fixed 1040x560 settings/control overlap, update notice title clipping, and tight lower-panel text candidates without broad UI redesign.
  - Checks: `python -m py_compile gui.py launcher_core.py launcher_update.py`; `python tools\smoke_test_gui_offscreen.py`.

- [x] P-001 [panel] Define panel MVP endpoints and data model.
  - Agent: 3 / Диспетчер
  - Result: documented panel MVP API/data model and aligned active-build `access_required` as boolean.
  - Checks: `python -m py_compile panel_client.py`; `python tools\smoke_test_admin_panel.py`.

- [x] P-002 [panel] Verify launcher fallback when panel is unavailable.
  - Agent: 3 / Диспетчер
  - Result: added smoke coverage for disabled panel config, missing panel URL, active-build 404 fallback, and launcher-update 404 fallback.
  - Checks: `python tools\smoke_test_admin_panel.py`.

- [x] P-003 [panel] Verify hosted admin/client flow for MSNukem handoff.
  - Agent: 3 / Диспетчер
  - Result: hosted `/client`, `/login`, protected `/builds` redirect, launcher update API, and GitHub fallback build/manifest are reachable; hosted active-build 404 is classified as no active Nukem build in the panel DB, not an unclassified API failure.
  - Caveat: accepted only as hosted panel reachable with GitHub fallback; panel-managed modpack handoff remains P-004.
  - Checks: `python tools\smoke_test_admin_panel.py`; hosted `/client`; hosted `/login`; hosted `/builds`; hosted `/api/launcher/update`; hosted GitHub fallback `build.json` and `manifest.json`; hosted `/api/projects/nukem/active-build`.

- [x] R-001 [release] Write release checklist for public MSNukem client.
  - Agent: 4 / Упаковщик
  - Result: rewrote public MSNukem release checklist with GitHub hosting notes, Nukem config, installer/package checklist, no-Minecraft smoke checks, and client handoff.
  - Checks: documentation review; `git diff -- release/RELEASE_CHECKLIST_RU.md`; `git status --short --branch`.

- [x] R-002 [release] Audit update/installer hash flow separately from launcher UI.
  - Agent: 4 / Упаковщик
  - Result: update/installer hash flow accepted; bootstrap manifest parser now requires SHA-256 as 64 lowercase hex chars in both Python and C# bootstrapper paths, while existing installer/hash safeguards are preserved.
  - Checks: `python -m py_compile bootstrapper.py launcher_update.py`; `python tools\smoke_test_launcher_update.py`.

- [x] R-003 [release] Remove build-spec dependency on previous `dist` output if confirmed unsafe.
  - Agent: 1C / Ревизор-замена
  - Result: accepted scoped packaging fix; `MSLauncher.spec` collects `minecraft_launcher_lib` package data from the installed dependency and no longer depends on old `dist\MSLauncher` contents.
  - Checks: `python tools\smoke_test_build_packaging.py`.
