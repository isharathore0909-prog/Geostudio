# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Renderers Engine
Symbology renderers for ASPRS classification, RGB, CIR, NDVI, scan angle, returns, and QA flags.
"""

from PyQt5.QtGui import QColor
from qgis.core import (
    QgsPointCloudAttributeByRampRenderer,
    QgsPointCloudClassifiedRenderer,
    QgsPointCloudCategory,
    QgsPointCloudRgbRenderer,
    QgsUnitTypes,
    QgsContrastEnhancement,
    Qgis
)

from .lidar_attributes import (
    is_point_cloud, get_attribute_names, find_attr, get_attribute_range, create_shader,
    get_rgb_contrast_range, DEFAULT_MAX_SCREEN_ERROR, DEFAULT_POINT_BUDGET
)
from .lidar_spectral_renderers import (
    apply_cir as _apply_cir,
    apply_ndvi,
    apply_ndwi,
    apply_point_density,
    apply_withheld_flag,
    apply_keypoint_flag,
    apply_overlap_flag,
    apply_return_height_delta
)
from .lidar_attribute_renderers import (
    apply_height_above_ground,
    apply_scan_angle,
    apply_point_source_id,
    apply_source_layer,
    apply_segment,
    apply_point_index
)


def apply_rgb(layer, point_size: float = 3.5) -> bool:
    """Render point cloud using embedded True Color RGB channels with native 8/16-bit dynamic scaling."""
    if not is_point_cloud(layer):
        return False

    r_name = find_attr(layer, ["Red", "red", "ColorRed", "R"])
    g_name = find_attr(layer, ["Green", "green", "ColorGreen", "G"])
    b_name = find_attr(layer, ["Blue", "blue", "ColorBlue", "B"])

    if not (r_name and g_name and b_name):
        return False

    try:
        try:
            if hasattr(layer, "setMaximumScreenError"):
                layer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
            if hasattr(layer, "setPointBudget"):
                layer.setPointBudget(DEFAULT_POINT_BUDGET)
        except Exception:
            pass

        renderer = QgsPointCloudRgbRenderer()
        renderer.setRedAttribute(r_name)
        renderer.setGreenAttribute(g_name)
        renderer.setBlueAttribute(b_name)

        min_c, max_c = get_rgb_contrast_range(layer)
        # Dynamic 8/16-bit ASPRS LAS color contrast enhancement
        for setter in [renderer.setRedContrastEnhancement, renderer.setGreenContrastEnhancement, renderer.setBlueContrastEnhancement]:
            ce = QgsContrastEnhancement(Qgis.DataType.UInt16)
            ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum, True)
            ce.setMinimumValue(float(min_c))
            ce.setMaximumValue(float(max_c))
            setter(ce)

        try:
            renderer.setPointSymbol(QgsPointCloudRgbRenderer.PointSymbol.Square)
        except Exception:
            pass
        renderer.setPointSize(point_size)
        renderer.setPointSizeUnit(QgsUnitTypes.RenderPixels)
        renderer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
        renderer.setMaximumScreenErrorUnit(QgsUnitTypes.RenderPixels)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[LidarStyler] Error applying RGB renderer: {e}")
        return False


def apply_cir(layer, point_size: float = 3.5) -> bool:
    """Color Infrared (CIR: NIR -> Red, Red -> Green, Green -> Blue)."""
    return _apply_cir(layer, point_size=point_size, apply_rgb_fallback=apply_rgb)


def apply_classification(layer, point_size: float = 3.5) -> bool:
    """Render point cloud using ASPRS LAS standard classification color palette with solid square splatting."""
    if not is_point_cloud(layer):
        return False

    try:
        try:
            if hasattr(layer, "setMaximumScreenError"):
                layer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
            if hasattr(layer, "setPointBudget"):
                layer.setPointBudget(DEFAULT_POINT_BUDGET)
        except Exception:
            pass

        class_attr = find_attr(layer, ["Classification", "classification", "class"], fallback="Classification")
        categories = [
            QgsPointCloudCategory(0, QColor("#94a3b8"), "0: Never Classified"),
            QgsPointCloudCategory(1, QColor("#cbd5e1"), "1: Unassigned"),
            QgsPointCloudCategory(2, QColor("#d4a373"), "2: Ground (Light Brown / Tan)"),
            QgsPointCloudCategory(3, QColor("#86efac"), "3: Low Vegetation"),
            QgsPointCloudCategory(4, QColor("#22c55e"), "4: Medium Vegetation"),
            QgsPointCloudCategory(5, QColor("#15803d"), "5: High Vegetation / Canopy"),
            QgsPointCloudCategory(6, QColor("#ef4444"), "6: Building / Roof"),
            QgsPointCloudCategory(7, QColor("#64748b"), "7: Low Point / Noise"),
            QgsPointCloudCategory(8, QColor("#f59e0b"), "8: Reserved / Model Key-Point"),
            QgsPointCloudCategory(9, QColor("#0284c7"), "9: Water"),
            QgsPointCloudCategory(10, QColor("#ec4899"), "10: Rail"),
            QgsPointCloudCategory(11, QColor("#334155"), "11: Road Surface"),
            QgsPointCloudCategory(12, QColor("#a855f7"), "12: Overlap Reserved"),
            QgsPointCloudCategory(13, QColor("#eab308"), "13: Wire - Guard"),
            QgsPointCloudCategory(14, QColor("#f97316"), "14: Wire - Conductor"),
            QgsPointCloudCategory(15, QColor("#84cc16"), "15: Transmission Tower"),
            QgsPointCloudCategory(17, QColor("#78716c"), "17: Bridge Deck"),
            QgsPointCloudCategory(18, QColor("#06b6d4"), "18: High Noise"),
        ]

        renderer = QgsPointCloudClassifiedRenderer(class_attr, categories)
        try:
            renderer.setPointSymbol(QgsPointCloudClassifiedRenderer.PointSymbol.Square)
        except Exception:
            pass
        renderer.setPointSize(point_size)
        renderer.setPointSizeUnit(QgsUnitTypes.RenderPixels)
        renderer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
        renderer.setMaximumScreenErrorUnit(QgsUnitTypes.RenderPixels)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[LidarStyler] Error applying classification renderer: {e}")
        return False


def apply_return_number(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by pulse return number (1st, 2nd, 3rd, last)."""
    if not is_point_cloud(layer):
        return False

    try:
        try:
            if hasattr(layer, "setMaximumScreenError"):
                layer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
            if hasattr(layer, "setPointBudget"):
                layer.setPointBudget(DEFAULT_POINT_BUDGET)
        except Exception:
            pass

        ret_attr = find_attr(layer, ["ReturnNumber", "returnnumber", "return_number", "Return", "return"], fallback="ReturnNumber")
        categories = [
            QgsPointCloudCategory(1, QColor("#10b981"), "1: First Return (Canopy/Roof)"),
            QgsPointCloudCategory(2, QColor("#3b82f6"), "2: Second Return"),
            QgsPointCloudCategory(3, QColor("#f59e0b"), "3: Third Return"),
            QgsPointCloudCategory(4, QColor("#ef4444"), "4: Fourth Return"),
            QgsPointCloudCategory(5, QColor("#8b5cf6"), "5+: Last Return (Ground)"),
        ]

        renderer = QgsPointCloudClassifiedRenderer(ret_attr, categories)
        try:
            renderer.setPointSymbol(QgsPointCloudClassifiedRenderer.PointSymbol.Square)
        except Exception:
            pass
        renderer.setPointSize(point_size)
        renderer.setPointSizeUnit(QgsUnitTypes.RenderPixels)
        renderer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
        renderer.setMaximumScreenErrorUnit(QgsUnitTypes.RenderPixels)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        return True
    except Exception as e:
        print(f"[LidarStyler] Error applying return number renderer: {e}")
        return False
