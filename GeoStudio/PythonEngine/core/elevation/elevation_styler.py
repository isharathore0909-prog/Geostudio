# -*- coding: utf-8 -*-
"""
GeoStudio - Elevation & DEM Styling Engine
Provides 100% Global Mapper & ArcGIS Pro style 3D visualization for DTM, DEM, and DSM rasters.
"""

import os
import re
from osgeo import gdal
from qgis.core import (
    QgsRasterLayer, QgsProject, QgsHillshadeRenderer
)

from .elevation_palettes import ELEVATION_PRESETS
from .relief_shading import generate_3d_shaded_relief_file
from .elevation_stats import (
    is_dem_or_elevation, get_valid_elevation_stats, apply_resampling,
    sample_elevation_at_point, DEM_KEYWORDS
)
from .raster_colormaps import (
    apply_elevation_colormap, apply_scientific_palette, apply_grayscale_contrast,
    apply_aspect_colormap, apply_slope_colormap, apply_cut_fill_colormap,
    apply_watershed_colormap, apply_flowdir_colormap, apply_flowaccum_colormap,
    apply_stream_colormap
)


class ElevationStyler:
    """
    Core engine for detecting, computing statistics, and applying Global Mapper/ArcGIS
    style 3D shaded relief rendering to DEM/DTM/DSM datasets.
    """

    DEM_KEYWORDS = DEM_KEYWORDS

    # Re-expose standalone functions as class / static methods
    is_dem_or_elevation = staticmethod(is_dem_or_elevation)
    get_valid_elevation_stats = staticmethod(get_valid_elevation_stats)
    sample_elevation_at_point = staticmethod(sample_elevation_at_point)
    apply_resampling = staticmethod(apply_resampling)

    apply_elevation_colormap = staticmethod(apply_elevation_colormap)
    apply_scientific_palette = staticmethod(apply_scientific_palette)
    apply_grayscale_contrast = staticmethod(apply_grayscale_contrast)
    apply_aspect_colormap = staticmethod(apply_aspect_colormap)
    apply_slope_colormap = staticmethod(apply_slope_colormap)
    apply_cut_fill_colormap = staticmethod(apply_cut_fill_colormap)
    apply_watershed_colormap = staticmethod(apply_watershed_colormap)
    apply_flowdir_colormap = staticmethod(apply_flowdir_colormap)
    apply_flowaccum_colormap = staticmethod(apply_flowaccum_colormap)
    apply_stream_colormap = staticmethod(apply_stream_colormap)

    # ------------------------------------------------------------------
    # Blend Modes  (ArcGIS: Appearance → Effects → Layer Blend)
    # ------------------------------------------------------------------

    #: Mapping of human-readable blend mode names → QPainter.CompositionMode_*
    BLEND_MODES = {
        "Normal":         "SourceOver",
        "Multiply":       "Multiply",
        "Screen":         "Screen",
        "Overlay":        "Overlay",
        "Hard Light":     "HardLight",
        "Soft Light":     "SoftLight",
        "Darken":         "Darken",
        "Lighten":        "Lighten",
        "Color Dodge":    "ColorDodge",
        "Color Burn":     "ColorBurn",
        "Linear Dodge":   "Plus",
        "Difference":     "Difference",
        "Exclusion":      "Exclusion",
        "Multiply (Dark Terrain)": "Multiply",
        "Screen (Light Glow)":     "Screen",
    }

    @staticmethod
    def apply_blend_mode(layer, mode_name: str) -> bool:
        """
        Applies a compositing blend mode to *layer*.

        Parameters
        ----------
        layer     : QgsMapLayer (raster or vector)
        mode_name : one of ElevationStyler.BLEND_MODES keys, e.g. "Multiply"

        Returns True on success, False on failure.

        ArcGIS equivalent
        -----------------
        Select layer → Appearance tab → Effects group → Layer Blend drop-down.
        """
        if not layer or not layer.isValid():
            return False
        try:
            from PyQt5.QtGui import QPainter
            qt_attr = ElevationStyler.BLEND_MODES.get(mode_name, "SourceOver")
            mode = getattr(QPainter, f"CompositionMode_{qt_attr}",
                           QPainter.CompositionMode_SourceOver)
            layer.setBlendMode(mode)
            layer.triggerRepaint()
            return True
        except Exception as e:
            print(f"[ElevationStyler] apply_blend_mode error: {e}")
            return False

    @staticmethod
    def get_layer_blend_mode_name(layer) -> str:
        """Returns the human-readable name of the current blend mode for *layer*."""
        if not layer or not layer.isValid():
            return "Normal"
        try:
            from PyQt5.QtGui import QPainter
            current = layer.blendMode()
            reverse = {
                getattr(QPainter, f"CompositionMode_{v}", None): k
                for k, v in ElevationStyler.BLEND_MODES.items()
            }
            return reverse.get(current, "Normal")
        except Exception:
            return "Normal"

    @classmethod
    def generate_3d_shaded_relief_file(
        cls,
        source_path: str,
        preset_key: str = "GLOBAL_MAPPER_ATLAS",
        z_factor: float = None,
        azimuth: float = 315.0,
        altitude: float = 45.0
    ) -> str:
        """Delegates to modular relief_shading engine."""
        return generate_3d_shaded_relief_file(
            source_path=source_path,
            preset_key=preset_key,
            z_factor=z_factor,
            azimuth=azimuth,
            altitude=altitude
        )

    @classmethod
    def apply_draped_relief(
        cls,
        layer: QgsRasterLayer,
        preset_key: str = "GLOBAL_MAPPER_ATLAS",
        z_factor: float = None,
        azimuth: float = 315.0,
        altitude: float = 45.0,
        band: int = 1,
        multidirectional: bool = True,
        **kwargs
    ) -> bool:
        """
        Applies 100% native full-resolution 3D shaded relief by dynamically combining
        the Atlas/Selected Color Ramp with multi-directional Hillshading.
        Produces razor-sharp Global Mapper 3D terrain relief with rich depth and illumination.
        """
        if not layer or not layer.isValid() or not isinstance(layer, QgsRasterLayer):
            return False

        source = getattr(layer, "_raw_dem_source", layer.source())
        if not os.path.isfile(source):
            return False

        relief_path = generate_3d_shaded_relief_file(
            source_path=source,
            preset_key=preset_key,
            z_factor=z_factor,
            azimuth=azimuth,
            altitude=altitude
        )
        if not relief_path or not os.path.isfile(relief_path):
            cls.apply_elevation_colormap(layer, preset_key=preset_key, band=band)
            return layer

        proj = QgsProject.instance()
        clean_name = re.sub(r'(\s*\[DEM\])+', '', layer.name()).strip()
        clean_name = re.sub(r'(\s*\[3D Hillshade\])+', '', clean_name).strip()
        clean_name = re.sub(r'(\s*\[3D Relief\])+', '', clean_name).strip()

        if layer.source() == relief_path:
            cls.apply_resampling(layer, mode="smooth")
            layer.triggerRepaint()
            return layer

        new_layer = QgsRasterLayer(relief_path, f"{clean_name} [DEM]")
        if not new_layer.isValid():
            cls.apply_elevation_colormap(layer, preset_key=preset_key, band=band)
            return layer

        abs_source = os.path.abspath(source)
        new_layer.setCustomProperty("raw_dem_source", abs_source)
        new_layer.setCustomProperty("is_3d_relief", True)
        new_layer._raw_dem_source = abs_source
        new_layer._is_3d_relief = True
        cls.apply_resampling(new_layer, mode="smooth")

        root = proj.layerTreeRoot()
        node = root.findLayer(layer.id())
        if node and node.parent():
            parent_node = node.parent()
            idx = parent_node.children().index(node)
            proj.addMapLayer(new_layer, False)
            parent_node.insertLayer(idx, new_layer)
            proj.removeMapLayer(layer.id())
        else:
            proj.addMapLayer(new_layer, True)
            proj.removeMapLayer(layer.id())

        return new_layer

    @classmethod
    def apply_hillshade(
        cls,
        layer: QgsRasterLayer,
        band: int = 1,
        z_factor: float = 1.5,
        azimuth: float = 315.0,
        altitude: float = 45.0,
        multidirectional: bool = True
    ) -> bool:
        """
        Applies grayscale 3D Hillshade.
        """
        if not layer or not layer.isValid():
            return False

        try:
            raw_source = getattr(layer, "_raw_dem_source", layer.source())
            if layer.bandCount() == 4 and os.path.isfile(raw_source):
                clean_name = re.sub(r'(\s*\[DEM\])+', '', layer.name()).strip()
                clean_name = re.sub(r'(\s*\[3D Relief\])+', '', clean_name).strip()
                clean_name = re.sub(r'(\s*\[3D Hillshade\])+', '', clean_name).strip()

                raw_layer = QgsRasterLayer(raw_source, f"{clean_name} [3D Hillshade]")
                if raw_layer.isValid():
                    raw_layer._is_sub_relief_layer = True
                    renderer = QgsHillshadeRenderer(raw_layer.dataProvider(), 1, azimuth, altitude)
                    renderer.setZFactor(z_factor)
                    renderer.setMultiDirectional(multidirectional)
                    raw_layer.setRenderer(renderer)
                    cls.apply_resampling(raw_layer, mode="smooth")

                    proj = QgsProject.instance()
                    root = proj.layerTreeRoot()
                    node = root.findLayer(layer.id())
                    if node and node.parent():
                        parent_node = node.parent()
                        idx = parent_node.children().index(node)
                        proj.addMapLayer(raw_layer, False)
                        parent_node.insertLayer(idx, raw_layer)
                        proj.removeMapLayer(layer.id())
                    else:
                        proj.addMapLayer(raw_layer, True)
                        proj.removeMapLayer(layer.id())
                    return raw_layer

            if layer.bandCount() == 1:
                renderer = QgsHillshadeRenderer(layer.dataProvider(), band, azimuth, altitude)
                renderer.setZFactor(z_factor)
                renderer.setMultiDirectional(multidirectional)
                layer.setRenderer(renderer)
                cls.apply_resampling(layer, mode="smooth")
                layer.triggerRepaint()
                return layer
        except Exception as e:
            print(f"[ElevationStyler] Error applying hillshade: {e}")
            return False

    @classmethod
    def auto_style_elevation_if_dem(cls, layer: QgsRasterLayer, preset_key: str = "GLOBAL_MAPPER_ATLAS") -> bool:
        """
        Automatically called when a raster layer is added. If it's a DEM/DTM/DSM,
        applies the unified 3D Shaded Relief with Atlas colors.
        """
        if not cls.is_dem_or_elevation(layer):
            return False

        print(f"[ElevationStyler] 🏔 Detected Elevation Raster: '{layer.name()}'. Generating Global Mapper 3D Shaded Relief...")
        return cls.apply_draped_relief(layer, preset_key=preset_key)
