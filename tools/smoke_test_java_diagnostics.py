from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import java_diagnostics as jd


def expect_error(callback) -> None:
    try:
        callback()
    except jd.JavaDiagnosticError:
        return
    raise AssertionError("Expected JavaDiagnosticError")


def main() -> None:
    assert jd.parse_java_major_version('java version "1.8.0_401"') == 8
    assert jd.parse_java_major_version('openjdk version "17.0.10" 2024-01-16') == 17
    assert jd.parse_java_major_version('openjdk version "21.0.2" 2024-01-16') == 21
    assert jd.parse_java_major_version("bad output") is None

    assert jd.get_required_java_major("1.16.5") == 8
    assert jd.get_required_java_major("1.17.1") == 16
    assert jd.get_required_java_major("1.20.1") == 17
    assert jd.get_required_java_major("1.20.5") == 21

    expect_error(lambda: jd.diagnose_launch_environment("1.12.2", "fabric", "", java_search_roots=[], path_env=""))
    expect_error(lambda: jd.diagnose_launch_environment("1.20.1", "vanilla", "", java_search_roots=[], path_env=""))

    original_get_java_major_version = jd.get_java_major_version
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_java = root / "old" / "bin" / "java.exe"
            new_java = root / "jdk-21" / "bin" / "java.exe"
            old_java.parent.mkdir(parents=True)
            new_java.parent.mkdir(parents=True)
            old_java.write_text("", encoding="utf-8")
            new_java.write_text("", encoding="utf-8")

            versions = {
                str(old_java): 8,
                str(new_java): 21,
            }

            def fake_get_java_major_version(java_path: str) -> int:
                return versions[str(Path(java_path))]

            jd.get_java_major_version = fake_get_java_major_version

            expect_error(lambda: jd.diagnose_launch_environment("1.20.1", "vanilla", str(old_java)))
            selected_java = jd.diagnose_launch_environment(
                "1.20.5",
                "vanilla",
                "",
                java_search_roots=[root],
                path_env="",
            )
            assert selected_java == str(new_java)
    finally:
        jd.get_java_major_version = original_get_java_major_version

    print("java diagnostics smoke test: OK")


if __name__ == "__main__":
    main()
