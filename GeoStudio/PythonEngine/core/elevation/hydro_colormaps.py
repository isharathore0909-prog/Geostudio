# -*- coding: utf-8 -*-
"""
GeoStudio - Hydrology & Catchment Colormaps
Colormaps for watershed delineation basins, D8 flow direction, flow accumulation, and stream network orders.
"""

import numpy as np
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsRasterLayer, QgsSingleBandPseudoColorRenderer, QgsColorRampShader,
    QgsRasterShader, QgsPalettedRasterRenderer
)
from .elevation_stats import get_valid_elevation_stats, apply_resampling


def apply_watershed_colormap(layer: QgsRasterLayer, band: int = 1) -> bool:
    """Applies categorical paletted renderer to delineated catchment basins."""
    if not layer or not layer.isValid():
        return False
    try:
        HEX_PALETTE = [
            "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4",
            "#ec4899", "#84cc16", "#f97316", "#14b8a6", "#6366f1", "#a855f7",
            "#e11d48", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777",
            "#65a30d", "#ea580c", "#0d9488", "#4f46e5", "#9333ea", "#be123c",
            "#047857", "#b45309", "#6d28d9", "#0e7490", "#be185d", "#4d7c0f",
            "#c2410c", "#0f766e", "#4338ca", "#7e22ce", "#9f1239", "#065f46",
            "#92400e", "#5b21b6", "#155e75", "#9d174d", "#3f6212", "#9a3412",
            "#115e59", "#3730a3", "#6b21a8", "#881337", "#064e3b", "#78350f",
            "#4c1d95", "#164e63", "#831843", "#365314", "#7c2d12", "#134e4a",
            "#312e81", "#581c87", "#701a75", "#0284c7", "#22c55e", "#eab308",
            "#e879f9", "#38bdf8", "#4ade80", "#facc15"
        ]

        classes = [QgsPalettedRasterRenderer.Class(0, QColor(0, 0, 0, 0), "NoData / Outlet")]
        stats = get_valid_elevation_stats(layer, band)
        max_basin = int(stats.get("max", 64)) if stats else 64
        max_basin = max(max_basin, 64)

        for val in range(1, max_basin + 1):
            hex_c = HEX_PALETTE[(val - 1) % len(HEX_PALETTE)]
            classes.append(QgsPalettedRasterRenderer.Class(val, QColor(hex_c), f"Basin #{val}"))

        renderer = QgsPalettedRasterRenderer(layer.dataProvider(), band, classes)
        layer.setRenderer(renderer)
        apply_resampling(layer, mode="nearest")
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying watershed colormap: {e}")
        return False


def apply_flowdir_colormap(layer: QgsRasterLayer, band: int = 1) -> bool:
    """Applies standard ESRI D8 flow direction 8-class paletted colormap."""
    if not layer or not layer.isValid():
        return False
    try:
        classes = [
            QgsPalettedRasterRenderer.Class(0,   QColor(0, 0, 0, 0),     "NoData / Flat"),
            QgsPalettedRasterRenderer.Class(1,   QColor("#3b82f6"),      "1 - East (0°)"),
            QgsPalettedRasterRenderer.Class(2,   QColor("#06b6d4"),      "2 - South-East (315°)"),
            QgsPalettedRasterRenderer.Class(4,   QColor("#10b981"),      "4 - South (270°)"),
            QgsPalettedRasterRenderer.Class(8,   QColor("#84cc16"),      "8 - South-West (225°)"),
            QgsPalettedRasterRenderer.Class(16,  QColor("#eab308"),      "16 - West (180°)"),
            QgsPalettedRasterRenderer.Class(32,  QColor("#f97316"),      "32 - North-West (135°)"),
            QgsPalettedRasterRenderer.Class(64,  QColor("#ef4444"),      "64 - North (90°)"),
            QgsPalettedRasterRenderer.Class(128, QColor("#a855f7"),      "128 - North-East (45°)"),
        ]
        renderer = QgsPalettedRasterRenderer(layer.dataProvider(), band, classes)
        layer.setRenderer(renderer)
        apply_resampling(layer, mode="nearest")
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying flow direction colormap: {e}")
        return False


def apply_flowaccum_colormap(layer: QgsRasterLayer, band: int = 1) -> bool:
    """Applies high-contrast logarithmic scientific colormap for flow accumulation."""
    if not layer or not layer.isValid():
        return False
    try:
        stats = get_valid_elevation_stats(layer, band)
        max_accum = float(stats.get("max", 1000.0)) if stats else 1000.0
        max_accum = max(max_accum, 10.0)

        log_max = np.log10(max_accum + 1.0)
        items = [
            QgsColorRampShader.ColorRampItem(0.0, QColor(241, 245, 249, 120), "1 cell (Hilltop)"),
            QgsColorRampShader.ColorRampItem(10.0 ** (log_max * 0.25), QColor(147, 197, 253, 200), "Low Accum"),
            QgsColorRampShader.ColorRampItem(10.0 ** (log_max * 0.50), QColor(59, 130, 246, 230),  "Rill / Gully"),
            QgsColorRampShader.ColorRampItem(10.0 ** (log_max * 0.75), QColor(29, 78, 216, 255),  "Tributary"),
            QgsColorRampShader.ColorRampItem(max_accum,                QColor(2, 132, 199, 255),  f"Main River ({max_accum:.0f} cells)"),
        ]
        ramp_shader = QgsColorRampShader(0.0, max_accum)
        ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
        ramp_shader.setClassificationMode(QgsColorRampShader.Continuous)
        ramp_shader.setColorRampItemList(items)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(ramp_shader)

        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, raster_shader)
        layer.setRenderer(renderer)
        apply_resampling(layer, mode="smooth")
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying flow accumulation colormap: {e}")
        return False


def apply_stream_colormap(layer: QgsRasterLayer, band: int = 1) -> bool:
    """Applies discrete Strahler stream order colormap with transparent background."""
    if not layer or not layer.isValid():
        return False
    try:
        classes = [
            QgsPalettedRasterRenderer.Class(0, QColor(0, 0, 0, 0),        "Non-Stream"),
            QgsPalettedRasterRenderer.Class(1, QColor("#0284c7"),        "Order 1 (Headwater)"),
            QgsPalettedRasterRenderer.Class(2, QColor("#0369a1"),        "Order 2 (Creek)"),
            QgsPalettedRasterRenderer.Class(3, QColor("#1d4ed8"),        "Order 3 (Stream)"),
            QgsPalettedRasterRenderer.Class(4, QColor("#1e40af"),        "Order 4 (River)"),
            QgsPalettedRasterRenderer.Class(5, QColor("#1e3a8a"),        "Order 5 (Major River)"),
            QgsPalettedRasterRenderer.Class(6, QColor("#0f172a"),        "Order 6+ (Main Stem)"),
        ]
        renderer = QgsPalettedRasterRenderer(layer.dataProvider(), band, classes)
        layer.setRenderer(renderer)
        apply_resampling(layer, mode="nearest")
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying stream colormap: {e}")
        return False
