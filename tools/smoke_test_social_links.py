from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import CLIENT_MODE_INDEPENDENT, CLIENT_MODE_NUKEM, get_social_links


def main() -> None:
    nested_config = {
        "social_links": {
            "nukem": {
                "youtube": "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98",
                "discord": "https://discord.com/invite/P35nvXQ",
                "telegram": "",
            }
        }
    }

    assert get_social_links(nested_config, CLIENT_MODE_INDEPENDENT) == {}
    assert get_social_links(nested_config, CLIENT_MODE_NUKEM) == {
        "youtube": "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98",
        "discord": "https://discord.com/invite/P35nvXQ",
    }

    flat_config = {
        "social_links": {
            "youtube": "https://example.com/youtube",
            "discord": {"url": "https://example.com/discord", "enabled": True},
            "telegram": {"url": "https://example.com/telegram", "enabled": False},
            "website": "",
        }
    }

    assert get_social_links(flat_config, CLIENT_MODE_NUKEM) == {
        "youtube": "https://example.com/youtube",
        "discord": "https://example.com/discord",
    }
    assert get_social_links({"social_links": {"nukem": {"youtube": ""}}}, CLIENT_MODE_NUKEM) == {}

    print("social links smoke test: OK")


if __name__ == "__main__":
    main()
