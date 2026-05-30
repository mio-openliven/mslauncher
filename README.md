# MSLauncher

MSLauncher is a compact Minecraft launcher and modpack synchronizer.

## Project Map

- `gui.py` - PyQt6 launcher UI, language switch, build selector, async workers.
- `launcher_core.py` - Minecraft version loading, Mojang install/launch, mod sync, crash log analysis.
- `profile_manager.py` - isolated launcher profiles for server, personal, and other mod sets.
- `generate_manifest.py` - admin tool for generating `manifest.json` from `mods`, `config`, and `resourcepacks`.
- `launcher_config.json` - default launcher configuration template: builds, manifest URLs, default language, nickname.
- `requirements.txt` - Python dependencies.

## Launch Config

MSLauncher keeps user data outside the install folder by default. On Windows, runtime data is stored under:

```text
%APPDATA%\MSLauncher
```

Default profile folders:

```text
%APPDATA%\MSLauncher\instances\server
%APPDATA%\MSLauncher\instances\personal
%APPDATA%\MSLauncher\instances\other
```

`server` is the only profile that runs server modpack sync. `personal` and `other` launch without server sync, so the launcher still works as a regular Minecraft launcher when no manifest is configured.

Crash reports are written into the active profile folder:

```text
%APPDATA%\MSLauncher\instances\<profile>\crash-reports
```

To enable portable mode, create an empty `.portable` file next to `MSLauncher.exe`. In portable mode, config and profiles are stored next to the executable:

```text
MSLauncher.exe
.portable
launcher_config.json
instances\
```

Assets are still read from the app bundle, not from user data.

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

## Java Requirements

MSLauncher checks Java before trying to start Minecraft. If `java_path` is empty, the launcher tries to find Java automatically from `PATH` and common Windows install folders:

- `C:\Program Files\Eclipse Adoptium`
- `C:\Program Files\Java`
- `C:\Program Files\Microsoft\jdk-*`
- `C:\Program Files (x86)\Java`

Required Java versions:

- Minecraft `1.20.5+` needs Java `21+`.
- Minecraft `1.18` through `1.20.4` needs Java `17+`.
- Minecraft `1.17.x` needs Java `16+`.
- Older Minecraft versions need Java `8+`.

On a clean Windows install, Java may not exist yet. Install a compatible Java version or set the full path to `java.exe` in launcher settings.

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
https://HOST/mslauncher/build.json
```

Remote `build.json` can provide `name`, `minecraft_version`, `loader`, `loader_version`, `manifest_url`, `server`, and `port`.

Security rules:

- `source_key`, `manifest_url`, and every manifest file URL must use `https://` in production.
- `http://` is not supported outside explicit local smoke tests.
- URLs must not contain username/password or fragments such as `#section`.
- Production URLs must not point to localhost or private IP addresses.

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
python tools\smoke_test_safe_sync.py
python tools\smoke_test_profiles.py
python tools\smoke_test_settings.py
python tools\smoke_test_java_diagnostics.py
python tools\smoke_test_remote_config.py
python tools\smoke_test_manifest_validator.py
python tools\smoke_test_url_security.py
python tools\smoke_test_crash_advisor.py
python tools\smoke_test_crash_logs.py
python tools\smoke_test_launch_worker_lifecycle.py
python tools\smoke_test_app_paths.py
```

The sync smoke test starts a local temporary HTTP server in explicit test mode and checks the `source_key -> manifest -> sync -> download` flow. The safe sync smoke test checks staging, managed markers, and no data loss on failed downloads. The profile smoke test checks isolated launcher folders. The settings smoke test checks loader, RAM, and Java path validation. The Java diagnostics smoke test checks Minecraft/Fabric Java requirements. The remote config smoke test checks invalid JSON, HTTP errors, and bad remote build fields. The manifest validator smoke test checks unsafe paths, hashes, URLs, and sizes. The URL security smoke test checks HTTPS-only production policy. The crash advisor smoke test checks player-friendly crash hints. The app paths smoke test checks source and packaged path resolution.

## Release Checklist

- Build the exe with `.\build_exe.ps1`.
- Launch on a clean Windows VM from a read-only/install-like folder.
- Verify Java auto-detection and the missing-Java error message.
- Verify successful server sync.
- Verify failed network sync leaves existing files untouched.
- Verify hash mismatch leaves existing files untouched.
- Verify Fabric launch for the target Minecraft version.
- Verify crash report visibility and the Open crash reports button after a forced crash.
