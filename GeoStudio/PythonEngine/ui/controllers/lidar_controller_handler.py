# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Controller Handler
Manages point cloud styling mode dispatch and background auto-classification execution.
"""

import os
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt, QCoreApplication


class LidarControllerHandler:
    """Helper for LiDAR layer visualization modes and auto-classification."""

    @staticmethod
    def set_lidar_color_mode(parent_window, mode_key: str):
        layer = parent_window.layer_panel.get_active_layer()
        if not layer:
            from qgis.core import QgsProject, QgsMapLayer
            for l in QgsProject.instance().mapLayers().values():
                if (hasattr(QgsMapLayer, "PointCloudLayer") and l.type() == QgsMapLayer.PointCloudLayer) or "[LiDAR]" in l.name():
                    layer = l
                    break
        if layer:
            from core.lidar_styler import LidarStyler
            from core.elevation_styler import ElevationStyler
            from qgis.core import QgsMapLayer

            if hasattr(QgsMapLayer, "PointCloudLayer") and layer.type() == QgsMapLayer.PointCloudLayer:
                mode_names = {
                    "rgb_elev": "RGB / Elevation Hybrid",
                    "elevation": "Elevation (Z Height)",
                    "intensity": "Intensity (Laser Reflectance)",
                    "classification": "Classification (ASPRS)",
                    "return_num": "Return Number",
                    "hag": "Height Above Ground (Normalized HAG)",
                    "scan_angle": "Scan Angle",
                    "point_source_id": "Point Source ID (Flight Strip)",
                    "source_layer": "Source Layer / Tile",
                    "segment": "Segment / Cluster",
                    "point_index": "Point Index / GPS Time",
                    "cir": "CIR (Color Infrared)",
                    "ndvi": "NDVI (Vegetation Index)",
                    "ndwi": "NDWI (Water Index)",
                    "point_density": "Point Density",
                    "withheld": "Withheld Flag",
                    "keypoint": "Key Point Flag",
                    "overlap": "Overlap Flag",
                    "return_delta": "Return Height Delta"
                }
                disp_name = mode_names.get(mode_key, mode_key.capitalize())

                if mode_key == "rgb_elev":
                    applied = LidarStyler.apply_rgb_elev(layer)
                elif mode_key == "elevation":
                    applied = LidarStyler.apply_elevation_ramp(layer, "Turbo")
                elif mode_key == "intensity":
                    applied = LidarStyler.apply_intensity_ramp(layer)
                elif mode_key == "rgb":
                    applied = LidarStyler.apply_rgb(layer)
                    if not applied:
                        applied = LidarStyler.apply_rgb_elev(layer)
                        parent_window.geo_status.showMessage("⚠ Point cloud has no embedded RGB channels — displaying Elevation Turbo palette.", 4000)
                elif mode_key == "classification":
                    applied = LidarStyler.apply_classification(layer)
                    source_file = getattr(layer, "source", lambda: "")()
                    if source_file and os.path.exists(source_file):
                        from core.point_cloud_indexer import PointCloudIndexer
                        status = PointCloudIndexer.check_classification_status(source_file)
                        if status.get("is_unclassified", False):
                            ans = QMessageBox.question(
                                parent_window,
                                "Raw Unclassified Point Cloud",
                                "This point cloud contains raw flight data with no ground classification (all points are class 0).\n\n"
                                "Would you like GeoStudio to auto-classify Ground & Vegetation (SMRF / HAG) now using 8-thread CPU/GPU processing?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.Yes
                            )
                            if ans == QMessageBox.Yes:
                                parent_window.run_lidar_auto_classification(layer)
                                return
                elif mode_key == "return_num":
                    applied = LidarStyler.apply_return_number(layer)
                elif mode_key == "hag":
                    applied = LidarStyler.apply_height_above_ground(layer)
                elif mode_key == "scan_angle":
                    applied = LidarStyler.apply_scan_angle(layer)
                elif mode_key == "point_source_id":
                    applied = LidarStyler.apply_point_source_id(layer)
                elif mode_key == "source_layer":
                    applied = LidarStyler.apply_source_layer(layer)
                elif mode_key == "segment":
                    applied = LidarStyler.apply_segment(layer)
                elif mode_key == "point_index":
                    applied = LidarStyler.apply_point_index(layer)
                elif mode_key == "cir":
                    applied = LidarStyler.apply_cir(layer)
                elif mode_key == "ndvi":
                    applied = LidarStyler.apply_ndvi(layer)
                elif mode_key == "ndwi":
                    applied = LidarStyler.apply_ndwi(layer)
                elif mode_key == "point_density":
                    applied = LidarStyler.apply_point_density(layer)
                elif mode_key == "withheld":
                    applied = LidarStyler.apply_withheld_flag(layer)
                elif mode_key == "keypoint":
                    applied = LidarStyler.apply_keypoint_flag(layer)
                elif mode_key == "overlap":
                    applied = LidarStyler.apply_overlap_flag(layer)
                elif mode_key == "return_delta":
                    applied = LidarStyler.apply_return_height_delta(layer)
                else:
                    applied = LidarStyler.apply_elevation_ramp(layer, "Turbo")

                if applied:
                    parent_window.map_canvas.force_refresh_canvas()
                    if hasattr(parent_window.map_canvas, "update_lidar_legend"):
                        parent_window.map_canvas.update_lidar_legend(layer, mode_key)
                    parent_window.geo_status.showMessage(f"LiDAR Display: Colored by {disp_name} for '{layer.name()}'.", 3500)
                else:
                    parent_window.geo_status.showMessage(f"Could not apply {disp_name} renderer (attribute not present).", 3500)

            elif layer.type() == QgsMapLayer.RasterLayer:
                if mode_key in ["elevation", "hag"]:
                    ElevationStyler.apply_scientific_palette(layer, "Turbo")
                    parent_window.map_canvas.force_refresh_canvas()
                    if hasattr(parent_window.map_canvas, "update_elevation_legend"):
                        parent_window.map_canvas.update_elevation_legend(layer)
                    parent_window.geo_status.showMessage(f"Raster Elevation Palette: Turbo applied for '{layer.name()}'.", 3000)
        else:
            parent_window.geo_status.showMessage("Please load or select a LiDAR point cloud (.las, .laz) first.", 3000)

    @staticmethod
    def run_auto_classification(parent_window, layer=None):
        if not layer:
            layer = parent_window.layer_panel.get_active_layer()
        if not layer:
            from qgis.core import QgsProject, QgsMapLayer
            for l in QgsProject.instance().mapLayers().values():
                if (hasattr(QgsMapLayer, "PointCloudLayer") and l.type() == QgsMapLayer.PointCloudLayer) or "[LiDAR]" in l.name():
                    layer = l
                    break
        if not layer:
            parent_window.geo_status.showMessage("Please load or select a LiDAR point cloud (.las, .laz) first.", 3000)
            return

        source_file = getattr(layer, "source", lambda: "")()
        if not source_file or not os.path.exists(source_file):
            parent_window.geo_status.showMessage("Could not locate local file for active point cloud layer.", 4000)
            return

        from core.point_cloud_indexer import PointCloudIndexer
        from qgis.core import QgsProject, QgsPointCloudLayer

        progress = QProgressDialog("Auto-classifying LiDAR Ground & Vegetation...", "Cancel", 0, 100, parent_window)
        progress.setWindowTitle("LiDAR Classification")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(10)
        progress.show()
        QCoreApplication.processEvents()

        def on_progress(pct, msg):
            if progress.wasCanceled():
                PointCloudIndexer.cancel()
            else:
                progress.setValue(pct)
                progress.setLabelText(msg)
                QCoreApplication.processEvents()

        try:
            out_copc = PointCloudIndexer.classify_point_cloud(source_file, progress_callback=on_progress)
            progress.close()

            if out_copc and os.path.exists(out_copc):
                clean_name = os.path.splitext(os.path.basename(out_copc))[0].replace(".copc", "")
                new_layer = QgsPointCloudLayer(out_copc, f"{clean_name} [LiDAR]", "copc")
                if not new_layer.isValid():
                    new_layer = QgsPointCloudLayer(out_copc, f"{clean_name} [LiDAR]", "pdal")

                if new_layer.isValid():
                    from core.lidar_styler import LidarStyler
                    LidarStyler.apply_classification(new_layer)
                    QgsProject.instance().removeMapLayer(layer.id())
                    QgsProject.instance().addMapLayer(new_layer)
                    parent_window.map_canvas.setExtent(new_layer.extent())
                    parent_window.map_canvas.force_refresh_canvas()
                    parent_window.geo_status.showMessage(f"Point cloud auto-classified successfully! ({clean_name})", 4500)
                else:
                    parent_window.geo_status.showMessage("Classification completed, but could not attach layer.", 4000)
            else:
                parent_window.geo_status.showMessage("Classification was cancelled or failed.", 3500)
        except Exception as e:
            progress.close()
            parent_window.geo_status.showMessage(f"Classification error: {e}", 4000)
