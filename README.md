# MSLaunch

MSLaunch is a compact Minecraft launcher and modpack synchronizer.

## Project Map

- `gui.py` - PyQt6 launcher UI, language switch, build selector, async workers.
- `launcher_core.py` - Minecraft version loading, Mojang install/launch, mod sync, crash log analysis.
- `profile_manager.py` - isolated launcher profiles for server, personal, and other mod sets.
- `generate_manifest.py` - admin tool for generating `manifest.json` from `mods`, `config`, and `resourcepacks`.
- `launcher_config.json` - default launcher configuration template: builds, manifest URLs, default language, nickname.
- `requirements.txt` - Python dependencies.

## Launch Config

MSLaunch keeps user data outside the install folder by default. On Windows, runtime data is stored under:

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

`client_mode` controls branding and project links:

```json
"client_mode": "independent",
"social_links": {
  "nukem": {
    "youtube": "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98",
    "discord": "https://discord.com/invite/P35nvXQ"
  }
}
```

`independent` mode is neutral and does not show project social buttons. `nukem` mode shows only non-empty links from `social_links.nukem`. Empty or disabled links are hidden. Older flat `social_links` configs are still accepted for compatibility.

## Минимальная Настройка Клиента

Откройте `launcher_config.json` и в блоке `builds` укажите главный параметр `source_key`.

Если серверная папка доступна так:

```text
https://domain.com/mslauncher/build.json
```

то в конфиге достаточно написать:

```json
"source_key": "domain.com"
```

MSLaunch сам скачает `build.json`, возьмет из него `manifest_url`, скачает `manifest.json`, а потом проверит и докачает файлы из `mods`, `config`, `resourcepacks`. Моды вручную в конфиг лаунчера прописывать не нужно.

## Java Requirements

MSLaunch checks Java before trying to start Minecraft. If `java_path` is empty, the launcher tries to find Java automatically from `PATH` and common Windows install folders:

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

## How Admin Updates A Modpack

```powershell
python generate_manifest.py --base-dir server_pack --base-url https://example.com/mslauncher --minecraft-version 1.20.1 --loader fabric --server play.example.com --port 25565
```

Use the `server_pack` folder as the admin workspace:

```text
server_pack\
  mods\
  config\
  resourcepacks\
  manifest.json
  build.json
  build.example.json
  README.txt
```

Simple workflow:

1. Put mod `.jar` files into `server_pack\mods`.
2. Put configs into `server_pack\config`.
3. Put resource packs, models, textures, and similar content into `server_pack\resourcepacks`.
4. Run the command above.
5. Upload the whole `server_pack` content to hosting/server.
6. In `launcher_config.json`, set `source_key` to the public `build.json` URL or to the host name if `build.json` is at `/mslauncher/build.json`.

Public hosting should look like this:

```text
https://example.com/mslauncher/build.json
https://example.com/mslauncher/manifest.json
https://example.com/mslauncher/mods/...
https://example.com/mslauncher/config/...
https://example.com/mslauncher/resourcepacks/...
```

If the public build file is exactly:

```text
https://example.com/mslauncher/build.json
```

then the client config can use the short form:

```json
"source_key": "example.com"
```

MSLaunch expands it to `https://example.com/mslauncher/build.json`.

## GitHub Modpack Hosting

For client projects, use a separate public GitHub repository that contains only the modpack files:

```text
mslauncher/
  build.json
  manifest.json
  mods/
  config/
  resourcepacks/
```

Generate the files with the raw GitHub base URL:

```powershell
python generate_manifest.py --base-dir server_pack --base-url https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher --minecraft-version 1.20.1 --loader fabric
```

Set `source_key` to the full raw `build.json` URL:

```json
"source_key": "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json"
```

The short host form such as `"source_key": "example.com"` is meant for normal hosting where `build.json` is exactly at `/mslauncher/build.json`. For GitHub, prefer the full raw URL.

Theoretical/security note: a public GitHub repository does not hide files. A password gate in the launcher is only a client-side UI barrier that stops casual downloads through MSLaunch. If a user gets the raw URL, the files are public. Real access protection requires a private repo, backend, signed URLs, or token-based delivery.

MSLaunch does not guess which mods are correct. It downloads `manifest.json`, compares local files by SHA-256, downloads missing/changed files, and removes extra mods only in managed server profiles after successful sync.

