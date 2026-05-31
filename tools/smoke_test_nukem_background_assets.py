from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QImage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_DIR = PROJECT_ROOT / "assets" / "backgrounds" / "nukem"
EXPECTED_FILES = (
    "nukem_01_winter.jpg",
    "nukem_02_island.jpg",
    "nukem_03_city.jpg",
    "nukem_04_road.jpg",
    "nukem_05_river.jpg",
    "nukem_06_village.jpg",
)


def main() -> None:
    for filename in EXPECTED_FILES:
        image_path = BACKGROUND_DIR / filename
        assert image_path.is_file(), image_path
        assert image_path.stat().st_size < 350_000, image_path
        image = QImage(str(image_path))
        assert not image.isNull(), image_path
        assert image.width() == 1600, (image_path, image.width())
        assert image.height() == 900, (image_path, image.height())

    print("nukem background assets smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
