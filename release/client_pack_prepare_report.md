# Client Pack Prepare Report

Status: historical/sample report from the earlier client-pack preparation pass.

Do not use this file as current first-client release truth. Current handoff truth is in:

- `release/FINAL_HANDOFF_AUDIT_RU.md`
- `release/LAST_BUILD_REPORT_RU.md`
- `release/OWNER_HANDOFF_RU.md`
- `TEAM_SYNC_MSLAUNCH.md`

- Archive: `C:\Users\Li2Fox\Downloads\mods.rar`
- Output dir: `C:\Users\Li2Fox\Documents\Лаунчер\server_pack`
- Status: `ok`
- Base URL: `https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher`
- Analyzer loader: `fabric` / confidence `high`
- Analyzer versions: `1.20.1 (35), 1.20 (15), 1.20.2 (6), 1.0.0 (5), 1.21 (2), 1.0.8 (1), 1.0.36 (1), 1.1 (1), 1.1.0 (1), 1.1.3 (1)`
- Loader used: `fabric`
- Minecraft version used: `1.20.1`
- Build name: `Nukem Project`
- Server: `play.example.com`
- Port: `25565`
- Copied files count: `43`

## Warnings

- 3 jar(s) contain multi-loader metadata; Fabric still dominates.

## Copied Files

- `mods/bbs-1.7.7-1.20.1.jar`
- `mods/bbs_extended_sync-1.0.0-1.20.1 (1).jar`
- `mods/campositions-1.0.0.jar`
- `mods/copycats-3.0.7+mc.1.20.1-fabric.jar`
- `mods/create-fabric-6.0.8.1-build.1744-mc1.20.1.jar`
- `mods/createbigcannons-5.11.2-mc.1.20.1-fabric.jar`
- `mods/createdeco-2.1.1-1.20.1-fabric.jar`
- `mods/createunlimited-0.7.1.jar`
- `mods/CustomPlayerModels-Fabric-1.20-0.6.25a.jar`
- `mods/decocraft-3.0.7-1.20.1-fabric.jar`
- `mods/doomsday_decoration-1.1.3-fabric-1.20.1.jar`
- `mods/enchanted-vertical-slabs-2.2.1-backport1.20.1-fabric-mc1.20.1.jar`
- `mods/fabric-api-0.92.71.20.1.jar`
- `mods/fabric-api-0.92.9%2B1.20.1.jar`
- `mods/fabric-api-0.92.9_2B1.20.1.jar`
- `mods/FakenameFabric-1.2.0.0.jar`
- `mods/flycommand-1.0.8.jar`
- `mods/fusion-1.2.12-fabric-mc1.20.1.jar`
- `mods/geckolib-fabric-1.20.1-4.8.3.jar`
- `mods/hidenames-1.0.0.jar`
- `mods/indium-1.0.36+mc1.20.1.jar`
- `mods/interiors-1.20.1-fabric-0.6.0 (2).jar`
- `mods/litematica-fabric-1.20.1-0.15.4.jar`
- `mods/lithium-fabric-mc1.20.1-0.11.4.jar`
- `mods/malilib-fabric-1.20.1-0.16.3.jar`
- `mods/metki-1.20.1-fabric-1.0.0.jar`
- `mods/mobdismembermentfabric-1.20.1-1.1.0.jar`
- `mods/nuckemskins-0.4.6.jar`
- `mods/pointblank-fabric-1.20.1-1.11.1.jar`
- `mods/punchy-2.5.5-fabric-1.20.1.jar`
- `mods/rechiseled-1.2.4-fabric-mc1.20.1.jar`
- `mods/replaymod-1.20.1-2.6.23.jar`
- `mods/skinrestorer-2.6.0+1.20-fabric.jar`
- `mods/sodium-fabric-0.5.13+mc1.20.1.jar`
- `mods/supermartijn642configlib-1.1.8a-fabric-mc1.20.jar`
- `mods/supermartijn642corelib-1.1.20-fabric-mc1.20.1.jar`
- `mods/tl_skin_cape_fabric_1.20_1.20.1-1.38.jar`
- `mods/vanilla-permissions-0.3.5+1.20.1.jar`
- `mods/window-1.0.0-fabric-1.20.1.jar`
- `mods/worldedit-mod-7.2.15-1.20.1-fabric-forge (1).jar`
- `mods/WorldEditCUI-1.20+01.jar`
- `mods/wraith-harvestscythes-2.5.6+mc1.20 (1).jar`
- `mods/xaeroworldmap-fabric-1.20.1-1.40.11.jar`

## Skipped Files

- none

## Generated Files

- `manifest.json`
- `build.json`

## Next Commands

Run these in the separate public modpack repository, not necessarily in the launcher repo:

```powershell
git add server_pack
git commit -m "Update Nukem modpack"
git push
```

After publishing, update launcher `source_key` to the public raw `build.json` URL.