If `--base-url` is empty, `manifest.json` will be generated with empty file URLs. That is useful for local inspection, but players cannot download files until a real HTTPS base URL is set.

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

If `source_key` is not a full URL, MSLaunch treats it as a host and loads:

```text
https://HOST/mslauncher/build.json
```

Remote `build.json` can provide `name`, `minecraft_version`, `loader`, `loader_version`, `manifest_url`, `server`, and `port`.

Security rules:

- `source_key`, `manifest_url`, and every manifest file URL must use `https://` in production.
- `http://` is not supported outside explicit local smoke tests.
- URLs must not contain username/password or fragments such as `#section`.
- Production URLs must not point to localhost or private IP addresses.
- Public GitHub raw URLs are allowed, but public repositories are not access control.

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

The build script uses `MSLauncher.spec` as the single source of truth and checks that the exe was created.

Output folder:

```text
dist\MSLauncher
```

Main executable:

```text
dist\MSLauncher\MSLauncher.exe
```

Before handing the release to a client, run the exe on Windows without Python installed.

## Release For Client

Для клиента: [release/CLIENT_SETUP_RU.md](release/CLIENT_SETUP_RU.md).

Для игроков: [release/PLAYER_README_RU.txt](release/PLAYER_README_RU.txt).

Чеклист перед передачей: [release/RELEASE_CHECKLIST_RU.md](release/RELEASE_CHECKLIST_RU.md).

Backlog после передачи: [release/POST_RELEASE_BACKLOG_RU.md](release/POST_RELEASE_BACKLOG_RU.md).

Release template config: [release/launcher_config.template.json](release/launcher_config.template.json).

## Smoke Test

```powershell
python tools\smoke_test_sync.py
python tools\smoke_test_safe_sync.py
python tools\smoke_test_profiles.py
python tools\smoke_test_build_packaging.py
python tools\smoke_test_qa_clean_sync_flow.py
python tools\smoke_test_generate_manifest.py
python tools\smoke_test_settings.py
python tools\smoke_test_java_diagnostics.py
python tools\smoke_test_remote_config.py
python tools\smoke_test_remote_server_contract.py
python tools\smoke_test_release_package.py
python tools\smoke_test_manifest_validator.py
python tools\smoke_test_url_security.py
python tools\smoke_test_user_errors.py
python tools\smoke_test_crash_advisor.py
python tools\smoke_test_crash_logs.py
python tools\smoke_test_launch_worker_lifecycle.py
python tools\smoke_test_app_paths.py
```

The sync smoke test starts a local temporary HTTP server in explicit test mode and checks the `source_key -> manifest -> sync -> download` flow. The safe sync smoke test checks staging, managed markers, and no data loss on failed downloads. The QA clean sync flow checks a clean server pack download, managed extra-mod deletion, bad hashes, missing files, missing manifest, and empty server manifest handling without launching Minecraft or opening the GUI. The profile smoke test checks isolated launcher folders. The build packaging smoke test checks PyInstaller spec/script release wiring. The generate manifest smoke test checks admin manifest/build generation and URL encoding. The settings smoke test checks loader, RAM, and Java path validation. The Java diagnostics smoke test checks Minecraft/Fabric Java requirements. The user errors smoke test checks player-friendly Java, HTTPS, hash, manifest, and technical report messages. The remote config smoke test checks invalid JSON, HTTP errors, and bad remote build fields. The remote server contract smoke test checks the `mslauncher/build.json + manifest.json + mods/config/resourcepacks` URL contract. The release package smoke test checks client release templates/docs. The manifest validator smoke test checks unsafe paths, hashes, URLs, and sizes. The URL security smoke test checks HTTPS-only production policy. The crash advisor smoke test checks player-friendly crash hints. The app paths smoke test checks source and packaged path resolution.

## Release Checklist

- Build the exe with `.\build_exe.ps1`.
- Launch on a clean Windows VM from a read-only/install-like folder.
- Verify Java auto-detection and the missing-Java error message.
- Verify successful server sync.
- Run `python tools\qa_clean_sync_flow.py`; it does not launch Minecraft and checks only server pack/config sync.
- Verify no-internet/source_key failure shows a short message and writes a technical report.
- Verify failed network sync leaves existing files untouched.
- Verify hash mismatch leaves existing files untouched.
- Verify Fabric launch for the target Minecraft version.
- Verify crash report visibility and the Open crash reports button after a forced crash.
