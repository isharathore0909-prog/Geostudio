# -*- coding: utf-8 -*-
"""
GeoStudio - Elevation & Raster Colormaps Engine
Renders thematic colormaps, shaded relief palettes, and analytical color scales on raster layers.
"""

import numpy as np
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsRasterLayer, QgsSingleBandPseudoColorRenderer, QgsColorRampShader,
    QgsRasterShader, QgsSingleBandGrayRenderer, QgsContrastEnhancement
)

from .elevation_palettes import ELEVATION_PRESETS
from .elevation_stats import get_valid_elevation_stats, apply_resampling
from .hydro_colormaps import (
    apply_watershed_colormap,
    apply_flowdir_colormap,
    apply_flowaccum_colormap,
    apply_stream_colormap
)


def apply_elevation_colormap(
    layer: QgsRasterLayer,
    preset_key: str = "GLOBAL_MAPPER_ATLAS",
    band: int = 1,
    min_val: float = None,
    max_val: float = None,
    invert: bool = False,
    enable_bilinear: bool = True
) -> bool:
    """Applies flat 2D Topographic / Elevation Color Ramp."""
    if not layer or not layer.isValid():
        return False

    preset = ELEVATION_PRESETS.get(preset_key, ELEVATION_PRESETS["GLOBAL_MAPPER_ATLAS"])
    stats = get_valid_elevation_stats(layer, band)

    if min_val is None or max_val is None:
        min_val = stats["min"] if stats else 0.0
        max_val = stats["max"] if stats else 100.0

    if min_val >= max_val:
        max_val = min_val + 10.0

    val_range = max_val - min_val

    ramp_shader = QgsColorRampShader(min_val, max_val)
    ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
    ramp_shader.setClassificationMode(QgsColorRampShader.Continuous)

    raw_stops = preset["stops"]
    if invert:
        raw_stops = list(reversed(raw_stops))

    items = []
    for stop_frac, hex_color, label in raw_stops:
        actual_val = min_val + (stop_frac * val_range)
        c = QColor(hex_color)
        items.append(QgsColorRampShader.ColorRampItem(actual_val, c, f"{actual_val:.1f} m"))

    ramp_shader.setColorRampItemList(items)
    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(ramp_shader)

    renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, raster_shader)
    layer.setRenderer(renderer)
    apply_resampling(layer)
    layer.triggerRepaint()
    return True


def apply_scientific_palette(layer: QgsRasterLayer, palette_name: str = "TURBO", band: int = 1) -> bool:
    """Alias to apply scientific elevation palettes (TURBO, VIRIDIS, GLOBAL_MAPPER_ATLAS, etc.)."""
    key = palette_name.upper()
    if key not in ELEVATION_PRESETS:
        key = "TURBO" if "TURB" in key else ("VIRIDIS" if "VIRID" in key else "GLOBAL_MAPPER_ATLAS")
    return apply_elevation_colormap(layer, preset_key=key, band=band)


def apply_grayscale_contrast(
    layer: QgsRasterLayer,
    band: int = 1,
    min_val: float = None,
    max_val: float = None,
    stretch_type: str = "cumulative_cut"
) -> bool:
    """Applies grayscale contrast."""
    if not layer or not layer.isValid():
        return False

    try:
        stats = get_valid_elevation_stats(layer, band)
        if min_val is None or max_val is None:
            min_val = stats["p2"]
            max_val = stats["p98"]

        if min_val >= max_val:
            max_val = min_val + 10.0

        renderer = QgsSingleBandGrayRenderer(layer.dataProvider(), band)
        enhancement = QgsContrastEnhancement(layer.dataProvider().dataType(band))
        enhancement.setContrastEnhancementAlgorithm(
            QgsContrastEnhancement.StretchToMinimumMaximum, True
        )
        enhancement.setMinimumValue(min_val)
        enhancement.setMaximumValue(max_val)
        renderer.setContrastEnhancement(enhancement)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying grayscale contrast: {e}")
        return False


