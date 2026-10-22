# -*- coding: utf-8 -*-
"""
GeoStudio - Elevation Profile Plot Canvas
High-DPI 2D Elevation Profile plotter widget with gradient fill,
elevation & distance axes, and interactive hover inspector.
"""

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QLinearGradient, QFont,
    QPainterPath
)


class ElevationPlotCanvas(QWidget):
    """Custom high-DPI 2D Elevation Profile plotter using QPainter."""

    hover_point_changed = pyqtSignal(float, float)  # (distance, elevation)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.distances = []   # in meters
        self.elevations = []  # in meters
        self.hover_idx = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(280)

    def set_data(self, distances, elevations):
        self.distances = distances
        self.elevations = elevations
        self.hover_idx = -1
        self.update()

    def mouseMoveEvent(self, event):
        if not self.distances or not self.elevations:
            return
        w = self.width() - 80
        if w <= 0:
            return
        rel_x = max(0, min(w, event.x() - 60))
        pct = rel_x / w
        idx = int(pct * (len(self.distances) - 1))
        if 0 <= idx < len(self.distances):
            self.hover_idx = idx
            self.hover_point_changed.emit(self.distances[idx], self.elevations[idx])
            self.update()

    def leaveEvent(self, event):
        self.hover_idx = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#0f172a"))

        if not self.distances or not self.elevations or len(self.distances) < 2:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(
                rect,
                Qt.AlignCenter,
                "Click 'Draw Transect on Map' and draw a line across terrain to generate elevation profile."
            )
            return

        left = 65
        right = rect.width() - 25
        top = 25
        bottom = rect.height() - 40

        plot_w = right - left
        plot_h = bottom - top

        min_d, max_d = min(self.distances), max(self.distances)
        min_e, max_e = min(self.elevations), max(self.elevations)

        e_range = max(1.0, max_e - min_e)
        min_e_plot = min_e - e_range * 0.08
        max_e_plot = max_e + e_range * 0.08
        e_range_plot = max_e_plot - min_e_plot
        d_range = max(1.0, max_d - min_d)

        # ── 1. Gridlines & Axes ────────────────────────────
        pen_grid = QPen(QColor("#334155"), 1, Qt.DashLine)
        pen_text = QPen(QColor("#94a3b8"))
        painter.setFont(QFont("Segoe UI", 8))

        num_y_ticks = 5
        for i in range(num_y_ticks + 1):
            y_val = min_e_plot + (e_range_plot * i / num_y_ticks)
            py = bottom - (i / num_y_ticks) * plot_h
            painter.setPen(pen_grid)
            painter.drawLine(int(left), int(py), int(right), int(py))
            painter.setPen(pen_text)
            painter.drawText(5, int(py) + 4, 55, 15, Qt.AlignRight, f"{y_val:.1f} m")

        num_x_ticks = 6
        for i in range(num_x_ticks + 1):
            d_val = min_d + (d_range * i / num_x_ticks)
            px = left + (i / num_x_ticks) * plot_w
            painter.setPen(pen_grid)
            painter.drawLine(int(px), int(top), int(px), int(bottom))
            painter.setPen(pen_text)
            d_str = f"{d_val/1000:.2f} km" if max_d >= 1000 else f"{d_val:.0f} m"
            painter.drawText(int(px) - 30, int(bottom) + 8, 60, 18, Qt.AlignCenter, d_str)

        # ── 2. Profile Area & Curve ────────────────────────
        path_area = QPainterPath()
        path_line = QPainterPath()

        start_x = left + ((self.distances[0] - min_d) / d_range) * plot_w
        start_y = bottom - ((self.elevations[0] - min_e_plot) / e_range_plot) * plot_h

        path_area.moveTo(start_x, bottom)
        path_area.lineTo(start_x, start_y)
        path_line.moveTo(start_x, start_y)

        for d, e in zip(self.distances[1:], self.elevations[1:]):
            px = left + ((d - min_d) / d_range) * plot_w
            py = bottom - ((e - min_e_plot) / e_range_plot) * plot_h
            path_area.lineTo(px, py)
            path_line.lineTo(px, py)

        last_x = left + ((self.distances[-1] - min_d) / d_range) * plot_w
        path_area.lineTo(last_x, bottom)
        path_area.closeSubpath()

        grad = QLinearGradient(0, top, 0, bottom)
        grad.setColorAt(0.0, QColor(16, 185, 129, 160))  # Emerald top
        grad.setColorAt(0.7, QColor(14, 165, 233, 80))   # Sky blue mid
        grad.setColorAt(1.0, QColor(15, 23, 42, 20))     # Dark bottom
        painter.fillPath(path_area, QBrush(grad))

        pen_curve = QPen(QColor("#10b981"), 2.5)
        painter.setPen(pen_curve)
        painter.drawPath(path_line)

        # ── 3. Hover Indicator ─────────────────────────────
        if 0 <= self.hover_idx < len(self.distances):
            hd = self.distances[self.hover_idx]
            he = self.elevations[self.hover_idx]
            hx = left + ((hd - min_d) / d_range) * plot_w
            hy = bottom - ((he - min_e_plot) / e_range_plot) * plot_h

            painter.setPen(QPen(QColor("#f59e0b"), 1, Qt.DashLine))
            painter.drawLine(int(hx), int(top), int(hx), int(bottom))

            painter.setBrush(QBrush(QColor("#f59e0b")))
            painter.setPen(QPen(Qt.white, 2))
            painter.drawEllipse(QPointF(hx, hy), 5, 5)

            badge_text = (
                f"Dist: {hd/1000:.2f} km | Elev: {he:.1f} m"
                if max_d >= 1000 else f"Dist: {hd:.1f} m | Elev: {he:.1f} m"
            )
            painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(30, 41, 59, 230)))
            badge_w = 170
            badge_x = min(right - badge_w, max(left, hx - badge_w / 2))
            badge_y = max(top + 5, hy - 30)
            painter.drawRoundedRect(QRectF(badge_x, badge_y, badge_w, 22), 4, 4)
            painter.setPen(QPen(QColor("#f8fafc")))
            painter.drawText(QRectF(badge_x, badge_y, badge_w, 22), Qt.AlignCenter, badge_text)
