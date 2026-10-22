# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Attribute & Metadata Renderers
Renderers for Scan Angle, Point Source ID, Source Layer, Segment, Point Index, and Height Above Ground.
"""

from qgis.core import (
    QgsPointCloudAttributeByRampRenderer,
    QgsUnitTypes
)
from .lidar_attributes import (
    is_point_cloud, find_attr, get_attribute_range, create_shader, DEFAULT_MAX_SCREEN_ERROR, DEFAULT_POINT_BUDGET
)


def apply_height_above_ground(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by height above ground."""
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

        hag_attr = find_attr(layer, ["HeightAboveGround", "HAG", "hag", "NormalizedZ", "normalized_z", "Z"], fallback="Z")
        h_min, h_max = get_attribute_range(layer, hag_attr, 0.0, 35.0)
        if h_min < 0.0:
            h_min = 0.0
        if h_max <= h_min:
            h_max = h_min + 35.0

        shader = create_shader(h_min, h_max, ramp_name="Viridis", num_stops=16)

        renderer = QgsPointCloudAttributeByRampRenderer()
        renderer.setAttribute(hag_attr)
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
        print(f"[LidarStyler] Error applying height above ground renderer: {e}")
        return False


def apply_scan_angle(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by scan angle deflection (-90 to +90 deg)."""
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

        attr = find_attr(layer, ["ScanAngleRank", "ScanAngle", "scan_angle", "scanangle", "ScanAngleDegrees", "Angle", "UserData", "Intensity"], fallback="Intensity")
        s_min, s_max = get_attribute_range(layer, attr, -35.0, 35.0)
        if abs(s_max - s_min) < 0.1:
            s_min, s_max = -35.0, 35.0
        shader = create_shader(s_min, s_max, ramp_name="Spectral", num_stops=16)

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
        print(f"[LidarStyler] Error applying scan angle: {e}")
        return False


def apply_point_source_id(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by flight line / strip ID."""
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

        attr = find_attr(layer, ["PointSourceId", "PointSourceID", "point_source_id", "PointSource", "SourceID", "FlightLine", "UserData", "Classification"], fallback="Classification")
        s_min, s_max = get_attribute_range(layer, attr, 1.0, 10.0)
        if s_max <= s_min:
            s_max = s_min + 10.0
        shader = create_shader(s_min, s_max, ramp_name="Turbo", num_stops=16)

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
        print(f"[LidarStyler] Error applying point source ID: {e}")
        return False


def apply_source_layer(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by source file / layer origin."""
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

        attr = find_attr(layer, ["SourceLayer", "source_layer", "LayerId", "FileId", "TileId", "UserData", "PointSourceId", "Classification"], fallback="PointSourceId")
        s_min, s_max = get_attribute_range(layer, attr, 0.0, 10.0)
        shader = create_shader(s_min, s_max, ramp_name="Accent", num_stops=12)

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
        print(f"[LidarStyler] Error applying source layer: {e}")
        return False


def apply_segment(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by cluster / tree / building segment ID."""
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

        attr = find_attr(layer, ["Segment", "segment", "SegmentId", "segment_id", "Cluster", "ClusterId", "TreeId", "Class", "Classification", "UserData"], fallback="Classification")
        s_min, s_max = get_attribute_range(layer, attr, 0.0, 100.0)
        shader = create_shader(s_min, s_max, ramp_name="Turbo", num_stops=24)

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
        print(f"[LidarStyler] Error applying segment: {e}")
        return False


def apply_point_index(layer, point_size: float = 3.5) -> bool:
    """Render point cloud colored by sequential point index order."""
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

        attr = find_attr(layer, ["PointIndex", "point_index", "Index", "index", "GpsTime", "gpstime", "Intensity", "Z"], fallback="GpsTime")
        s_min, s_max = get_attribute_range(layer, attr, 0.0, 1000000.0)
        shader = create_shader(s_min, s_max, ramp_name="Spectral", num_stops=16)

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
        print(f"[LidarStyler] Error applying point index: {e}")
        return False
