from __future__ import annotations

from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageSequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "assets" / "mascots" / "source"
PROCESSED_DIR = PROJECT_ROOT / "assets" / "mascots" / "processed"

MASCOTS = (
    ("shigure_transparent_sticker.gif", "shigure_transparent_sticker", 245, 190),
    ("shigure_original_wide.gif", "shigure_original_wide", 245, 190),
    ("shigure_dance_tall.gif", "shigure_dance_tall", 170, 300),
    ("shigure_vtuber.gif", "shigure_vtuber", 190, 190),
    ("shigure_ui_jp.gif", "shigure_ui_jp", 190, 190),
)


def estimate_background_color(rgb: Image.Image) -> tuple[int, int, int]:
    width, height = rgb.size
    pixels = rgb.load()
    samples: list[tuple[int, int, int]] = []
    for x in range(width):
        samples.append(pixels[x, 0])
        samples.append(pixels[x, height - 1])
    for y in range(height):
        samples.append(pixels[0, y])
        samples.append(pixels[width - 1, y])
    quantized = [((r // 8) * 8, (g // 8) * 8, (b // 8) * 8) for r, g, b in samples]
    return Counter(quantized).most_common(1)[0][0]


def connected_background_mask(image: Image.Image, threshold: int = 42) -> Image.Image:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    background = estimate_background_color(rgb)
    visited = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def is_background(x: int, y: int) -> bool:
        red, green, blue = pixels[x, y]
        return (
            abs(red - background[0])
            + abs(green - background[1])
            + abs(blue - background[2])
            <= threshold
        )

    def enqueue(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= width or y >= height:
            return
        index = y * width + x
        if visited[index] or not is_background(x, y):
            return
        visited[index] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        enqueue(x + 1, y)
        enqueue(x - 1, y)
        enqueue(x, y + 1)
        enqueue(x, y - 1)

    return Image.frombytes("L", (width, height), bytes(255 if value else 0 for value in visited))


def fit_size(size: tuple[int, int], max_width: int, max_height: int) -> tuple[int, int]:
    width, height = size
    scale = min(max_width / max(width, 1), max_height / max(height, 1), 1.0)
    return max(1, int(width * scale)), max(1, int(height * scale))


def clean_frame(frame: Image.Image, max_width: int, max_height: int) -> Image.Image:
    rgba = frame.convert("RGBA")
    background = connected_background_mask(rgba)
    # Expand the removed background slightly, then feather by less than a pixel.
    background = background.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.45))
    alpha = ImageChops.invert(background)
    rgba.putalpha(alpha)
    target_size = fit_size(rgba.size, max_width, max_height)
    if target_size != rgba.size:
        rgba = rgba.resize(target_size, Image.Resampling.LANCZOS)
    return rgba


def process_mascot(source_name: str, output_name: str, max_width: int, max_height: int) -> None:
    source_path = SOURCE_DIR / source_name
    output_dir = PROCESSED_DIR / output_name
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_frame in output_dir.glob("frame_*.png"):
        stale_frame.unlink()

    with Image.open(source_path) as image:
        for index, frame in enumerate(ImageSequence.Iterator(image)):
            cleaned = clean_frame(frame, max_width, max_height)
            cleaned.save(output_dir / f"frame_{index:04d}.png", optimize=True)

    print(f"{output_name}: {index + 1} frames")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for mascot in MASCOTS:
        process_mascot(*mascot)


if __name__ == "__main__":
    main()
