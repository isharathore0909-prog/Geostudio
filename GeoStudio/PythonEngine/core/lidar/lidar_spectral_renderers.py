# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Spectral & QA Symbology Renderers
Vegetation indices (NDVI/NDWI), CIR infrared, density, and QA/QC quality flag renderers.
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


def apply_cir(layer, point_size: float = 3.5, apply_rgb_fallback=None) -> bool:
    """Color Infrared (CIR: NIR -> Red, Red -> Green, Green -> Blue)."""
    if not is_point_cloud(layer):
        return False

    try:
        if hasattr(layer, "setMaximumScreenError"):
            layer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
        if hasattr(layer, "setPointBudget"):
            layer.setPointBudget(DEFAULT_POINT_BUDGET)
    except Exception:
        pass

    min_c, max_c = get_rgb_contrast_range(layer)

    attrs = [a.lower() for a in get_attribute_names(layer)]
    if ("nir" in attrs or "infrared" in attrs) and ("red" in attrs and "green" in attrs):
        try:
            renderer = QgsPointCloudRgbRenderer()
            nir_name = find_attr(layer, ["Nir", "NIR", "Infrared", "infrared", "near_infrared"])
            r_name = find_attr(layer, ["Red", "red", "R"])
            g_name = find_attr(layer, ["Green", "green", "G"])

            renderer.setRedAttribute(nir_name)
            renderer.setGreenAttribute(r_name)
            renderer.setBlueAttribute(g_name)

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
            print(f"[LidarStyler] Error applying CIR NIR renderer: {e}")

    # Fallback to CIR false-color simulation or classification vegetation highlight
    if "red" in attrs and "green" in attrs and "blue" in attrs:
        try:
            renderer = QgsPointCloudRgbRenderer()
            r_name = find_attr(layer, ["Red", "red", "R"])
            g_name = find_attr(layer, ["Green", "green", "G"])
            b_name = find_attr(layer, ["Blue", "blue", "B"])

            # False color infrared: Red channel shows green reflection, Green channel shows red, Blue shows blue
            renderer.setRedAttribute(g_name)
            renderer.setGreenAttribute(r_name)
            renderer.setBlueAttribute(b_name)

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
        except Exception:
            pass

    from .lidar_renderers import apply_classification
    return apply_classification(layer, point_size=point_size)


