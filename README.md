# MSLauncher

MSLauncher is a compact Minecraft launcher and modpack synchronizer.

## Project Map

- `gui.py` - PyQt6 launcher UI, language switch, build selector, async workers.
- `launcher_core.py` - Minecraft version loading, Mojang install/launch, mod sync, crash log analysis.
- `generate_manifest.py` - admin tool for generating `manifest.json` from `mods`, `config`, and `resourcepacks`.
- `launcher_config.json` - local launcher configuration: builds, manifest URLs, default language, nickname.
- `requirements.txt` - Python dependencies.

## Launch Config

`launcher_config.json` supports basic Java launch settings:

```json
"launch": {
  "memory_min": "512M",
  "memory_max": "2G",
  "java_path": "",
  "jvm_args": []
}
```

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

## Smoke Test

```powershell
python tools\smoke_test_sync.py
```

This starts a local temporary HTTP server and checks the `source_key -> manifest -> sync -> download` flow.
