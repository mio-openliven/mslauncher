from __future__ import annotations

import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from launch_defaults import read_minecraft_options, seed_minecraft_options
from launcher_core import build_subprocess_startup_kwargs


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        profile_path = Path(temp_dir)
        options_path = seed_minecraft_options(profile_path, "RU")
        options = read_minecraft_options(options_path)
        assert options["lang"] == "ru_ru"
        assert options["soundCategory_music"] == "0.5"
        assert options["narrator"] == "0"
        assert options["onboardAccessibility"] == "false"

        options_path.write_text(
            "lang:en_us\nsoundCategory_music:1.0\nnarrator:1\n",
            encoding="utf-8",
        )
        seed_minecraft_options(profile_path, "RU")
        preserved_options = read_minecraft_options(options_path)
        assert preserved_options["lang"] == "en_us"
        assert preserved_options["soundCategory_music"] == "1.0"
        assert preserved_options["narrator"] == "1"
        assert preserved_options["onboardAccessibility"] == "false"

    startup_kwargs = build_subprocess_startup_kwargs()
    if startup_kwargs:
        assert "startupinfo" in startup_kwargs
        assert "creationflags" in startup_kwargs

    print("launch defaults smoke test: OK")


if __name__ == "__main__":
    main()