def apply_ndvi(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by Normalized Difference Vegetation Index (NDVI) or Vegetation Classification."""
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

        attr = find_attr(layer, ["NDVI", "ndvi", "VegetationIndex", "vegetation_index"])
        if attr:
            s_min, s_max = get_attribute_range(layer, attr, -0.2, 0.8)
            shader = create_shader(s_min, s_max, ramp_name="RdYlGn", num_stops=16)

            renderer = QgsPointCloudAttributeByRampRenderer()
            renderer.setAttribute(attr)
            renderer.setColorRampShader(shader)
            try:
                renderer.setPointSymbol(QgsPointCloudAttributeByRampRenderer.PointSymbol.Square)
            except Exception:
                pass
            renderer.setPointSize(point_size)
            renderer.setPointSizeUnit(QgsUnitTypes.RenderPixels)
            renderer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
            renderer.setMaximumScreenErrorUnit(QgsUnitTypes.RenderPixels)

            layer.setRenderer(renderer)
            layer.triggerRepaint()
            return True

        # Robust Fallback: ASPRS Vegetation Calibrated Palette (NDVI colors)
        class_attr = find_attr(layer, ["Classification", "classification", "class"], fallback="Classification")
        categories = [
            QgsPointCloudCategory(0, QColor("#94a3b8"), "0: Unclassified (NDVI 0.0)"),
            QgsPointCloudCategory(1, QColor("#cbd5e1"), "1: Unassigned (NDVI 0.0)"),
            QgsPointCloudCategory(2, QColor("#d4a373"), "2: Ground / Soil (NDVI 0.08)"),
            QgsPointCloudCategory(3, QColor("#a3e635"), "3: Low Vegetation (NDVI 0.35)"),
            QgsPointCloudCategory(4, QColor("#22c55e"), "4: Medium Vegetation (NDVI 0.60)"),
            QgsPointCloudCategory(5, QColor("#15803d"), "5: High Forest Canopy (NDVI 0.85)"),
            QgsPointCloudCategory(6, QColor("#ef4444"), "6: Building / Non-Veg (NDVI -0.1)"),
            QgsPointCloudCategory(7, QColor("#64748b"), "7: Noise / Non-Veg"),
            QgsPointCloudCategory(9, QColor("#0284c7"), "9: Water (NDVI -0.4)"),
            QgsPointCloudCategory(11, QColor("#475569"), "11: Road / Non-Veg (NDVI -0.15)"),
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
        print(f"[LidarStyler] Error applying NDVI: {e}")
        return False


def apply_ndwi(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by Normalized Difference Water Index (NDWI) or Hydrological Water Classes."""
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

        attr = find_attr(layer, ["NDWI", "ndwi", "WaterIndex", "water_index"])
        if attr:
            s_min, s_max = get_attribute_range(layer, attr, -0.5, 0.5)
            shader = create_shader(s_min, s_max, ramp_name="Blues", num_stops=16)

            renderer = QgsPointCloudAttributeByRampRenderer()
            renderer.setAttribute(attr)
            renderer.setColorRampShader(shader)
            try:
                renderer.setPointSymbol(QgsPointCloudAttributeByRampRenderer.PointSymbol.Square)
            except Exception:
                pass
            renderer.setPointSize(point_size)
            renderer.setPointSizeUnit(QgsUnitTypes.RenderPixels)
            renderer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
            renderer.setMaximumScreenErrorUnit(QgsUnitTypes.RenderPixels)

            layer.setRenderer(renderer)
            layer.triggerRepaint()
            return True

        # Robust Fallback: Hydrological Water & Moisture Palette
        class_attr = find_attr(layer, ["Classification", "classification", "class"], fallback="Classification")
        categories = [
            QgsPointCloudCategory(0, QColor("#e2e8f0"), "0: Unclassified"),
            QgsPointCloudCategory(1, QColor("#cbd5e1"), "1: Dry Surface"),
            QgsPointCloudCategory(2, QColor("#d4a373"), "2: Dry Ground"),
            QgsPointCloudCategory(3, QColor("#86efac"), "3: Moist Low Vegetation"),
            QgsPointCloudCategory(4, QColor("#10b981"), "4: Moist Canopy"),
            QgsPointCloudCategory(5, QColor("#047857"), "5: Dense Canopy"),
            QgsPointCloudCategory(6, QColor("#94a3b8"), "6: Impervious Surface"),
            QgsPointCloudCategory(9, QColor("#0ea5e9"), "9: Open Water Body (High NDWI)"),
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
        print(f"[LidarStyler] Error applying NDWI: {e}")
        return False


def apply_point_density(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by local point density / return clustering."""
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

        attr = find_attr(layer, ["PointDensity", "point_density", "Density", "density", "Intensity", "ReturnNumber"], fallback="Intensity")
        s_min, s_max = get_attribute_range(layer, attr, 1.0, 50.0)
        shader = create_shader(s_min, s_max, ramp_name="Plasma", num_stops=16)

        renderer = QgsPointCloudAttributeByRampRenderer()
        renderer.setAttribute(attr)
        renderer.setColorRampShader(shader)
        try:
            renderer.setPointSymbol(QgsPointCloudAttributeByRampRenderer.PointSymbol.Square)
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
        print(f"[LidarStyler] Error applying point density: {e}")
        return False


def apply_withheld_flag(layer, point_size: float = 3.5) -> bool:
    """Highlight withheld points (QA/QC noise flagging)."""
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

        attr = find_attr(layer, ["Withheld", "withheld", "WithheldFlag", "withheld_flag"])
        if attr:
            categories = [
                QgsPointCloudCategory(0, QColor("#10b981"), "Valid (Not Withheld)"),
                QgsPointCloudCategory(1, QColor("#ef4444"), "Withheld / Outlier Flagged"),
            ]
        else:
            attr = find_attr(layer, ["Classification", "classification", "class"], fallback="Classification")
            categories = [
                QgsPointCloudCategory(0, QColor("#10b981"), "Valid (Unclassified)"),
                QgsPointCloudCategory(1, QColor("#10b981"), "Valid (Unassigned)"),
                QgsPointCloudCategory(2, QColor("#10b981"), "Valid (Ground)"),
                QgsPointCloudCategory(3, QColor("#10b981"), "Valid (Low Veg)"),
                QgsPointCloudCategory(4, QColor("#10b981"), "Valid (Med Veg)"),
                QgsPointCloudCategory(5, QColor("#10b981"), "Valid (High Veg)"),
                QgsPointCloudCategory(6, QColor("#10b981"), "Valid (Building)"),
                QgsPointCloudCategory(7, QColor("#ef4444"), "Flagged: Low Point Noise (Withheld)"),
                QgsPointCloudCategory(9, QColor("#10b981"), "Valid (Water)"),
                QgsPointCloudCategory(11, QColor("#10b981"), "Valid (Road)"),
                QgsPointCloudCategory(18, QColor("#ef4444"), "Flagged: High Noise (Withheld)"),
            ]

        renderer = QgsPointCloudClassifiedRenderer(attr, categories)
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
        print(f"[LidarStyler] Error applying withheld flag: {e}")
        return False


def apply_keypoint_flag(layer, point_size: float = 3.5) -> bool:
    """Highlight model keypoints (decimated DTM surface anchors)."""
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

        attr = find_attr(layer, ["KeyPoint", "keypoint", "Keypoint", "KeyPointFlag"])
        if attr:
            categories = [
                QgsPointCloudCategory(0, QColor("#94a3b8"), "Standard Point"),
                QgsPointCloudCategory(1, QColor("#f59e0b"), "Keypoint (Model Anchor)"),
            ]
        else:
            attr = find_attr(layer, ["Classification", "classification", "class"], fallback="Classification")
            categories = [
                QgsPointCloudCategory(0, QColor("#94a3b8"), "Standard Point"),
                QgsPointCloudCategory(1, QColor("#94a3b8"), "Standard Point"),
                QgsPointCloudCategory(2, QColor("#cbd5e1"), "Standard Ground"),
                QgsPointCloudCategory(8, QColor("#f59e0b"), "Class 8: Model Keypoint (Surface Anchor)"),
            ]

        renderer = QgsPointCloudClassifiedRenderer(attr, categories)
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
        print(f"[LidarStyler] Error applying keypoint flag: {e}")
        return False


def apply_overlap_flag(layer, point_size: float = 3.5) -> bool:
    """Highlight flight strip overlap points."""
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

        attr = find_attr(layer, ["Overlap", "overlap", "OverlapFlag"])
        if attr:
            categories = [
                QgsPointCloudCategory(0, QColor("#3b82f6"), "Single Flight Swath"),
                QgsPointCloudCategory(1, QColor("#a855f7"), "Overlap Zone Point"),
            ]
        else:
            attr = find_attr(layer, ["Classification", "classification", "class"], fallback="Classification")
            categories = [
                QgsPointCloudCategory(0, QColor("#3b82f6"), "Flight Swath Point"),
                QgsPointCloudCategory(1, QColor("#3b82f6"), "Flight Swath Point"),
                QgsPointCloudCategory(2, QColor("#60a5fa"), "Ground Swath"),
                QgsPointCloudCategory(12, QColor("#a855f7"), "Class 12: Overlap Reserved Point"),
            ]

        renderer = QgsPointCloudClassifiedRenderer(attr, categories)
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
        print(f"[LidarStyler] Error applying overlap flag: {e}")
        return False


def apply_return_height_delta(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by first vs last return height difference (canopy penetration)."""
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

        attr = find_attr(layer, ["ReturnHeightDelta", "return_height_delta", "DeltaZ", "NumberOfReturns", "ReturnNumber", "Intensity", "Z"], fallback="ReturnNumber")
        s_min, s_max = get_attribute_range(layer, attr, 0.0, 25.0)
        shader = create_shader(s_min, s_max, ramp_name="YlGnBu", num_stops=16)

        renderer = QgsPointCloudAttributeByRampRenderer()
        renderer.setAttribute(attr)
        renderer.setColorRampShader(shader)
        try:
            renderer.setPointSymbol(QgsPointCloudAttributeByRampRenderer.PointSymbol.Square)
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
        print(f"[LidarStyler] Error applying return height delta: {e}")
        return False
