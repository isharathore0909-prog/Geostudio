# -*- coding: utf-8 -*-
"""
GeoStudio - Layer Loading Operations
Handles vector, raster (DEM/imagery), point cloud (LAS/LAZ/COPC), OSM basemaps, and CSV importing.
Reports live loading progress, file sizes, and load elapsed time metrics to the footer status bar.
"""

import os
import time
import shutil
import tempfile
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt

from core.elevation_styler import ElevationStyler
from core.raster.raster_optimizer import get_raster_optimizer


def _format_size(file_path: str) -> str:
    """Returns human-readable file size string."""
    try:
        if file_path and os.path.isfile(file_path):
            sz = os.path.getsize(file_path)
            if sz >= 1024 * 1024 * 1024:
                return f"{sz / (1024 * 1024 * 1024):.2f} GB"
            elif sz >= 1024 * 1024:
                return f"{sz / (1024 * 1024):.1f} MB"
            elif sz >= 1024:
                return f"{sz / 1024:.1f} KB"
            return f"{sz} B"
    except Exception:
        pass
    return ""


def _get_status_bar(panel):
    """Safely retrieves the GeoStatusBar or QStatusBar from parent window."""
    try:
        if hasattr(panel, "geo_status") and panel.geo_status:
            return panel.geo_status
        if hasattr(panel, "window"):
            win = panel.window()
            if hasattr(win, "geo_status") and win.geo_status:
                return win.geo_status
            if hasattr(win, "statusBar"):
                return win.statusBar()
    except Exception:
        pass
    return None