def apply_aspect_colormap(layer: QgsRasterLayer, band: int = 1) -> bool:
    """Applies standard 8-direction aspect color palette (0° - 360° Compass bearings + Flat)."""
    if not layer or not layer.isValid():
        return False
    try:
        items = [
            QgsColorRampShader.ColorRampItem(-1.0, QColor("#808080"), "Flat (-1)"),
            QgsColorRampShader.ColorRampItem(0.0, QColor("#e31a1c"), "North (0°)"),
            QgsColorRampShader.ColorRampItem(22.5, QColor("#ff7f00"), "North-East (22.5°)"),
            QgsColorRampShader.ColorRampItem(67.5, QColor("#ffff33"), "East (67.5°)"),
            QgsColorRampShader.ColorRampItem(112.5, QColor("#4daf4a"), "South-East (112.5°)"),
            QgsColorRampShader.ColorRampItem(157.5, QColor("#377eb8"), "South (157.5°)"),
            QgsColorRampShader.ColorRampItem(202.5, QColor("#984ea3"), "South-West (202.5°)"),
            QgsColorRampShader.ColorRampItem(247.5, QColor("#f781bf"), "West (247.5°)"),
            QgsColorRampShader.ColorRampItem(292.5, QColor("#a65628"), "North-West (292.5°)"),
            QgsColorRampShader.ColorRampItem(337.5, QColor("#e31a1c"), "North (337.5°)"),
            QgsColorRampShader.ColorRampItem(360.0, QColor("#e31a1c"), "North (360°)"),
        ]
        ramp_shader = QgsColorRampShader(0.0, 360.0)
        ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
        ramp_shader.setColorRampItemList(items)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(ramp_shader)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, raster_shader)
        layer.setRenderer(renderer)
        apply_resampling(layer, mode="sharp")
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying aspect colormap: {e}")
        return False


def apply_slope_colormap(layer: QgsRasterLayer, band: int = 1) -> bool:
    """Applies standard Green -> Yellow -> Orange -> Red terrain slope steepness colormap."""
    if not layer or not layer.isValid():
        return False
    try:
        stats = get_valid_elevation_stats(layer, band)
        max_slope = min(float(stats.get("max", 60.0) if stats else 60.0), 90.0)
        if max_slope < 10.0:
            max_slope = 45.0
        items = [
            QgsColorRampShader.ColorRampItem(0.0, QColor("#22c55e"), "0° (Flat)"),
            QgsColorRampShader.ColorRampItem(max_slope * 0.15, QColor("#84cc16"), f"{max_slope * 0.15:.1f}° (Gentle)"),
            QgsColorRampShader.ColorRampItem(max_slope * 0.35, QColor("#eab308"), f"{max_slope * 0.35:.1f}° (Moderate)"),
            QgsColorRampShader.ColorRampItem(max_slope * 0.60, QColor("#f97316"), f"{max_slope * 0.60:.1f}° (Steep)"),
            QgsColorRampShader.ColorRampItem(max_slope, QColor("#ef4444"), f"{max_slope:.1f}° (Extreme)"),
        ]
        ramp_shader = QgsColorRampShader(0.0, max_slope)
        ramp_shader.setColorRampType(QgsColorRampShader.Interpolated)
        ramp_shader.setColorRampItemList(items)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(ramp_shader)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), band, raster_shader)
        layer.setRenderer(renderer)
        apply_resampling(layer, mode="smooth")
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[ElevationStyler] Error applying slope colormap: {e}")
        return False


def apply_cut_fill_colormap(layer: QgsRasterLayer, max_abs_val: float = None, band: int = 1) -> bool:
    """Applies 3-tone diverging colormap to a Cut/Fill difference raster."""
    if not layer or not layer.isValid():
        return False
    try:
        if max_abs_val is None or max_abs_val <= 0.001:
            stats = get_valid_elevation_stats(layer, band)
            if stats and "min" in stats and "max" in stats:
                max_abs_val = max(abs(float(stats["min"])), abs(float(stats["max"])), 1.0)
            else:
                max_abs_val = 10.0

        val = float(max_abs_val)
        items = [
            QgsColorRampShader.ColorRampItem(-val,        QColor(185, 28, 28, 240),  f"Cut -{val:.1f} m (Excavation)"),
            QgsColorRampShader.ColorRampItem(-val * 0.3,  QColor(239, 68, 68, 210),  f"Cut -{val*0.3:.1f} m"),
            QgsColorRampShader.ColorRampItem(-val * 0.02, QColor(254, 202, 202, 120), "Cut -0.05 m"),
            QgsColorRampShader.ColorRampItem(0.0,         QColor(255, 255, 255, 0),   "Daylight (0.0 m)"),
            QgsColorRampShader.ColorRampItem(val * 0.02,  QColor(191, 219, 254, 120), "Fill +0.05 m"),
            QgsColorRampShader.ColorRampItem(val * 0.3,   QColor(59, 130, 246, 210),  f"Fill +{val*0.3:.1f} m"),
            QgsColorRampShader.ColorRampItem(val,         QColor(29, 78, 216, 240),  f"Fill +{val:.1f} m (Embankment)"),
        ]
        ramp_shader = QgsColorRampShader(-val, val)
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
        print(f"[ElevationStyler] Error applying cut & fill colormap: {e}")
        return False
