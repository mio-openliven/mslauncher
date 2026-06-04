from __future__ import annotations


SUPPORTED_LOADERS = ("vanilla", "fabric", "quilt", "neoforge")
INSTALLABLE_LOADERS = tuple(loader for loader in SUPPORTED_LOADERS if loader != "vanilla")
LOADER_LABELS = {
    "vanilla": "Vanilla",
    "fabric": "Fabric",
    "quilt": "Quilt",
    "neoforge": "NeoForge",
}


def normalize_loader(loader: object) -> str:
    return str(loader or "").strip().lower()


def is_supported_loader(loader: object) -> bool:
    return normalize_loader(loader) in SUPPORTED_LOADERS


def format_supported_loaders() -> str:
    return "vanilla, fabric, quilt, or neoforge"
