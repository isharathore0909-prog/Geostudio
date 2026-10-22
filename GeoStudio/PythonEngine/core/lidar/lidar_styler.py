# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR & Point Cloud Styler
Provides high-performance 2D & 3D styling and coloring for QgsPointCloudLayer (.las, .laz, .copc.laz, .e57).
Guarantees explicit ColorRampItem list generation for all ramp-based shaders.
"""

from qgis.core import (
    QgsPointCloudAttributeByRampRenderer,
    QgsUnitTypes
)

from .lidar_attributes import (
    is_point_cloud, get_attribute_names, find_attr, get_attribute_range,
    create_shader, set_point_size, DEFAULT_MAX_SCREEN_ERROR, DEFAULT_POINT_BUDGET
)
from .lidar_renderers import (
    apply_rgb, apply_classification, apply_return_number, apply_height_above_ground,
    apply_scan_angle, apply_point_source_id, apply_source_layer, apply_segment,
    apply_point_index, apply_cir, apply_ndvi, apply_ndwi, apply_point_density,
    apply_withheld_flag, apply_keypoint_flag, apply_overlap_flag, apply_return_height_delta
)


class LidarStyler:
    """Provides automated rendering, color ramps, and symbology for Point Cloud layers."""

    # Attribute and helper exports
    is_point_cloud = staticmethod(is_point_cloud)
    get_attribute_names = staticmethod(get_attribute_names)
    _find_attr = staticmethod(find_attr)
    _get_attribute_range = staticmethod(get_attribute_range)
    _create_shader = staticmethod(create_shader)
    set_point_size = staticmethod(set_point_size)

    # Renderer exports
    apply_rgb = staticmethod(apply_rgb)
    apply_classification = staticmethod(apply_classification)
    apply_return_number = staticmethod(apply_return_number)
    apply_height_above_ground = staticmethod(apply_height_above_ground)
    apply_scan_angle = staticmethod(apply_scan_angle)
    apply_point_source_id = staticmethod(apply_point_source_id)
    apply_source_layer = staticmethod(apply_source_layer)
    apply_segment = staticmethod(apply_segment)
    apply_point_index = staticmethod(apply_point_index)
    apply_cir = staticmethod(apply_cir)
    apply_ndvi = staticmethod(apply_ndvi)
    apply_ndwi = staticmethod(apply_ndwi)
    apply_point_density = staticmethod(apply_point_density)
    apply_withheld_flag = staticmethod(apply_withheld_flag)
    apply_keypoint_flag = staticmethod(apply_keypoint_flag)
    apply_overlap_flag = staticmethod(apply_overlap_flag)
    apply_return_height_delta = staticmethod(apply_return_height_delta)

    @staticmethod
    def auto_style(layer, point_size: float = 3.5) -> bool:
        """Automatically style point cloud in True Color RGB on first load, falling back to Elevation Turbo."""
        if not is_point_cloud(layer):
            return False

        try:
            if hasattr(layer, "setMaximumScreenError"):
                layer.setMaximumScreenError(DEFAULT_MAX_SCREEN_ERROR)
            if hasattr(layer, "setPointBudget"):
                layer.setPointBudget(DEFAULT_POINT_BUDGET)
        except Exception:
            pass

        # Check for valid True Color RGB first
        if apply_rgb(layer, point_size=point_size):
            return True

        # Fallback to vibrant Elevation Turbo Color Ramp
        return LidarStyler.apply_elevation_ramp(layer, ramp_name="Turbo", point_size=point_size)

    @staticmethod
    def apply_rgb_elev(layer, point_size: float = 3.5) -> bool:
        """Render point cloud with RGB true color if present, otherwise fall back to elevation ramp."""
        if not is_point_cloud(layer):
            return False
        from .lidar_attributes import has_valid_rgb
        if has_valid_rgb(layer):
            if apply_rgb(layer, point_size=point_size):
                return True
        return LidarStyler.apply_elevation_ramp(layer, ramp_name="Turbo", point_size=point_size)

    @staticmethod
    def apply_elevation_ramp(layer, ramp_name: str = "Turbo", point_size: float = 3.5) -> bool:
        """Render point cloud colored by elevation (Z attribute) with seamless solid splatting."""
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

            z_attr = find_attr(layer, ["Z", "Elevation", "Height", "z"], fallback="Z")
            z_min, z_max = get_attribute_range(layer, z_attr, 0.0, 100.0)

            shader = create_shader(z_min, z_max, ramp_name=ramp_name, num_stops=16)

            renderer = QgsPointCloudAttributeByRampRenderer()
            renderer.setAttribute(z_attr)
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
            print(f"[LidarStyler] Error applying elevation ramp: {e}")
            return False

    @staticmethod
    def apply_intensity_ramp(layer, point_size: float = 3.5) -> bool:
        """Render point cloud colored by laser return intensity with dynamic contrast range."""
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

            int_attr = find_attr(layer, ["Intensity", "intensity", "reflectance", "LaserIntensity"], fallback="Intensity")
            i_min, i_max = get_attribute_range(layer, int_attr, 0.0, 4095.0)
            if i_max <= i_min:
                i_max = i_min + 255.0

            # Generate high-contrast laser intensity shader (Dark-to-Light: Greys inverted)
            shader = create_shader(i_min, i_max, ramp_name="Greys", num_stops=16, invert=True)

            renderer = QgsPointCloudAttributeByRampRenderer()
            renderer.setAttribute(int_attr)
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
            print(f"[LidarStyler] Error applying intensity ramp: {e}")
            return False

