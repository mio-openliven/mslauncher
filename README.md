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

## Run

```powershell
python -m pip install -r requirements.txt
python gui.py
```
