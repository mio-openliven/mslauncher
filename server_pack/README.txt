MSLauncher server pack

1. Put mod .jar files into:
   server_pack\mods

2. Put server/client config files into:
   server_pack\config

3. Put resource packs, models, textures, and similar content into:
   server_pack\resourcepacks

4. Generate manifest.json and build.json:
   python generate_manifest.py --base-dir server_pack --base-url https://example.com/mslauncher --minecraft-version 1.20.1 --loader fabric --server play.example.com --port 25565

5. Upload the whole server_pack content to your hosting/server.
   Upload it so the public folder is named mslauncher.
   The public files should look like this:
   https://example.com/mslauncher/build.json
   https://example.com/mslauncher/manifest.json
   https://example.com/mslauncher/mods/...
   https://example.com/mslauncher/config/...
   https://example.com/mslauncher/resourcepacks/...

6. In launcher_config.json set source_key to either:
   https://example.com/mslauncher/build.json

   Or set only the host:
   example.com

   This short value works only when build.json is exactly here:
   https://example.com/mslauncher/build.json

7. For public GitHub hosting, use the full raw URL:
   https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json

   GitHub short host form is not recommended.

8. build.example.json shows the expected build.json format.

Important:
- MSLauncher does not guess the mod list.
- It reads manifest.json and compares player files by SHA-256.
- If you change mods/config/resourcepacks, generate manifest.json again.
- Public GitHub files are public. A launcher password gate is only a UI barrier.
