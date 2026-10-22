# -*- coding: utf-8 -*-
"""
GeoStudio - On-Canvas Dynamic Color Scale & Legend Overlay Widget
Renders vertical gradient scale bars and discrete categorical legends for all LiDAR & Raster modes.
Supports dragging, real-time min/max values, units (m, °, index, pts/m²), and custom color ramps.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont

from .elevation_legend_data import RAMP_STOPS, configure_lidar_legend, configure_raster_legend


class ElevationLegendWidget(QWidget):
    """
    Floating draggable on-canvas color scale & legend overlay.
    Displays dynamic color ramps or categorical badges for all 19 LiDAR modes and Raster DEMs.
    """

    RAMP_STOPS = RAMP_STOPS

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self.mode = "elevation"
        self.legend_type = "gradient"
        self.title = "Elevation (Z)"
        self.min_val = 0.0
        self.max_val = 100.0
        self.unit_str = "m"
        self.ramp_name = "Turbo"
        self.categories = []
        self.is_active = False
        self.layer_name = ""

        self._dragging = False
        self._drag_start_pos = QPoint()

        self.setFixedWidth(130)
        self.setMinimumHeight(180)
        self.setMaximumHeight(380)

        self.move(14, 14)
        self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            new_pos = event.globalPos() - self._drag_start_pos
            if self.parent():
                parent_rect = self.parent().rect()
                x = max(0, min(new_pos.x(), parent_rect.width() - self.width()))
                y = max(0, min(new_pos.y(), parent_rect.height() - self.height()))
                self.move(x, y)
            else:
                self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def update_from_layer(self, layer, mode: str = None):
        """Automatically determines layer type, inspects active renderer, and configures scale legend."""
        try:
            if not layer or not layer.isValid():
                self.is_active = False
                self.hide()
                return

            from qgis.core import QgsMapLayer
            if hasattr(QgsMapLayer, "PointCloudLayer") and layer.type() == QgsMapLayer.PointCloudLayer:
                self.update_for_lidar_mode(layer, mode)
            elif layer.type() == QgsMapLayer.RasterLayer:
                self.update_for_raster(layer)
            else:
                self.is_active = False
                self.hide()
        except Exception:
            self.is_active = False
            self.hide()

    def update_for_lidar_mode(self, layer, mode: str = None):
        """Sets scale values, units, and colormaps for LiDAR color modes."""
        active = configure_lidar_legend(self, layer, mode)
        if active:
            self.is_active = True
            self.show()
            self.update()
        else:
            self.is_active = False
            self.hide()

    def update_for_raster(self, layer):
        """Updates legend from raster DEM statistics."""
        active = configure_raster_legend(self, layer)
        if active:
            self.is_active = True
            self.show()
            self.update()
        else:
            self.is_active = False
            self.hide()

    def paintEvent(self, event):
        if not self.is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Background card
        painter.setPen(QPen(QColor(15, 23, 42, 220), 1.0))
        painter.setBrush(QBrush(QColor(15, 23, 42, 215)))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8.0, 8.0)

        # Title
        painter.setPen(QColor("#f8fafc"))
        font_title = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font_title)
        painter.drawText(8, 18, self.title)

        if self.legend_type == "gradient":
            self._paint_gradient(painter, w, h)
        elif self.legend_type == "discrete":
            self._paint_discrete(painter, w, h)

    def _paint_gradient(self, painter: QPainter, w: int, h: int):
        bar_x = 12
        bar_y = 30
        bar_w = 16
        bar_h = h - 42

        # Draw vertical gradient bar
        grad = QLinearGradient(0, bar_y, 0, bar_y + bar_h)
        stops = self.RAMP_STOPS.get(self.ramp_name, self.RAMP_STOPS["Turbo"])
        for frac, hex_c in stops:
            grad.setColorAt(1.0 - frac, QColor(hex_c))

        painter.setPen(QPen(QColor("#64748b"), 1.0))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3.0, 3.0)

        # Labels (Max, Mid, Min)
        painter.setPen(QColor("#e2e8f0"))
        font_labels = QFont("Segoe UI", 8, QFont.DemiBold)
        painter.setFont(font_labels)

        lbl_x = bar_x + bar_w + 6

        # Top label (Max)
        max_str = f"{self.max_val:,.1f} {self.unit_str}".strip()
        painter.drawText(lbl_x, bar_y + 10, max_str)

        # Mid label
        mid_val = (self.min_val + self.max_val) / 2.0
        mid_str = f"{mid_val:,.1f} {self.unit_str}".strip()
        painter.drawText(lbl_x, bar_y + (bar_h // 2) + 4, mid_str)

        # Bottom label (Min)
        min_str = f"{self.min_val:,.1f} {self.unit_str}".strip()
        painter.drawText(lbl_x, bar_y + bar_h - 2, min_str)

    def _paint_discrete(self, painter: QPainter, w: int, h: int):
        y = 32
        font_item = QFont("Segoe UI", 8, QFont.Medium)
        painter.setFont(font_item)

        for hex_c, lbl in self.categories:
            painter.setPen(QPen(QColor(hex_c).darker(120), 1.0))
            painter.setBrush(QBrush(QColor(hex_c)))
            painter.drawRoundedRect(10, y - 9, 12, 12, 2.0, 2.0)

            painter.setPen(QColor("#f1f5f9"))
            painter.drawText(28, y + 1, lbl)
            y += 18
            if y > h - 8:
                break