class LayerLoader:
    """Helper class containing all file-loading routines for the layer panel."""

    @staticmethod
    def load_vector(panel, path: str):
        if not path or not os.path.exists(path):
            return
        status = _get_status_bar(panel)
        fname = os.path.basename(path)
        sz_str = _format_size(path)
        t0 = time.perf_counter()

        if status and hasattr(status, "start_file_loading"):
            status.start_file_loading(fname, sz_str, "Reading vector dataset...")

        try:
            from qgis.core import QgsVectorLayer, QgsProject
            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(35, "Parsing features & attributes...")

            name = os.path.splitext(fname)[0]
            layer = QgsVectorLayer(path, name, "ogr")

            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(75, "Rendering vector features on map...")

            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                panel.map_canvas.zoom_to_layer(layer)

                def _on_vector_done():
                    t_elapsed = time.perf_counter() - t0
                    if status and hasattr(status, "finish_file_loading"):
                        status.finish_file_loading(fname, t_elapsed, sz_str, "Vector")

                if hasattr(panel, "map_canvas") and hasattr(panel.map_canvas, "wait_for_render_complete"):
                    panel.map_canvas.wait_for_render_complete(_on_vector_done, timeout_ms=3000)
                else:
                    _on_vector_done()
            else:
                t_elapsed = time.perf_counter() - t0
                if status and hasattr(status, "fail_file_loading"):
                    status.fail_file_loading(fname, t_elapsed, "Invalid vector layer format")
                QMessageBox.critical(panel, "Error", f"Failed to load vector layer:\n{path}")
        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            if status and hasattr(status, "fail_file_loading"):
                status.fail_file_loading(fname, t_elapsed, str(e))
            QMessageBox.critical(panel, "Error", f"Failed to load vector layer:\n{e}")


    @staticmethod
    def load_raster(panel, path: str):
        if not path or not os.path.exists(path):
            return

        # Check if point cloud was opened
        if path.lower().endswith(('.las', '.laz', '.copc.laz', '.e57', '.ply', '.xyz', '.pts', '.pcd')):
            panel.load_point_cloud(path)
            return

        status = _get_status_bar(panel)
        fname = os.path.basename(path)
        sz_str = _format_size(path)
        t0 = time.perf_counter()

        if status and hasattr(status, "start_file_loading"):
            status.start_file_loading(fname, sz_str, "Opening raster dataset...")

        try:
            from qgis.core import (
                QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem,
                QgsMultiBandColorRenderer, QgsSingleBandGrayRenderer,
                QgsContrastEnhancement, QgsRasterBandStats
            )
            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(20, "Reading raster dataset & header...")

            name = os.path.splitext(fname)[0]
            layer = QgsRasterLayer(path, name)
            if not layer or not layer.isValid():
                t_elapsed = time.perf_counter() - t0
                if status and hasattr(status, "fail_file_loading"):
                    status.fail_file_loading(fname, t_elapsed, "Invalid raster layer format")
                QMessageBox.critical(panel, "Error", f"Failed to load raster layer:\n{path}")
                return

            # Ensure valid CRS
            orig_crs = layer.crs()
            if not orig_crs.isValid() or not orig_crs.authid():
                ext = layer.extent()
                if ext.xMinimum() > 180.0 or ext.yMinimum() > 90.0 or ext.xMaximum() > 180.0 or ext.yMinimum() < -90.0:
                    orig_crs = QgsCoordinateReferenceSystem("EPSG:32643")
                else:
                    orig_crs = QgsCoordinateReferenceSystem("EPSG:4326")
                layer.setCrs(orig_crs)

            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(50, "Configuring visual color contrast...")

            band_count = layer.bandCount()
            is_dem = ElevationStyler.is_dem_or_elevation(layer)

            if is_dem:
                layer_type_label = "DEM / Elevation"
                relief_layer = ElevationStyler.auto_style_elevation_if_dem(layer)
                if isinstance(relief_layer, QgsRasterLayer) and relief_layer.isValid():
                    layer = relief_layer
            elif band_count >= 3:
                layer_type_label = "RGB Imagery"
                # Multi-band RGB / RGBA Orthomosaic (Optimized for instant 0-255 rendering without 7.5GB full scans)
                try:
                    renderer = QgsMultiBandColorRenderer(layer.dataProvider(), 1, 2, 3)
                    for band_no in [1, 2, 3]:
                        try:
                            data_type = layer.dataProvider().dataType(band_no)
                            # Standard Byte (uint8) RGB orthomosaic - instant (0ms)
                            if data_type == 1:
                                min_v, max_v = 0.0, 255.0
                            else:
                                stats = layer.bandStatistics(
                                    band_no, QgsRasterBandStats.Min | QgsRasterBandStats.Max,
                                    layer.extent(), 250000
                                )
                                min_v = float(stats.minimumValue) if stats.minimumValue is not None else 0.0
                                max_v = float(stats.maximumValue) if stats.maximumValue is not None else 255.0
                                if min_v >= max_v or (min_v == 0.0 and max_v == 0.0):
                                    min_v, max_v = 0.0, 255.0

                            ce = QgsContrastEnhancement(data_type)
                            ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum, True)
                            ce.setMinimumValue(min_v)
                            ce.setMaximumValue(max_v)
                            if band_no == 1:
                                renderer.setRedContrastEnhancement(ce)
                            elif band_no == 2:
                                renderer.setGreenContrastEnhancement(ce)
                            elif band_no == 3:
                                renderer.setBlueContrastEnhancement(ce)
                        except Exception:
                            pass
                    layer.setRenderer(renderer)
                except Exception:
                    pass
                ElevationStyler.apply_resampling(layer, mode="sharp")
            else:
                layer_type_label = "Grayscale Imagery"
                # Single band non-DEM imagery (Fast subsampled stats)
                try:
                    renderer = QgsSingleBandGrayRenderer(layer.dataProvider(), 1)
                    data_type = layer.dataProvider().dataType(1)
                    if data_type == 1:
                        min_v, max_v = 0.0, 255.0
                    else:
                        stats = layer.bandStatistics(
                            1, QgsRasterBandStats.Min | QgsRasterBandStats.Max,
                            layer.extent(), 250000
                        )
                        min_v = float(stats.minimumValue) if stats.minimumValue is not None else 0.0
                        max_v = float(stats.maximumValue) if stats.maximumValue is not None else 255.0
                        if min_v >= max_v:
                            min_v, max_v = 0.0, 255.0

                    ce = QgsContrastEnhancement(data_type)
                    ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum, True)
                    ce.setMinimumValue(min_v)
                    ce.setMaximumValue(max_v)
                    renderer.setContrastEnhancement(ce)
                    layer.setRenderer(renderer)
                except Exception:
                    pass
                ElevationStyler.apply_resampling(layer, mode="sharp")



            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(85, "Rendering high-resolution map...")

            if not QgsProject.instance().mapLayer(layer.id()):
                QgsProject.instance().addMapLayer(layer)
            if hasattr(panel, "map_canvas") and panel.map_canvas:
                panel.map_canvas.zoom_to_layer(layer)
                panel.map_canvas.refresh_canvas()
                if is_dem and hasattr(panel.map_canvas, "update_elevation_legend"):
                    panel.map_canvas.update_elevation_legend(layer)

            # Automatic pyramid / overview optimization in background for large files
            try:
                from core.raster.raster_optimizer import get_raster_optimizer
                canvas_obj = panel.map_canvas.canvas if hasattr(panel, "map_canvas") else None
                get_raster_optimizer().check_and_optimize(layer, canvas=canvas_obj)
            except Exception:
                pass

            def _on_raster_done():
                t_elapsed = time.perf_counter() - t0
                if status and hasattr(status, "finish_file_loading"):
                    status.finish_file_loading(fname, t_elapsed, sz_str, layer_type_label)

            if hasattr(panel, "map_canvas") and hasattr(panel.map_canvas, "wait_for_render_complete"):
                panel.map_canvas.wait_for_render_complete(_on_raster_done, timeout_ms=4000)
            else:
                _on_raster_done()

        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            if status and hasattr(status, "fail_file_loading"):
                status.fail_file_loading(fname, t_elapsed, str(e))
            QMessageBox.critical(panel, "Error", f"Failed to load raster layer:\n{e}")



    @staticmethod
    def load_point_cloud(panel, path: str):
        if not path or not os.path.exists(path):
            return

        status = _get_status_bar(panel)
        fname = os.path.basename(path)
        sz_str = _format_size(path)
        t0 = time.perf_counter()

        if status and hasattr(status, "start_file_loading"):
            status.start_file_loading(fname, sz_str, "Indexing & reading LiDAR point cloud...")

        try:
            from qgis.core import QgsProject, QgsPointCloudLayer
            from core.lidar_styler import LidarStyler
            from core.point_cloud_indexer import PointCloudIndexer

            name = os.path.splitext(fname)[0]
            if name.lower().endswith(".copc"):
                name = os.path.splitext(name)[0]

            copc_path = path
            if not path.lower().endswith(".copc.laz"):
                from ui.dialogs.layer_loading_dialog import LayerLoadingProgressDialog
                dlg = LayerLoadingProgressDialog(
                    parent=panel,
                    file_path=path,
                    layer_type="point_cloud",
                    title="Converting to Cloud-Optimized Point Cloud",
                    message=f"Indexing & generating 3D octree for:\n{fname}",
                    cancel_callback=PointCloudIndexer.cancel,
                    auto_start=False
                )
                dlg.show()
                try:
                    copc_path = PointCloudIndexer.ensure_copc_index(
                        path,
                        progress_callback=dlg.set_progress
                    )
                finally:
                    dlg.close()

                if not copc_path or not os.path.exists(copc_path):
                    t_elapsed = time.perf_counter() - t0
                    if status and hasattr(status, "fail_file_loading"):
                        status.fail_file_loading(fname, t_elapsed, "COPC point cloud indexing cancelled")
                    QMessageBox.warning(
                        panel, "Indexing Cancelled",
                        "COPC point cloud indexing was cancelled or failed."
                    )
                    return

            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(85, "Mounting point cloud in canvas...")

            pc_layer = QgsPointCloudLayer(copc_path, f"{name} [LiDAR]", "copc")
            if not pc_layer or not pc_layer.isValid():
                pc_layer = QgsPointCloudLayer(copc_path, f"{name} [LiDAR]", "pdal")

            if pc_layer and pc_layer.isValid():
                pc_layer.setCustomProperty("original_las_path", path)
                pc_layer.setCustomProperty("copc_path", copc_path)
                pc_layer.setCustomProperty("is_lidar_layer", True)

                # Ensure spatial reference system is properly configured
                if not pc_layer.crs().isValid() or not pc_layer.crs().authid():
                    from qgis.core import QgsCoordinateReferenceSystem
                    ext = pc_layer.extent()
                    if ext.xMinimum() > 180.0 or ext.yMinimum() > 90.0 or ext.xMaximum() > 180.0 or ext.yMinimum() < -90.0:
                        pc_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:32643"))
                    else:
                        pc_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

                if status and hasattr(status, "update_file_loading"):
                    status.update_file_loading(95, "Styling discrete 3D point cloud...")

                LidarStyler.auto_style(pc_layer, point_size=3.5)
                QgsProject.instance().addMapLayer(pc_layer)
                panel.map_canvas.zoom_to_layer(pc_layer)
                panel.map_canvas.refresh_canvas()
                if hasattr(panel.map_canvas, "update_lidar_legend"):
                    panel.map_canvas.update_lidar_legend(pc_layer, "auto")

                def _on_pc_done():
                    t_elapsed = time.perf_counter() - t0
                    if status and hasattr(status, "finish_file_loading"):
                        status.finish_file_loading(fname, t_elapsed, sz_str, "LiDAR / Point Cloud")

                if hasattr(panel, "map_canvas") and hasattr(panel.map_canvas, "wait_for_render_complete"):
                    panel.map_canvas.wait_for_render_complete(_on_pc_done, timeout_ms=3000)
                else:
                    _on_pc_done()
            else:
                t_elapsed = time.perf_counter() - t0
                if status and hasattr(status, "fail_file_loading"):
                    status.fail_file_loading(fname, t_elapsed, "Invalid point cloud layer format")
                QMessageBox.critical(panel, "Error", f"Failed to load Point Cloud layer:\n{path}")

        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            if status and hasattr(status, "fail_file_loading"):
                status.fail_file_loading(fname, t_elapsed, str(e))
            QMessageBox.critical(panel, "Error", f"Failed to load Point Cloud layer:\n{e}")

    @staticmethod
    def load_osm_basemap(panel):
        pass

    @staticmethod
    def load_csv(panel, path: str, x_field: str = "longitude", y_field: str = "latitude"):
        if not path or not os.path.exists(path):
            return
        status = _get_status_bar(panel)
        fname = os.path.basename(path)
        sz_str = _format_size(path)
        t0 = time.perf_counter()

        if status and hasattr(status, "start_file_loading"):
            status.start_file_loading(fname, sz_str, "Parsing CSV points & coordinates...")

        try:
            from qgis.core import QgsVectorLayer, QgsProject
            if status and hasattr(status, "update_file_loading"):
                status.update_file_loading(40, "Reading delimited rows...")

            name = os.path.splitext(fname)[0]
            uri = f"file:///{path.replace(os.sep, '/')}?delimiter=,&xField={x_field}&yField={y_field}&crs=EPSG:4326"
            layer = QgsVectorLayer(uri, name, "delimitedtext")
            if layer and layer.isValid():
                if status and hasattr(status, "update_file_loading"):
                    status.update_file_loading(80, "Adding CSV point layer...")
                QgsProject.instance().addMapLayer(layer)
                panel.map_canvas.zoom_to_layer(layer)
                t_elapsed = time.perf_counter() - t0
                if status and hasattr(status, "finish_file_loading"):
                    status.finish_file_loading(fname, t_elapsed, sz_str, "CSV Points")
            else:
                t_elapsed = time.perf_counter() - t0
                if status and hasattr(status, "fail_file_loading"):
                    status.fail_file_loading(fname, t_elapsed, "Invalid coordinate columns in CSV")
                QMessageBox.critical(panel, "Error", f"Failed to load CSV layer:\n{path}")
        except Exception as e:
            t_elapsed = time.perf_counter() - t0
            if status and hasattr(status, "fail_file_loading"):
                status.fail_file_loading(fname, t_elapsed, str(e))
            QMessageBox.critical(panel, "Error", f"Failed to load CSV layer:\n{e}")

