# -*- coding: utf-8 -*-
"""
GeoStudio - Print & Export Overlays
Drawing routines for Title banner, North Arrow compass, and Scale Bar overlays.
"""

import math
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QPen, QBrush
from qgis.core import QgsProject, QgsDistanceArea, QgsPointXY


def draw_title_overlay(painter, w: int, h: int, title: str):
    """Draws map title banner overlay."""
    title_font_size = max(12, int(h / 36))
    painter.setFont(QFont("Segoe UI", title_font_size, QFont.Bold))
    margin = int(w * 0.02)
    box_h = int(title_font_size * 2.2)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
    painter.drawRoundedRect(QRectF(margin, margin, w * 0.45, box_h), 6, 6)

    painter.setPen(QPen(QColor("#cbd5e1"), 1.5))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(QRectF(margin, margin, w * 0.45, box_h), 6, 6)

    painter.setPen(QColor("#0f172a"))
    painter.drawText(QRectF(margin + 12, margin, w * 0.45 - 24, box_h), Qt.AlignVCenter | Qt.AlignLeft, title)


def draw_north_arrow_overlay(painter, w: int, h: int):
    """Draws North Arrow compass rose."""
    size = max(40, int(w * 0.04))
    margin_x = w - size - int(w * 0.03)
    margin_y = int(h * 0.03)

    painter.setPen(QPen(QColor("#94a3b8"), 1))
    painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
    painter.drawEllipse(QRectF(margin_x, margin_y, size, size))

    cx = margin_x + size / 2.0
    cy = margin_y + size / 2.0

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#0f172a")))
    poly_n = [QPointF(cx, margin_y + size * 0.15), QPointF(cx, cy), QPointF(cx - size * 0.18, cy + size * 0.1)]
    painter.drawPolygon(poly_n)

    painter.setBrush(QBrush(QColor("#64748b")))
    poly_nr = [QPointF(cx, margin_y + size * 0.15), QPointF(cx, cy), QPointF(cx + size * 0.18, cy + size * 0.1)]
    painter.drawPolygon(poly_nr)

    painter.setFont(QFont("Segoe UI", max(8, int(size * 0.22)), QFont.Bold))
    painter.setPen(QColor("#0f172a"))
    painter.drawText(QRectF(margin_x, margin_y + size * 0.02, size, size * 0.3), Qt.AlignCenter, "N")


def draw_scalebar_overlay(painter, w: int, h: int, extent, crs):
    """Draws dynamic scalebar overlay scaled to ground width."""
    da = QgsDistanceArea()
    da.setSourceCrs(crs, QgsProject.instance().transformContext())
    da.setEllipsoid("WGS84")

    is_geographic = crs.isGeographic() or (abs(extent.center().x()) <= 180.0 and abs(extent.center().y()) <= 90.0)
    if is_geographic:
        lat = math.radians(extent.center().y())
        meters_per_deg_lon = 111320.0 * math.cos(lat)
        ground_width_m = extent.width() * meters_per_deg_lon
    else:
        p1 = extent.center()
        p2 = QgsPointXY(p1.x() + extent.width(), p1.y())
        ground_width_m = float(da.measureLine(p1, p2))

    bar_len_px = int(w * 0.20)
    bar_len_m = ground_width_m * 0.20

    if bar_len_m >= 1000:
        val = round(bar_len_m / 1000, 1)
        lbl = f"{val} km"
    else:
        val = round(bar_len_m, -1)
        lbl = f"{int(val)} m"

    margin_x = int(w * 0.03)
    margin_y = h - int(h * 0.06)

    painter.setPen(QPen(QColor("#cbd5e1"), 1))
    painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
    painter.drawRoundedRect(QRectF(margin_x - 10, margin_y - 20, bar_len_px + 20, 32), 4, 4)

    painter.setPen(QPen(QColor("#0f172a"), 3))
    painter.drawLine(margin_x, margin_y, margin_x + bar_len_px, margin_y)
    painter.drawLine(margin_x, margin_y - 5, margin_x, margin_y + 5)
    painter.drawLine(margin_x + bar_len_px, margin_y - 5, margin_x + bar_len_px, margin_y + 5)

    painter.setFont(QFont("Segoe UI", max(8, int(h / 70)), QFont.Bold))
    painter.setPen(QColor("#0f172a"))
    painter.drawText(QRectF(margin_x, margin_y - 20, bar_len_px, 16), Qt.AlignCenter, lbl)
