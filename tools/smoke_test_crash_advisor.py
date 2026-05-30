from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crash_advisor import advise_crash


def assert_contains(message: str, expected_parts: tuple[str, ...]) -> None:
    lower_message = message.lower()
    missing_parts = [part for part in expected_parts if part.lower() not in lower_message]
    if missing_parts:
        raise AssertionError(f"Missing {missing_parts} in message:\n{message}")


def main() -> None:
    missing_dependency = advise_crash(
        [
            "Mod 'coolmod' requires any version of fabric-api, which is missing",
            "mods/coolmod-1.20.1.jar",
        ],
        1,
        "EN",
    )
    assert_contains(missing_dependency, ("dependency", "fabric-api", "coolmod-1.20.1.jar", "what to try", "what to send admin"))

    missing_dependency_ru = advise_crash(
        [
            "Mod 'coolmod' requires any version of fabric-api, which is missing",
            "mods/coolmod-1.20.1.jar",
        ],
        1,
        "RU",
    )
    assert_contains(missing_dependency_ru, ("\u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442", "fabric-api", "\u0447\u0442\u043e \u043f\u043e\u043f\u0440\u043e\u0431\u043e\u0432\u0430\u0442\u044c"))

    mixin_conflict = advise_crash(
        [
            "org.spongepowered.asm.mixin.transformer.throwables.MixinTransformerError",
            "Mixin apply failed for mod examplemod",
        ],
        1,
        "EN",
    )
    assert_contains(mixin_conflict, ("mixin", "examplemod", "wrong mod version"))

    java_version = advise_crash(
        [
            "java.lang.UnsupportedClassVersionError: net/example/Mod has been compiled by a more recent version",
        ],
        1,
        "EN",
    )
    assert_contains(java_version, ("java", "too old", "java 21"))

    duplicate_mods = advise_crash(
        [
            "Duplicate mods: mods/fabric-api-1.jar and mods/fabric-api-2.jar",
        ],
        1,
        "EN",
    )
    assert_contains(duplicate_mods, ("duplicate", "fabric-api-1.jar", "fabric-api-2.jar"))

    unknown = advise_crash(["Something unexpected happened"], 1, "EN", "C:/Temp/latest.log")
    assert_contains(unknown, ("not recognized", "latest.log", "send latest.log", "C:\\Temp\\latest.log"))

    unknown_ru = advise_crash(["Something unexpected happened"], 1, "RU")
    assert_contains(unknown_ru, ("\u043d\u0435\u043e\u0436\u0438\u0434\u0430\u043d\u043d\u043e", "latest.log"))

    print("crash advisor smoke test: OK")


if __name__ == "__main__":
    main()
