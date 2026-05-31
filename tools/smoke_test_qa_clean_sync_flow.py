from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.qa_clean_sync_flow import run_qa


def main() -> None:
    summary = run_qa()
    assert summary["downloaded"] == 3
    assert summary["deleted_extra_mods"] == 1
    assert summary["failed_download_preserved_files"] == "OK"
    print("qa clean sync flow smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
