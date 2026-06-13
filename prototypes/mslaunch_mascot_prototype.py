from __future__ import annotations

import os
import sys
import tempfile
from collections import deque
from pathlib import Path

from PIL import Image, ImageSequence
from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_CANDIDATES = (
    SCRIPT_DIR / "mslaunch_mascot_source.gif",
    Path.home() / "Desktop" / "mslaunch_mascot_source.gif",
    Path(r"C:\Users\Li2Fox\Desktop\Новая папка\assets\shigure-ui-dance.gif"),
    Path(r"C:\Users\Li2Fox\Documents\Лаунчер\assets\mascots\source\shigure_transparent_sticker.gif"),
)
LOCK_HANDLE = None


def acquire_single_instance_lock():
    if os.name != "nt":
        return object()
    import msvcrt

    lock_path = Path(tempfile.gettempdir()) / "mslaunch_mascot_prototype.lock"
    handle = open(lock_path, "w", encoding="utf-8")
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def find_source() -> Path:
    for path in SOURCE_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("Не нашёл GIF-заготовку рядом со скриптом или в проекте.")


def estimate_background(frame: Image.Image) -> tuple[int, int, int]:
    rgb = frame.convert("RGB")
    width, height = rgb.size
    samples: list[tuple[int, int, int]] = []
    for x in range(width):
        samples.append(rgb.getpixel((x, 0)))
        samples.append(rgb.getpixel((x, height - 1)))
    for y in range(height):
        samples.append(rgb.getpixel((0, y)))
        samples.append(rgb.getpixel((width - 1, y)))
    buckets: dict[tuple[int, int, int], int] = {}
    for r, g, b in samples:
        key = (r // 8 * 8, g // 8 * 8, b // 8 * 8)
        buckets[key] = buckets.get(key, 0) + 1
    return max(buckets, key=buckets.get)


def remove_small_alpha_islands(image: Image.Image, min_area: int = 24) -> Image.Image:
    width, height = image.size
    pixels = image.load()
    seen = bytearray(width * height)

    for start_y in range(height):
        for start_x in range(width):
            start_index = start_y * width + start_x
            if seen[start_index] or pixels[start_x, start_y][3] == 0:
                continue
            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            seen[start_index] = 1
            component: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    index = ny * width + nx
                    if seen[index] or pixels[nx, ny][3] == 0:
                        continue
                    seen[index] = 1
                    queue.append((nx, ny))
            if len(component) < min_area:
                for x, y in component:
                    r, g, b, _a = pixels[x, y]
                    pixels[x, y] = (r, g, b, 0)
    return image


def remove_connected_background(
    frame: Image.Image,
    bg: tuple[int, int, int],
    tolerance: int = 82,
) -> Image.Image:
    rgba = frame.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    seen = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def distance_to_bg(x: int, y: int) -> int:
        r, g, b, _a = pixels[x, y]
        return max(abs(r - bg[0]), abs(g - bg[1]), abs(b - bg[2]))

    def close_to_bg(x: int, y: int) -> bool:
        _r, _g, _b, a = pixels[x, y]
        return a == 0 or distance_to_bg(x, y) <= tolerance

    def add(x: int, y: int) -> None:
        index = y * width + x
        if seen[index] or not close_to_bg(x, y):
            return
        seen[index] = 1
        queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        if x > 0:
            add(x - 1, y)
        if x + 1 < width:
            add(x + 1, y)
        if y > 0:
            add(x, y - 1)
        if y + 1 < height:
            add(x, y + 1)

    for y in range(height):
        for x in range(width):
            if seen[y * width + x]:
                pixels[x, y] = (0, 0, 0, 0)

    # Feather only pixels that touch the removed outer background. Applying this
    # globally eats bright hair/face pixels, which is exactly what we avoid here.
    soft_start = tolerance - 6
    soft_end = tolerance + 46
    for y in range(1, height - 1):
        row = y * width
        for x in range(1, width - 1):
            if seen[row + x]:
                continue
            if not (
                seen[row + x - 1]
                or seen[row + x + 1]
                or seen[row - width + x]
                or seen[row + width + x]
                or seen[row - width + x - 1]
                or seen[row - width + x + 1]
                or seen[row + width + x - 1]
                or seen[row + width + x + 1]
            ):
                continue
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue
            dist = distance_to_bg(x, y)
            if dist <= soft_start:
                pixels[x, y] = (r, g, b, max(0, int(a * 0.12)))
            elif dist < soft_end:
                keep = (dist - soft_start) / max(1, soft_end - soft_start)
                pixels[x, y] = (r, g, b, max(int(a * 0.35), int(a * keep)))

    return remove_small_alpha_islands(rgba)


def fit_frame(
    frame: Image.Image,
    bg: tuple[int, int, int],
    max_width: int = 245,
    max_height: int = 238,
) -> Image.Image:
    image = remove_connected_background(frame, bg)
    width, height = image.size
    scale = min(max_width / max(width, 1), max_height / max(height, 1), 1.0)
    target = (max(1, int(width * scale)), max(1, int(height * scale)))
    if target != image.size:
        image = image.resize(target, Image.Resampling.LANCZOS)
    return image


def load_frames(source: Path) -> tuple[list[Image.Image], list[int]]:
    with Image.open(source) as gif:
        frames: list[Image.Image] = []
        durations: list[int] = []
        global_bg = estimate_background(next(ImageSequence.Iterator(gif)).copy())
        for source_frame in ImageSequence.Iterator(gif):
            frames.append(fit_frame(source_frame.copy(), global_bg))
            duration = int(source_frame.info.get("duration", 70) or 70)
            durations.append(max(35, min(duration, 140)))
        if not frames:
            raise RuntimeError("В GIF нет кадров.")
        return frames, durations


def pixmap_from_image(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, width, height, width * 4, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


class MascotPrototype(QWidget):
    def __init__(self, source: Path) -> None:
        super().__init__()
        self.setWindowTitle("MSLaunch mascot prototype")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        frames_raw, self.durations = load_frames(source)
        self.frames = [pixmap_from_image(frame) for frame in frames_raw]
        self.index = 0
        self.drag_anchor: QPoint | None = None
        self.message = "Обновление"
        self.text_height = 44
        max_width = max(frame.width() for frame in self.frames)
        max_height = max(frame.height() for frame in self.frames)
        self.setFixedSize(max(285, max_width + 24), self.text_height + max_height + 12)
        self.move(620, 230)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(self.durations[0])

    def next_frame(self) -> None:
        self.index = (self.index + 1) % len(self.frames)
        self.timer.start(self.durations[self.index])
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        font = QFont("Segoe UI", 15, QFont.Weight.Bold)
        painter.setFont(font)
        text_rect = QRect(0, 0, self.width(), self.text_height)
        painter.setPen(QColor(0, 0, 0, 180))
        painter.drawText(text_rect.translated(2, 2), Qt.AlignmentFlag.AlignCenter, self.message)
        painter.setPen(QColor(230, 255, 246))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.message)

        frame = self.frames[self.index]
        x = (self.width() - frame.width()) // 2
        y = self.text_height
        painter.drawPixmap(x, y, frame)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_anchor = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_anchor is None:
            return
        self.move(event.globalPosition().toPoint() - self.drag_anchor)

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        self.drag_anchor = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()


def main() -> int:
    global LOCK_HANDLE
    LOCK_HANDLE = acquire_single_instance_lock()
    if LOCK_HANDLE is None:
        return 0

    source = find_source()
    if "--self-test" in sys.argv:
        frames, _durations = load_frames(source)
        print(f"OK: {source} -> {len(frames)} frames")
        return 0
    app = QApplication(sys.argv)
    mascot = MascotPrototype(source)
    mascot.show()
    return app.exec()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
