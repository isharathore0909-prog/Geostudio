# -*- coding: utf-8 -*-
"""
GeoStudio - Terrain, LiDAR, Satellite & Geoprocessing Controller Mixin
"""
import os
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from ui.controllers.lidar_controller_handler import LidarControllerHandler


class AnalysisControllerMixin:
    """Handles Terrain, DEM styler, Satellite, LiDAR and geoprocessing algorithm dialogs."""

    def apply_shader_preset(self, preset_key: str):
        layer = self.layer_panel.get_active_layer() if hasattr(self, "layer_panel") else None
        if not layer:
            from qgis.core import QgsProject, QgsRasterLayer
            from core.elevation_styler import ElevationStyler
            for l in QgsProject.instance().mapLayers().values():
                if isinstance(l, QgsRasterLayer) and ElevationStyler.is_dem_or_elevation(l):
                    layer = l
                    break
        if not layer:
            self._info("Please select a DEM/Elevation raster layer first.")
            return
        if hasattr(self, "layer_panel") and hasattr(self.layer_panel, "apply_elevation_preset"):
            self.layer_panel.apply_elevation_preset(layer, preset_key)
        else:
            from ui.layers.layer_context_menu import LayerContextMenuHandler
            LayerContextMenuHandler.apply_elevation_preset(getattr(self, "layer_panel", None), layer, preset_key)
        if hasattr(self, "geo_status") and self.geo_status:
            self.geo_status.showMessage(f"Applied terrain shader: {preset_key}", 2500)

    def open_dem_elevation_dialog(self, layer=None):
        target = layer or (self.layer_panel.get_active_layer() if hasattr(self, "layer_panel") else None)
        try:
            from ui.dialogs.dem_elevation_dialog import DEMElevationDialog
            dlg = DEMElevationDialog(map_canvas=getattr(self, "map_canvas", None), target_layer=target, parent=self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open DEM Elevation dialog: {e}")

    def open_slope_dialog(self):        self.processing_dock.open_algorithm("native:slope")
    def open_aspect_dialog(self):       self.processing_dock.open_algorithm("native:aspect")
    def open_hillshade_dialog(self):    self.processing_dock.open_algorithm("native:hillshade")
    def open_tri_dialog(self):          self.processing_dock.open_algorithm("native:roughness")
    def open_tpi_dialog(self):          self.processing_dock.open_algorithm("native:tpi")
    def open_twi_dialog(self):          self.processing_dock.open_algorithm("native:twi")
    def open_curvature_dialog(self):    self.processing_dock.open_algorithm("native:curvature")
    def open_contour_dialog(self):      self.processing_dock.open_algorithm("gdal:contour")
    def open_viewshed(self):            self.processing_dock.open_algorithm("spatial:viewshed")

    def open_volumetric_analysis(self, layer=None):
        target = layer or self.layer_panel.get_active_layer()
        try:
            from ui.dialogs.volumetric_dialog import VolumetricAnalysisDialog
            dlg = VolumetricAnalysisDialog(map_canvas=self.map_canvas, target_layer=target, parent=self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open Volumetric Analysis dialog: {e}")

    def open_cut_fill(self, layer=None):
        target = layer or self.layer_panel.get_active_layer()
        try:
            from ui.dialogs.cut_fill_dialog import CutFillDialog
            dlg = CutFillDialog(map_canvas=self.map_canvas, target_layer=target, parent=self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open Cut & Fill dialog: {e}")

    def open_hydro_fillsinks(self):     self.processing_dock.open_algorithm("hydrology:fillsinks")
    def open_hydro_flowdir(self):       self.processing_dock.open_algorithm("hydrology:flowdir")
    def open_hydro_flowaccum(self):     self.processing_dock.open_algorithm("hydrology:flowaccum")
    def open_hydro_watershed(self):     self.processing_dock.open_algorithm("hydrology:watershed")
    def open_spectral_index(self, id):  self.processing_dock.open_algorithm(id)
    def open_composite_dialog(self):    self.processing_dock.open_algorithm("landsat:composites")
    def open_band_stack_dialog(self):   self.processing_dock.open_algorithm("satellite:bandstack")
    def open_pca_dialog(self):          self.processing_dock.open_algorithm("satellite:pca")
    def open_sam_dialog(self):          self.processing_dock.open_algorithm("satellite:sam")
    def open_band_math_dialog(self):    self.processing_dock.open_algorithm("satellite:bandmath")

    def open_buffer_dialog(self):       self.processing_dock.open_algorithm("native:buffer")
    def open_clip_dialog(self):         self.processing_dock.open_algorithm("native:clip")
    def open_intersect_dialog(self):    self.processing_dock.open_algorithm("native:intersection")
    def open_union_dialog(self):        self.processing_dock.open_algorithm("native:union")
    def open_diff_dialog(self):         self.processing_dock.open_algorithm("native:difference")
    def open_dissolve_dialog(self):     self.processing_dock.open_algorithm("native:dissolve")
    def run_centroids(self):            self.processing_dock.open_algorithm("native:centroids")
    def run_convex_hull(self):          self.processing_dock.open_algorithm("native:convexhull")
    def run_voronoi(self):              self.processing_dock.open_algorithm("native:voronoi")
    def run_merge(self):                self.processing_dock.open_algorithm("native:merge")
    def raster_stats(self):             self.processing_dock.open_algorithm("native:rasterstats")
    def raster_reproject(self):         self.processing_dock.open_algorithm("native:reproject")
    def raster_clip(self):              self.open_crop_raster_dialog()

    def open_road_classification_dialog(self): self.processing_dock.open_algorithm("lidar:classify_roads")
    def open_road_centerline_dialog(self):     self.processing_dock.open_algorithm("lidar:road_centerline")
    def open_road_condition_dialog(self):      self.processing_dock.open_algorithm("lidar:road_condition")

    def open_elevation_profile(self):
        from ui.dialogs.elevation_profile_dialog import ElevationProfileDialog
        if not hasattr(self, "_elev_profile_dialog") or self._elev_profile_dialog is None:
            self._elev_profile_dialog = ElevationProfileDialog(self)
        self._elev_profile_dialog.show()
        self._elev_profile_dialog.raise_()
        self._elev_profile_dialog.activateWindow()

    def open_crop_raster_dialog(self):
        from ui.dialogs.crop_raster_dialog import CropRasterDialog
        dlg = CropRasterDialog(self)
        dlg.exec_()

    def open_3d_viewer(self, target_layer=None):
        from ui.viewer3d import GeoStudio3DViewerWindow
        from qgis.core import QgsProject, QgsMapLayer

        def _is_pc_layer(lyr):
            if not lyr or not lyr.isValid():
                return False
            if hasattr(QgsMapLayer, "PointCloudLayer") and lyr.type() == QgsMapLayer.PointCloudLayer:
                return True
            name = lyr.name().lower()
            if "[lidar]" in name or "cloud" in name:
                return True
            src = (lyr.source() if hasattr(lyr, "source") else "") or ""
            return src.lower().endswith((".las", ".laz", ".copc.laz", ".e57"))

        # 1. Determine layer
        layer = target_layer
        if not layer:
            active = self.layer_panel.get_active_layer()
            if active and _is_pc_layer(active):
                layer = active
            else:
                # Prioritize any Point Cloud / LiDAR layer loaded in the project
                for l in QgsProject.instance().mapLayers().values():
                    if _is_pc_layer(l):
                        layer = l
                        break
                if not layer:
                    layer = active

        if layer:
            raw_src = layer.customProperty("raw_dem_source") or getattr(layer, "_raw_dem_source", None)
            if not raw_src and layer.source() and "_3d_relief.tif" in layer.source():
                try:
                    from osgeo import gdal
                    chk = gdal.Open(layer.source(), gdal.GA_ReadOnly)
                    if chk:
                        raw_meta = chk.GetMetadataItem("RAW_DEM_SOURCE")
                        if raw_meta and os.path.isfile(raw_meta):
                            raw_src = raw_meta
                        chk = None
                except Exception:
                    pass

            src = raw_src if (raw_src and os.path.exists(raw_src)) else (
                layer.customProperty("original_las_path") or (layer.source() if hasattr(layer, "source") else None)
            )
            if src and "_surface.tif" in src:
                for cand in [src.replace("_surface.tif", ".las"), src.replace("_surface.tif", ".laz"), src.replace("_surface.tif", ".copc.laz")]:
                    if os.path.exists(cand):
                        src = cand
                        break

            # If layer is a vector and user didn't right-click it, check if project has LiDAR layer
            if not target_layer and src and src.lower().endswith((".gpkg", ".shp")):
                for l in QgsProject.instance().mapLayers().values():
                    if _is_pc_layer(l):
                        pc_src = l.source()
                        if pc_src and os.path.exists(pc_src):
                            layer = l
                            src = pc_src
                            break

            if src and os.path.exists(src):
                dlg = GeoStudio3DViewerWindow(self, layer=layer, file_path=src)
                dlg.exec_()
                return

        path, _ = QFileDialog.getOpenFileName(
            self, "Open 3D Point Cloud", "",
            "Point Cloud & 3D Vector Files (*.las *.laz *.copc.laz *.e57 *.ply *.xyz *.pts *.csv *.pcd *.gpkg *.shp);;All Files (*)"
        )
        if path:
            dlg = GeoStudio3DViewerWindow(self, file_path=path)
            dlg.exec_()


    def set_lidar_color_mode(self, m: str):
        LidarControllerHandler.set_lidar_color_mode(self, m)

    def adjust_point_cloud_size(self, delta: float):
        layer = self.layer_panel.get_active_layer()
        if not layer:
            from qgis.core import QgsProject, QgsMapLayer
            for l in QgsProject.instance().mapLayers().values():
                if hasattr(QgsMapLayer, "PointCloudLayer") and l.type() == QgsMapLayer.PointCloudLayer:
                    layer = l
                    break
        if layer:
            from core.lidar_styler import LidarStyler
            sz = LidarStyler.set_point_size(layer, delta)
            self.map_canvas.force_refresh_canvas()
            self.geo_status.showMessage(f"Point Size: {sz:.1f}px", 2000)

    def run_lidar_auto_classification(self, layer=None):
        LidarControllerHandler.run_auto_classification(self, layer=layer)

    # ── Swipe Compare ──────────────────────────────────────────────────────
    def open_swipe_compare(self):
        """Open the interactive Layer Swipe Compare dialog (ArcGIS: Compare → Swipe)."""
        try:
            from ui.dialogs.swipe_compare_dialog import SwipeCompareDialog
            if hasattr(self, "_swipe_dialog") and self._swipe_dialog and self._swipe_dialog.isVisible():
                self._swipe_dialog.raise_()
                self._swipe_dialog.activateWindow()
                return
            self._swipe_dialog = SwipeCompareDialog(map_canvas=getattr(self, "map_canvas", None), parent=self)
            self._swipe_dialog.show()
        except Exception as e:
            QMessageBox.critical(self, "Swipe Compare", f"Could not open Swipe Compare: {e}")

    # ── Blend Modes ────────────────────────────────────────────────────────
    def apply_layer_blend_mode(self, mode_name: str):
        """Apply a named blend mode to the active raster layer (ArcGIS: Appearance → Layer Blend)."""
        layer = self.layer_panel.get_active_layer() if hasattr(self, "layer_panel") else None
        if not layer:
            from qgis.core import QgsProject, QgsRasterLayer
            for l in QgsProject.instance().mapLayers().values():
                if isinstance(l, QgsRasterLayer):
                    layer = l
                    break
        if not layer:
            QMessageBox.information(self, "Layer Blend Mode", "Please select a raster layer first.")
            return
        from core.elevation_styler import ElevationStyler
        ElevationStyler.apply_blend_mode(layer, mode_name)
        self.map_canvas.refresh_canvas()
        if hasattr(self, "geo_status") and self.geo_status:
            self.geo_status.showMessage(f"Blend Mode: {mode_name}", 2500)

    # ── Transpose Fields ───────────────────────────────────────────────────
    def open_transpose_fields_dialog(self):
        """Open the Transpose / Pivot Fields geoprocessing dialog (ArcGIS: Data Management → Transpose Fields)."""
        try:
            from ui.dialogs.transpose_fields_dialog import TransposeFieldsDialog
            dlg = TransposeFieldsDialog(map_canvas=getattr(self, "map_canvas", None), parent=self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Transpose Fields", f"Could not open Transpose Fields dialog: {e}")
