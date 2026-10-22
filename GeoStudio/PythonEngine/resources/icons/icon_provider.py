# -*- coding: utf-8 -*-
"""
GeoStudio - Modern Vector Icon Provider
Generates crisp, high-detail GIS icons matching Global Mapper & QGIS visual design.
"""

from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QByteArray, QSize, QRectF
from PyQt5.QtSvg import QSvgRenderer

from .svg_map_icons import MAP_SVGS
from .svg_gis_icons import GIS_SVGS

_ICON_CACHE = {}

# Merged master dictionary of SVG icons
_SVGS = {**MAP_SVGS, **GIS_SVGS}


def get_icon(name: str, size: int = 24) -> QIcon:
    """Returns a high-resolution, anti-aliased QIcon with clean margin and background clarity."""
    cache_key = f"{name}_{size}"
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    svg_data = _SVGS.get(name)
    if not svg_data:
        return QIcon()

    renderer = QSvgRenderer(QByteArray(svg_data.strip().encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    padding = 1.5
    target_rect = QRectF(padding, padding, float(size) - (padding * 2.0), float(size) - (padding * 2.0))
    renderer.render(painter, target_rect)
    painter.end()

    icon = QIcon(pixmap)
    _ICON_CACHE[cache_key] = icon
    return icon
