from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def root_panel_imports() -> set[str]:
    app_tree = ast.parse((PROJECT_ROOT / "admin_panel" / "app.py").read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(app_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.partition(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module.partition(".")[0])
    return {
        f"{name}.py"
        for name in imports
        if (PROJECT_ROOT / f"{name}.py").is_file()
    }


def main() -> int:
    script_path = PROJECT_ROOT / "release" / "upload_host_artifacts.ps1"
    assert script_path.is_file()

    script = script_path.read_text(encoding="utf-8")
    assert "MSLaunchPayload.dat" in script
    assert "MSLaunchSetup.exe" in script
    assert "bootstrap.json" in script
    assert "loader_support.py" in script
    assert root_panel_imports() == {"loader_support.py"}
    for support_file in root_panel_imports():
        assert support_file in script
    assert "C859A9338100F74D1A1F420C2F22209A4F0C4271F7B86170398DC08ADB341C37" in script
    assert "166E36D6075787FE310FA45AF1431E16DC7CB452133A54CD0D06C4D2922B04A3" in script
    assert "38E21AE303A524F616FA39A2D8BDCAE1EA9CA350739B5F313775780BB46F2971" in script
    assert "3024C90BCBB86668369804649C5F191D7915839C98BAB9DD4B94DF33A7C3B2A4" in script
    assert "/opt/mslaunch/data/downloads" in script
    assert "/opt/mslaunch/app" in script
    assert "mslaunch-panel.service" in script
    assert "systemctl restart '$PanelService'" in script
    assert "velocity" not in script.lower()
    assert "backup-$timestamp" in script
    assert "sha256sum -c -" in script
    assert "Invoke-RestMethod" in script
    assert "password" not in script.lower()
    assert "sshpass" not in script.lower()
    assert "plink" not in script.lower()

    print("host upload script smoke test: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
