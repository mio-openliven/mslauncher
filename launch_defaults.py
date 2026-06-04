from __future__ import annotations

from pathlib import Path


LANGUAGE_OPTIONS = {
    "EN": "en_us",
    "RU": "ru_ru",
}

FRESH_PROFILE_OPTIONS = {
    "narrator": "0",
    "onboardAccessibility": "false",
    "soundCategory_music": "0.5",
}


def seed_minecraft_options(profile_directory: str | Path, language: str) -> Path:
    profile_path = Path(profile_directory)
    profile_path.mkdir(parents=True, exist_ok=True)
    options_path = profile_path / "options.txt"

    options = read_minecraft_options(options_path)
    desired_options = dict(FRESH_PROFILE_OPTIONS)
    lang_value = LANGUAGE_OPTIONS.get(language.strip().upper())
    if lang_value:
        desired_options["lang"] = lang_value

    changed = False
    for key, value in desired_options.items():
        if key not in options:
            options[key] = value
            changed = True

    if changed or not options_path.exists():
        write_minecraft_options(options_path, options)
    return options_path


def read_minecraft_options(options_path: Path) -> dict[str, str]:
    if not options_path.exists():
        return {}

    options: dict[str, str] = {}
    for line in options_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            options[key] = value.strip()
    return options


def write_minecraft_options(options_path: Path, options: dict[str, str]) -> None:
    lines = [f"{key}:{value}" for key, value in sorted(options.items())]
    options_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
