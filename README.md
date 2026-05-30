# MSLauncher

MSLauncher is a compact Minecraft launcher and modpack synchronizer.

## Project Map

- `gui.py` - PyQt6 launcher UI, language switch, build selector, async workers.
- `launcher_core.py` - Minecraft version loading, Mojang install/launch, mod sync, crash log analysis.
- `profile_manager.py` - isolated launcher profiles for server, personal, and other mod sets.
- `generate_manifest.py` - admin tool for generating `manifest.json` from `mods`, `config`, and `resourcepacks`.
- `launcher_config.json` - local launcher configuration: builds, manifest URLs, default language, nickname.
- `requirements.txt` - Python dependencies.

## Launch Config

MSLauncher keeps mod sets isolated by profile. By default they are created under:

```text
data\instances\server
data\instances\personal
data\instances\other
```

`server` is the only profile that runs server modpack sync. `personal` and `other` launch without server sync, so the launcher still works as a regular Minecraft launcher when no manifest is configured.

You can override the root profile folder:

```json
"profiles_directory": "D:\\Games\\MSLauncher\\instances",
"default_profile": "server"
```

`launcher_config.json` supports basic Java launch settings:

```json
"launch": {
  "memory_min": "512M",
  "memory_max": "2G",
  "java_path": "",
  "loader": "vanilla",
  "jvm_args": []
}
```

The in-app settings panel can change the loader, RAM, Java path, and open the current profile folder.

## Admin Manifest

```powershell
python generate_manifest.py --base-dir . --base-url https://raw.githubusercontent.com/OWNER/REPO/main
```

The generated `manifest.json` should be available through a raw URL and configured in `launcher_config.json`.

## Remote Build Config

Each build can use either `manifest_url` directly or a `source_key`.

```json
{
  "id": "main",
  "name": "Main Server",
  "minecraft_version": "1.20.1",
  "loader": "fabric",
  "loader_version": "latest",
  "source_key": "https://example.com/mslauncher/build.json",
  "server": "play.example.com",
  "port": "25565",
  "manifest_url": ""
}
```

If `source_key` is not a full URL, MSLauncher treats it as a host and loads:

```text
http://HOST/mslauncher/build.json
```

Remote `build.json` can provide `name`, `minecraft_version`, `loader`, `loader_version`, `manifest_url`, `server`, and `port`.

Supported loader values:

- `vanilla`
- `fabric`

## Run

```powershell
python -m pip install -r requirements.txt
python gui.py
```

## Build EXE

```powershell
.\build_exe.ps1
```

Output:

```text
dist\MSLauncher\MSLauncher.exe
```

## Smoke Test

```powershell
python tools\smoke_test_sync.py
python tools\smoke_test_profiles.py
python tools\smoke_test_settings.py
python tools\smoke_test_java_diagnostics.py
python tools\smoke_test_remote_config.py
```

The sync smoke test starts a local temporary HTTP server and checks the `source_key -> manifest -> sync -> download` flow. The profile smoke test checks isolated launcher folders. The settings smoke test checks loader, RAM, and Java path validation. The Java diagnostics smoke test checks Minecraft/Fabric Java requirements. The remote config smoke test checks invalid JSON, HTTP errors, and bad remote build fields.
