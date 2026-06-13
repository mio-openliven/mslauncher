from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPixmap, QTransform
from PyQt6.QtWidgets import QApplication, QWidget


SCRIPT_DIR = Path(__file__).resolve().parent
ASSET_DIR = SCRIPT_DIR / "assets"
RUN_SECONDS = float(os.environ.get("MSMASCOT_RUN_SECONDS", "60"))
LOOP_SECONDS = float(os.environ.get("MSMASCOT_LOOP_SECONDS", "2.2"))

CHARACTERS = {
    "blonde": {"front": "blonde.png", "back": "blonde_back.png", "title": "Blonde"},
    "cat": {"front": "cat.png", "back": "cat_back.png", "title": "Cat"},
    "asuna": {"front": "asuna_a2.png", "back": "asuna_back.png", "title": "Asuna A2"},
}

SCENES = {
    "dance": "Танец",
    "intro": "Привет",
    "sway": "Сценка",
}


class MascotScene(QWidget):
    def __init__(self, character: str, scene: str) -> None:
        super().__init__()
        self.character = character
        self.scene = scene
        self.started = time.monotonic()
        self.drag_anchor: QPointF | None = None

        char_info = CHARACTERS[character]
        asset_name = char_info["back"] if scene == "sway" else char_info["front"]
        self.pixmap = QPixmap(str(ASSET_DIR / asset_name))
        if self.pixmap.isNull():
            raise RuntimeError(f"Asset not found or broken: {asset_name}")

        self.setWindowTitle(f"MSLaunch mascot {char_info['title']} {scene}")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(420, 560)
        self.move(620, 160)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def tick(self) -> None:
        if time.monotonic() - self.started >= RUN_SECONDS:
            self.timer.stop()
            self.close()
            QApplication.instance().quit()
            return
        self.update()

    def paintEvent(self, _event) -> None:
        elapsed = time.monotonic() - self.started
        loop = (elapsed % LOOP_SECONDS) / LOOP_SECONDS
        wave = math.sin(loop * math.tau)
        wave2 = math.sin(loop * math.tau * 2.0)
        wave3 = math.sin(loop * math.tau * 3.0)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        self.draw_caption(painter, elapsed, wave)

        base_rect = self.sprite_rect()
        transform = QTransform()
        center = base_rect.center()
        transform.translate(center.x(), center.y())

        if self.scene == "dance":
            transform.translate(wave * 12, wave2 * 8)
            transform.rotate(wave * 5.5 + wave3 * 1.8)
            scale = 1.0 + wave2 * 0.028
            transform.scale(scale, scale)
        elif self.scene == "intro":
            hello = min(1.0, elapsed / 0.45)
            slide = (1.0 - hello) * -56
            transform.translate(slide + wave * 4, wave2 * 5)
            transform.rotate(wave * 2.2)
            scale = 0.96 + hello * 0.04 + max(0.0, math.sin(loop * math.tau)) * 0.015
            transform.scale(scale, scale)
        else:
            transform.translate(wave * 9, wave2 * 4)
            transform.rotate(wave * 3.2)
            transform.scale(1.0 + wave * 0.018, 1.0 - wave * 0.012)

        transform.translate(-center.x(), -center.y())
        painter.setTransform(transform)
        painter.drawPixmap(base_rect, self.pixmap)

    def draw_caption(self, painter: QPainter, elapsed: float, wave: float) -> None:
        if self.scene == "dance":
            text = ""
        elif self.scene == "intro":
            text = "Привет!"
        else:
            text = ""
        if not text:
            return
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        alpha = 220 if elapsed > 0.2 else int(220 * elapsed / 0.2)
        rect = QRect(0, 18 + int(wave * 2), self.width(), 36)
        painter.setPen(QColor(0, 0, 0, min(160, alpha)))
        painter.drawText(rect.translated(2, 2), Qt.AlignmentFlag.AlignCenter, text)
        painter.setPen(QColor(230, 255, 246, alpha))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def sprite_rect(self) -> QRect:
        max_w = 320
        max_h = 480
        scale = min(max_w / max(1, self.pixmap.width()), max_h / max(1, self.pixmap.height()))
        width = int(self.pixmap.width() * scale)
        height = int(self.pixmap.height() * scale)
        x = (self.width() - width) // 2
        y = self.height() - height - 18
        if self.scene == "intro":
            y -= 8
        return QRect(x, y, width, height)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_anchor = event.globalPosition() - QPointF(self.frameGeometry().topLeft())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_anchor is None:
            return
        self.move((event.globalPosition() - self.drag_anchor).toPoint())

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        self.drag_anchor = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in CHARACTERS or sys.argv[2] not in SCENES:
        print("Usage: mascot_scene_player.py <blonde|cat|asuna> <dance|intro|sway>")
        return 2
    app = QApplication(sys.argv)
    scene = MascotScene(sys.argv[1], sys.argv[2])
    scene.show()
    return app.exec()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
