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
    )
    assert_contains(missing_dependency, ("dependency", "fabric-api", "coolmod-1.20.1.jar", "what to try"))

    mixin_conflict = advise_crash(
        [
            "org.spongepowered.asm.mixin.transformer.throwables.MixinTransformerError",
            "Mixin apply failed for mod examplemod",
        ],
        1,
    )
    assert_contains(mixin_conflict, ("mixin", "examplemod", "wrong mod version"))

    java_version = advise_crash(
        [
            "java.lang.UnsupportedClassVersionError: net/example/Mod has been compiled by a more recent version",
        ],
        1,
    )
    assert_contains(java_version, ("java", "too old", "java 21"))

    duplicate_mods = advise_crash(
        [
            "Duplicate mods: mods/fabric-api-1.jar and mods/fabric-api-2.jar",
        ],
        1,
    )
    assert_contains(duplicate_mods, ("duplicate", "fabric-api-1.jar", "fabric-api-2.jar"))

    unknown = advise_crash(["Something unexpected happened"], 1)
    assert_contains(unknown, ("not recognized", "latest.log"))

    print("crash advisor smoke test: OK")


if __name__ == "__main__":
    main()
