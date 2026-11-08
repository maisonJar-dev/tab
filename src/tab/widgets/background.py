"""The 'Hard Work is the Goal' wall behind tab's main screen.

Drop-in for src/tab/widgets/background.py.

Renders assets/background.svg to cover the widget (centred, cropping only
empty wall on unusual window shapes), then fades the artwork with a
translucent coat of the wall colour so it stays in the background.
The result is cached and only rebuilt on resize, so painting is just a blit.

Usage: make it the main window's central widget and put the real UI inside
it, with transparent backgrounds:

    wall = WallBackground()
    layout = QHBoxLayout(wall)
    layout.addWidget(sidebar)
    layout.addWidget(stack)
    window.setCentralWidget(wall)
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

ASSET = Path(__file__).resolve().parent.parent / "assets" / "background.svg"
FALLBACK = QColor("#151516")  # wall colour if the asset is missing
ARTWORK_FADE_ALPHA = 140  # 0-255; a coat of FALLBACK over the artwork, higher = fainter


class WallBackground(QWidget):
    def __init__(self, parent: QWidget | None = None, asset: str | os.PathLike = ASSET):
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent)  # we paint every pixel
        self._svg = QSvgRenderer(str(asset), self)
        self._cache: QPixmap | None = None
        self._cache_size = QSize()

    def _rebuild(self):
        ratio = self.devicePixelRatioF()
        px = QPixmap(self.size() * ratio)
        px.setDevicePixelRatio(ratio)
        px.fill(FALLBACK)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        if self._svg.isValid():
            # cover: scale to fill, centred, preserving aspect ratio
            vb = self._svg.viewBoxF()
            k = max(self.width() / vb.width(), self.height() / vb.height())
            w, h = vb.width() * k, vb.height() * k
            self._svg.render(p, QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h))
        fade_colour = QColor(FALLBACK)
        fade_colour.setAlpha(ARTWORK_FADE_ALPHA)
        p.fillRect(self.rect(), fade_colour)
        p.end()
        self._cache, self._cache_size = px, self.size()

    def paintEvent(self, _):
        if self._cache is None or self._cache_size != self.size():
            self._rebuild()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)
        p.end()
