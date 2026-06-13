from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QPointF, QRect, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget


SCRIPT_DIR = Path(__file__).resolve().parent
RUN_SECONDS = float(os.environ.get("MSMASCOT_RUN_SECONDS", "60"))
LOOP_SECONDS = float(os.environ.get("MSMASCOT_LOOP_SECONDS", "2.2"))
CAPTIONS = {
    "hello": "Приветик",
    "update": "Обновление",
}
CAPTION = os.environ.get("MSMASCOT_CAPTION", "").strip()
if not CAPTION:
    CAPTION = CAPTIONS.get(os.environ.get("MSMASCOT_CAPTION_KEY", "").strip(), "")


class SpriteSequenceWindow(QWidget):
    def __init__(self, frames_dir: Path) -> None:
        super().__init__()
        self.frames = [QPixmap(str(path)) for path in sorted(frames_dir.glob("frame_*.png"))]
        self.frames = [frame for frame in self.frames if not frame.isNull()]
        if not self.frames:
            raise RuntimeError(f"No frames in {frames_dir}")

        self.started = time.monotonic()
        self.frame_index = 0
        self.drag_anchor: QPointF | None = None

        self.setWindowTitle("MSLaunch sprite sequence")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(
            int(os.environ.get("MSMASCOT_WINDOW_WIDTH", "220")),
            int(os.environ.get("MSMASCOT_WINDOW_HEIGHT", "220")),
        )
        self.move(660, 230)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def tick(self) -> None:
        elapsed = time.monotonic() - self.started
        if elapsed >= RUN_SECONDS:
            self.timer.stop()
            self.close()
            QApplication.instance().quit()
            return
        phase = (elapsed % LOOP_SECONDS) / LOOP_SECONDS
        self.frame_index = int(phase * len(self.frames)) % len(self.frames)
        self.update()

    def paintEvent(self, _event) -> None:
        pixmap = self.frames[self.frame_index]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = self.sprite_rect(pixmap)
        if CAPTION:
            painter.setFont(painter.font())
            font = painter.font()
            font.setFamily("Segoe UI")
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            caption_rect = QRect(0, 10, self.width(), 28)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(caption_rect.translated(1, 1), Qt.AlignmentFlag.AlignCenter, CAPTION)
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(caption_rect, Qt.AlignmentFlag.AlignCenter, CAPTION)
        if os.environ.get("MSMASCOT_RUNTIME_OUTLINE", "0") == "1":
            painter.setOpacity(0.28)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                painter.drawPixmap(rect.translated(dx, dy), pixmap)
            painter.setOpacity(1.0)
        painter.drawPixmap(rect, pixmap)

    def sprite_rect(self, pixmap: QPixmap) -> QRect:
        max_h = int(os.environ.get("MSMASCOT_MAX_HEIGHT", "150"))
        max_w = int(os.environ.get("MSMASCOT_MAX_WIDTH", "175"))
        scale = min(max_w / max(1, pixmap.width()), max_h / max(1, pixmap.height()))
        width = int(pixmap.width() * scale)
        height = int(pixmap.height() * scale)
        top_offset = 34 if CAPTION else 0
        area_h = self.height() - top_offset
        return QRect((self.width() - width) // 2, top_offset + (area_h - height) // 2, width, height)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            QApplication.instance().quit()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_anchor = event.globalPosition() - QPointF(self.frameGeometry().topLeft())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_anchor is not None:
            self.move((event.globalPosition() - self.drag_anchor).toPoint())

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        self.drag_anchor = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            QApplication.instance().quit()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: sprite_sequence_player.py <frames_dir>")
        return 2
    app = QApplication(sys.argv)
    window = SpriteSequenceWindow(Path(sys.argv[1]))
    window.show()
    return app.exec()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
