# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Attribute & Shader Utilities
Attribute extraction, statistical range discovery, color ramp shader generation, and point size adjustment.
"""

import os
import math
import struct
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsMapLayer, QgsPointCloudLayer, QgsColorRampShader, QgsStyle
)

DEFAULT_MAX_SCREEN_ERROR = 1.0
DEFAULT_POINT_BUDGET = 20000000
DEFAULT_POINT_SIZE = 3.5



def is_point_cloud(layer) -> bool:
    """Check if layer is a valid QgsPointCloudLayer."""
    if not layer or not layer.isValid():
        return False
    return hasattr(QgsMapLayer, "PointCloudLayer") and layer.type() == QgsMapLayer.PointCloudLayer


def get_point_cloud_source_file(layer) -> str:
    """Gets the underlying local file path for a point cloud layer."""
    if not is_point_cloud(layer):
        return ""
    if hasattr(layer, "customProperty"):
        p = layer.customProperty("original_las_path") or layer.customProperty("copc_path")
        if p and os.path.exists(p):
            return p
    source = layer.source() if hasattr(layer, "source") else ""
    if source and os.path.exists(source):
        return source
    return ""


def get_point_cloud_las_bounds(layer) -> tuple:
    """Reads accurate X, Y, Z bounding box from the LAS/LAZ/COPC source file header in < 1ms."""
    cached = getattr(layer, "_cached_las_bounds", None)
    if cached is not None:
        return cached

    try:
        source_path = get_point_cloud_source_file(layer)
        if source_path and os.path.exists(source_path):
            with open(source_path, 'rb') as f:
                header = f.read(375)
                if header[:4] == b'LASF' and len(header) >= 227:
                    max_x, min_x, max_y, min_y, max_z, min_z = struct.unpack('<6d', header[179:227])
                    if min_z < max_z:
                        res = (min_z, max_z, min_x, max_x, min_y, max_y)
                        try:
                            layer._cached_las_bounds = res
                        except Exception:
                            pass
                        return res
    except Exception:
        pass
    return None


def get_attribute_names(layer) -> list:
    """Extract available attribute names from point cloud layer."""
    if not is_point_cloud(layer):
        return []
    cached = getattr(layer, "_cached_attr_names", None)
    if cached is not None:
        return cached
    try:
        attrs = []
        if hasattr(layer, "attributes"):
            a_obj = layer.attributes()
            if hasattr(a_obj, "count") and hasattr(a_obj, "at"):
                attrs = [a_obj.at(i).name() for i in range(a_obj.count())]
            elif hasattr(a_obj, "attributes"):
                attrs = [a.name() for a in a_obj.attributes()]
            elif hasattr(a_obj, "__iter__"):
                attrs = [a.name() if hasattr(a, "name") else str(a) for a in a_obj]
        if not attrs:
            dp = layer.dataProvider()
            if dp and hasattr(dp, "attributes"):
                a_obj = dp.attributes()
                if hasattr(a_obj, "count") and hasattr(a_obj, "at"):
                    attrs = [a_obj.at(i).name() for i in range(a_obj.count())]
                elif hasattr(a_obj, "__iter__"):
                    attrs = [a.name() if hasattr(a, "name") else str(a) for a in a_obj]
        if attrs:
            try:
                layer._cached_attr_names = attrs
            except Exception:
                pass
            return attrs
    except Exception:
        pass
    return []


def find_attr(layer, candidates: list, fallback: str = None) -> str:
    """Finds the actual attribute name matching any of the candidates (case-insensitive)."""
    attrs = get_attribute_names(layer)
    for c in candidates:
        for a in attrs:
            if a.lower() == c.lower():
                return a
    return fallback


def get_attribute_range(layer, attr_name: str, default_min: float = 0.0, default_max: float = 100.0):
    """Retrieves statistical min/max accurately without blocking full-disk scans."""
    if not is_point_cloud(layer):
        return default_min, default_max

    attr_clean = attr_name.strip().lower()

    # 1. Query dataProvider attributeStats if available
    try:
        dp = layer.dataProvider() if hasattr(layer, "dataProvider") else None
        if dp and hasattr(dp, "attributeStats"):
            st = dp.attributeStats(attr_name)
            if st and hasattr(st, "maximum") and hasattr(st, "minimum"):
                if st.maximum > st.minimum:
                    return float(st.minimum), float(st.maximum)
    except Exception:
        pass

    # 2. Check cached LAS bounds for Z
    if attr_clean in ["z", "elevation", "height"]:
        las_bounds = get_point_cloud_las_bounds(layer)
        if las_bounds and las_bounds[0] < las_bounds[1]:
            return float(las_bounds[0]), float(las_bounds[1])

        try:
            elev_props = layer.elevationProperties()
            if elev_props:
                mn = getattr(elev_props, "zMinimum", None) or getattr(elev_props, "lowerElevationLimit", None)
                mx = getattr(elev_props, "zMaximum", None) or getattr(elev_props, "upperElevationLimit", None)
                if mn is not None and mx is not None and mn < mx and not math.isnan(mn) and not math.isnan(mx):
                    return float(mn), float(mx)
        except Exception:
            pass

    # 3. Fast laser / LAS header / percentile sample for Intensity
    if attr_clean in ["intensity", "reflectance", "laserintensity"]:
        try:
            source_file = get_point_cloud_source_file(layer)
            if source_file and os.path.exists(source_file):
                import laspy
                import numpy as np
                with laspy.open(source_file) as fh:
                    if hasattr(fh.header, "point_count") and fh.header.point_count > 0:
                        n_pts = min(10000, fh.header.point_count)
                        las_chunk = fh.read_points(n_pts)
                        if hasattr(las_chunk, "intensity"):
                            i_vals = np.array(las_chunk.intensity, dtype=np.float32)
                            if len(i_vals) > 0 and np.max(i_vals) > np.min(i_vals):
                                p1 = float(np.percentile(i_vals, 1))
                                p99 = float(np.percentile(i_vals, 99))
                                if p99 > p1:
                                    return (p1, p99)
        except Exception:
            pass
        return (0.0, 65535.0)

    # Static physical domains for standard LiDAR attributes
    if attr_clean in ["scanangle", "scan_angle", "scananglerank", "angle"]:
        return (-35.0, 35.0)
    elif attr_clean in ["heightaboveground", "hag", "normalizedz", "normalized_z"]:
        return (0.0, 35.0)
    elif attr_clean in ["returnnumber", "numberofreturns", "return", "return_number"]:
        return (1.0, 5.0)
    elif attr_clean in ["classification", "class"]:
        return (0.0, 18.0)
    elif attr_clean in ["pointsourceid", "point_source_id", "sourceid", "flightline"]:
        return (1.0, 10.0)
    elif attr_clean in ["pointdensity", "density"]:
        return (1.0, 50.0)
    elif attr_clean in ["ndvi", "vegetationindex"]:
        return (-0.2, 0.8)
    elif attr_clean in ["ndwi", "waterindex"]:
        return (-0.5, 0.5)

    return default_min, default_max


def get_rgb_contrast_range(layer) -> tuple:
    """Calculates optimal contrast stretch min/max for RGB channels in < 10ms."""
    cached = getattr(layer, "_cached_rgb_contrast", None)
    if cached is not None:
        return cached

    min_val, max_val = 0.0, 255.0
    try:
        source_path = get_point_cloud_source_file(layer)
        if source_path and os.path.exists(source_path):
            import laspy
            import numpy as np
            with laspy.open(source_path) as fh:
                n = min(5000, fh.header.point_count)
                chunk = fh.read_points(n)
                if hasattr(chunk, 'red') and hasattr(chunk, 'green') and hasattr(chunk, 'blue'):
                    r_raw = np.array(chunk.red, dtype=np.float32)
                    g_raw = np.array(chunk.green, dtype=np.float32)
                    b_raw = np.array(chunk.blue, dtype=np.float32)
                    max_sampled = max(float(np.max(r_raw)), float(np.max(g_raw)), float(np.max(b_raw)))
                    if max_sampled > 255.0:
                        # 16-bit RGB data: use 1% and 99% percentiles to prevent dark squashing
                        all_vals = np.concatenate([r_raw, g_raw, b_raw])
                        p1 = max(0.0, float(np.percentile(all_vals, 1)))
                        p99 = min(65535.0, float(np.percentile(all_vals, 99)))
                        if p99 > p1 + 100.0:
                            min_val, max_val = p1, p99
                        else:
                            min_val, max_val = 0.0, 30000.0
                    else:
                        min_val, max_val = 0.0, 255.0
    except Exception:
        min_val, max_val = 0.0, 30000.0

    res = (min_val, max_val)
    try:
        layer._cached_rgb_contrast = res
    except Exception:
        pass
    return res


def has_valid_rgb(layer) -> bool:
    """Checks whether the point cloud actually contains populated RGB color channels in 0.1ms."""
    if not is_point_cloud(layer):
        return False

    cached = getattr(layer, "_cached_has_valid_rgb", None)
    if cached is not None:
        return cached

    attrs = [a.lower() for a in get_attribute_names(layer)]
    has_rgb = ("red" in attrs and "green" in attrs and "blue" in attrs)
    
    # If not found directly in attributes, check LAS header (formats 2, 3, 5, 7, 8, 10 or compressed 130, 131, 135)
    if not has_rgb:
        try:
            source_path = get_point_cloud_source_file(layer)
            if source_path and os.path.exists(source_path):
                with open(source_path, 'rb') as f:
                    header = f.read(110)
                    if header[:4] == b'LASF' and len(header) >= 105:
                        p_format = header[104] % 128
                        has_rgb = p_format in (2, 3, 5, 7, 8, 10)
        except Exception:
            pass

    try:
        layer._cached_has_valid_rgb = has_rgb
    except Exception:
        pass
    return has_rgb


def create_shader(min_v: float, max_v: float, ramp_name: str = "Turbo", num_stops: int = 16, invert: bool = False):
    """Creates a QgsColorRampShader with explicit ColorRampItem stops."""
    if min_v is None or max_v is None or min_v >= max_v:
        min_v, max_v = 0.0, 100.0

    style = QgsStyle.defaultStyle()
    ramp = style.colorRamp(ramp_name)
    if not ramp and ramp_name != "Turbo":
        ramp = style.colorRamp("Turbo")
    if not ramp:
        ramp = style.colorRamp("Spectral") or style.colorRamp("Viridis")

    shader = QgsColorRampShader(float(min_v), float(max_v))
    shader.setColorRampType(QgsColorRampShader.Interpolated)

    items = []
    if ramp:
        shader.setSourceColorRamp(ramp)
        for i in range(num_stops):
            frac = i / (num_stops - 1)
            val = min_v + frac * (max_v - min_v)
            col = ramp.color(1.0 - frac if invert else frac)
            items.append(QgsColorRampShader.ColorRampItem(val, col, f"{val:.1f}"))
    else:
        turbo_cols = [
            (0.00, "#30123b"), (0.15, "#4662d8"), (0.30, "#28bbec"),
            (0.45, "#40e0d0"), (0.60, "#a2fc3c"), (0.75, "#febc2b"),
            (0.90, "#f86214"), (1.00, "#7a0403")
        ]
        for frac, hex_col in turbo_cols:
            val = min_v + frac * (max_v - min_v)
            items.append(QgsColorRampShader.ColorRampItem(val, QColor(hex_col), f"{val:.1f}"))

    shader.setColorRampItemList(items)
    return shader


def set_point_size(layer, delta: float) -> float:
    """Increase or decrease point size on current renderer."""
    if not is_point_cloud(layer):
        return 0.0
    try:
        renderer = layer.renderer()
        if renderer and hasattr(renderer, "pointSize") and hasattr(renderer, "setPointSize"):
            current = renderer.pointSize()
            new_size = max(0.5, min(20.0, current + delta))
            renderer.setPointSize(new_size)
            layer.triggerRepaint()
            return new_size
    except Exception:
        pass
    return 0.0
