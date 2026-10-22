# -*- coding: utf-8 -*-
"""
GeoStudio - Map Canvas Layer Coordination & Elevation Sampling.
Handles layer addition/removal lifecycle, CRS auto-detection, and spatial sampling.
"""

from typing import Optional, List
from core.elevation_styler import ElevationStyler


class CanvasLayerCoordinator:
    """Coordinates layer events and elevation sampling for MapCanvasWidget."""

    @staticmethod
    def sample_elevation_at_point(canvas, point) -> Optional[float]:
        """Sample elevation value from top-most visible raster layer at point."""
        try:
            from qgis.core import QgsProject, QgsMapLayer
            map_crs = canvas.mapSettings().destinationCrs() if canvas else None
            layers = list(QgsProject.instance().mapLayers().values())
            
            for layer in reversed(layers):
                if layer.type() == QgsMapLayer.RasterLayer and layer.isValid():
                    node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
                    if node and not node.isVisible():
                        continue
                    val, _ = ElevationStyler.sample_elevation_at_point(layer, point, map_crs=map_crs, band=1)
                    if val is not None:
                        return val
        except Exception:
            pass
        return None

    @staticmethod
    def sync_project_crs(canvas):
        """Synchronize destination CRS from project to canvas."""
        try:
            from qgis.core import QgsProject
            crs = QgsProject.instance().crs()
            if canvas and crs.isValid():
                canvas.setDestinationCrs(crs)
                canvas.refresh()
        except Exception:
            pass

    @staticmethod
    def handle_layers_added(canvas, bridge, nav_mgr, legend_widget, layers: List) -> Optional[object]:
        """
        Handle layer addition: sets coordinate CRS, auto-styles elevation layers,
        and determines zoom target. Returns the layer to zoom to if any.
        """
        try:
            from qgis.core import QgsProject, QgsCoordinateReferenceSystem
            proj = QgsProject.instance()
            zoom_target = None

            for layer in list(layers):
                if not layer:
                    continue
                try:
                    if (not layer.isValid() or 
                            getattr(layer, "_is_sub_relief_layer", False) or 
                            getattr(layer, "_is_analysis_result", False) or 
                            "[3D Hillshade]" in layer.name() or 
                            "[3D Relief]" in layer.name()):
                        continue
                except RuntimeError:
                    continue

                if getattr(layer, "_is_3d_relief", False):
                    if legend_widget:
                        legend_widget.update_from_layer(layer)
                    if zoom_target is None:
                        zoom_target = layer
                    continue

                # Ensure CRS is valid
                if not layer.crs().isValid() or not layer.crs().authid():
                    ext = layer.extent()
                    if ext.xMinimum() > 180.0 or ext.yMinimum() > 90.0 or ext.xMaximum() > 180.0 or ext.yMinimum() < -90.0:
                        layer.setCrs(QgsCoordinateReferenceSystem("EPSG:32643"))
                    else:
                        layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

                if layer.crs().isValid():
                    valid_others = [
                        l for l in proj.mapLayers().values() 
                        if l.isValid() and l.id() != layer.id() 
                        and not getattr(l, "_is_sub_relief_layer", False) 
                        and "[3D Hillshade]" not in l.name()
                    ]
                    if not valid_others or proj.crs().authid() == "EPSG:4326":
                        proj.setCrs(layer.crs())
                        if canvas:
                            canvas.setDestinationCrs(layer.crs())
                    if zoom_target is None:
                        zoom_target = layer

                    if ElevationStyler.is_dem_or_elevation(layer):
                        ElevationStyler.apply_elevation_colormap(layer, preset_key="GLOBAL_MAPPER_ATLAS")
                        if legend_widget:
                            legend_widget.update_from_layer(layer)
                        zoom_target = layer

            if bridge:
                bridge.setCanvasLayers()
            elif canvas:
                all_layers = [l for l in proj.mapLayers().values() if l.isValid()]
                canvas.setLayers(all_layers)

            if zoom_target and nav_mgr:
                try:
                    if hasattr(zoom_target, "isValid") and zoom_target.isValid():
                        nav_mgr.zoom_to_layer(zoom_target)
                except RuntimeError:
                    pass

            if canvas:
                canvas.refresh()
                canvas.update()

            return zoom_target
        except Exception:
            return None

