# -*- coding: utf-8 -*-
"""
GeoStudio - Stage-Storage & Capacity Curve Plot Canvas
High-DPI 2D Interactive Plotter rendering Elevation vs. Cumulative Volume and Surface Area.
"""

from typing import List, Optional
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QLinearGradient, QFont,
    QPainterPath
)

from core.earthworks.volumetrics import StageStorageStep


class StageStoragePlotCanvas(QWidget):
    """Interactive high-DPI 2D Stage-Storage Curve plotter using QPainter."""

    hover_step_changed = pyqtSignal(object)  # Emits StageStorageStep on hover

    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps: List[StageStorageStep] = []
        self.hover_idx = -1
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(260)

    def set_data(self, steps: List[StageStorageStep]):
        self.steps = steps
        self.hover_idx = -1
        self.update()

    def mouseMoveEvent(self, event):
        if not self.steps or len(self.steps) < 2:
            return
        left = 75
        right = self.width() - 30
        w = right - left
        if w <= 0:
            return
        rel_x = max(0, min(w, event.x() - left))
        pct = rel_x / w
        idx = int(round(pct * (len(self.steps) - 1)))
        idx = max(0, min(len(self.steps) - 1, idx))
        if idx != self.hover_idx:
            self.hover_idx = idx
            self.hover_step_changed.emit(self.steps[idx])
            self.update()

    def leaveEvent(self, event):
        self.hover_idx = -1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#0f172a"))

        if not self.steps or len(self.steps) < 2:
            painter.setPen(QColor("#64748b"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(
                rect,
                Qt.AlignCenter,
                "Select a DEM and run Volumetric Analysis to display Stage-Storage & Capacity Curves."
            )
            return

        left = 80
        right = rect.width() - 40
        top = 35
        bottom = rect.height() - 45

        plot_w = right - left
        plot_h = bottom - top

        elevations = [s.elevation_m for s in self.steps]
        volumes = [s.cumulative_capacity_m3 for s in self.steps]

        min_e, max_e = min(elevations), max(elevations)
        min_v, max_v = min(volumes), max(volumes)

        if max_e == min_e: max_e += 1.0
        if max_v == min_v: max_v += 1.0

        # Draw Grid Lines
        grid_pen = QPen(QColor("#1e293b"), 1, Qt.DashLine)
        painter.setPen(grid_pen)
        num_grid_y = 5
        for i in range(num_grid_y + 1):
            y = bottom - (i / num_grid_y) * plot_h
            painter.drawLine(int(left), int(y), int(right), int(y))
            e_val = min_e + (i / num_grid_y) * (max_e - min_e)
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(QRectF(5, y - 8, left - 12, 16), Qt.AlignRight | Qt.AlignVCenter, f"{e_val:.1f} m")
            painter.setPen(grid_pen)

        num_grid_x = 4
        for i in range(num_grid_x + 1):
            x = left + (i / num_grid_x) * plot_w
            painter.drawLine(int(x), int(top), int(x), int(bottom))
            v_val = min_v + (i / num_grid_x) * (max_v - min_v)
            v_str = f"{v_val / 1e6:.2f}M m³" if max_v >= 1e6 else f"{v_val:,.0f} m³"
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(QRectF(x - 45, bottom + 8, 90, 18), Qt.AlignCenter, v_str)
            painter.setPen(grid_pen)

        # Plot Curves: Volume Curve (Cyan)
        poly_points = []
        curve_path = QPainterPath()

        for idx, s in enumerate(self.steps):
            x = left + (s.cumulative_capacity_m3 - min_v) / (max_v - min_v) * plot_w
            y = bottom - (s.elevation_m - min_e) / (max_e - min_e) * plot_h
            pt = QPointF(x, y)
            poly_points.append(pt)
            if idx == 0:
                curve_path.moveTo(pt)
            else:
                curve_path.lineTo(pt)

        # Fill under curve
        fill_path = QPainterPath(curve_path)
        fill_path.lineTo(QPointF(poly_points[-1].x(), bottom))
        fill_path.lineTo(QPointF(poly_points[0].x(), bottom))
        fill_path.closeSubpath()

        grad = QLinearGradient(0, top, 0, bottom)
        grad.setColorAt(0.0, QColor(6, 182, 212, 120))
        grad.setColorAt(1.0, QColor(6, 182, 212, 10))
        painter.fillPath(fill_path, QBrush(grad))

        # Stroke Volume Curve
        curve_pen = QPen(QColor("#06b6d4"), 2.5)
        painter.setPen(curve_pen)
        painter.drawPath(curve_path)

        # Draw Points
        for pt in poly_points:
            painter.setBrush(QBrush(QColor("#0891b2")))
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.drawEllipse(pt, 3, 3)

        # Title & Legend
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QColor("#38bdf8"))
        painter.drawText(QRectF(left, 8, 250, 20), Qt.AlignLeft, "📈 Cumulative Volume Capacity (m³)")

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#64748b"))
        painter.drawText(QRectF(right - 220, 8, 220, 20), Qt.AlignRight, "Elevation (Y) vs Volume (X)")

        # Hover Inspector
        if 0 <= self.hover_idx < len(self.steps):
            h_step = self.steps[self.hover_idx]
            hx = poly_points[self.hover_idx].x()
            hy = poly_points[self.hover_idx].y()

            # Crosshair
            painter.setPen(QPen(QColor("#f59e0b"), 1, Qt.DashLine))
            painter.drawLine(int(hx), int(top), int(hx), int(bottom))
            painter.drawLine(int(left), int(hy), int(right), int(hy))

            # Highlighted Dot
            painter.setBrush(QBrush(QColor("#f59e0b")))
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawEllipse(QPointF(hx, hy), 6, 6)

            # Tooltip Box
            v_fmt = f"{h_step.cumulative_capacity_m3:,.1f} m³"
            a_fmt = f"{h_step.surface_area_ha:,.2f} ha ({h_step.surface_area_m2:,.0f} m²)"
            tip_txt = f"Elev: {h_step.elevation_m:.2f} m\nVol: {v_fmt}\nArea: {a_fmt}"

            tw, th = 175, 54
            tx = hx + 12
            if tx + tw > right: tx = hx - tw - 12
            ty = hy - th - 8
            if ty < top: ty = hy + 12

            tip_rect = QRectF(tx, ty, tw, th)
            painter.setBrush(QBrush(QColor(15, 23, 42, 235)))
            painter.setPen(QPen(QColor("#f59e0b"), 1.5))
            painter.drawRoundedRect(tip_rect, 5, 5)

            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(tip_rect.adjusted(6, 4, -6, -4), Qt.AlignLeft | Qt.AlignVCenter, tip_txt)
