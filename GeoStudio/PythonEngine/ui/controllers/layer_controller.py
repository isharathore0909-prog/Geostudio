# -*- coding: utf-8 -*-
"""
GeoStudio - Layer & Data Sources Controller Mixin
"""
import os
from PyQt5.QtWidgets import QFileDialog


class LayerControllerMixin:
    """Handles adding, removing, and inspecting vector, raster, point cloud, and basemap layers."""

    def add_vector(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Vector Layer", "",
            "Vector Files (*.shp *.gpkg *.geojson *.json *.kml *.csv);;All (*)"
        )
        if path:
            self.layer_panel.load_vector(path)

    def add_raster(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Raster Layer", "",
            "Raster Files (*.tif *.tiff *.img *.asc *.nc *.hdf *.vrt);;All (*)"
        )
        if path:
            self.layer_panel.load_raster(path)

    def add_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add CSV as Points", "", "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            self.layer_panel.load_csv(path)

    def load_las_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load LAS / LAZ / 3D Point Cloud", "",
            "Point Cloud Files (*.las *.laz *.copc.laz *.e57 *.ply *.xyz *.pts *.csv *.pcd);;All Files (*)"
        )
        if path:
            self.layer_panel.load_point_cloud(path)

    def add_wms(self):
        self.layer_panel.load_osm_basemap()

    def add_xyz_basemap(self):
        self.layer_panel.load_osm_basemap()

    def remove_layer(self):
        self.layer_panel.remove_active_layer()

    def layer_properties(self):
        self.layer_panel.show_layer_properties()

    def toggle_layer_dock(self):
        self.layer_dock.setVisible(not self.layer_dock.isVisible())

    def toggle_processing_dock(self):
        self.processing_dock.setVisible(not self.processing_dock.isVisible())

    def show_recently_used(self):
        self.processing_dock.show()

    def open_processing_settings(self):
        self.processing_dock.open_algorithm("tools:settings")

    def toggle_python_console(self):
        self.console_dock.setVisible(not self.console_dock.isVisible())

    def open_plugin_manager(self):
        self._info("Plugin Manager.")

    def open_attribute_table(self):
        self.attr_table_dock.show()
        self.attr_table_dock.load_active_layer(self.layer_panel.get_active_layer())

    def open_gpu_status(self):
        from core.gpu.cuda_detector import get_cuda_hardware_info
        from PyQt5.QtWidgets import QMessageBox
        info = get_cuda_hardware_info()
        status_str = (
            f"GPU Available: {info.is_cuda_available}\n"
            f"Device: {info.device_name}\n"
            f"VRAM: {info.vram_total_gb:.1f} GB (Free: {info.vram_free_gb:.1f} GB)"
        )
        QMessageBox.information(self, "GPU Status", status_str)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            return
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if not file_path or not os.path.exists(file_path):
                continue
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".las", ".laz", ".copc.laz", ".e57", ".ply", ".xyz", ".pts", ".pcd"]:
                self.layer_panel.load_point_cloud(file_path)
            elif ext in [".tif", ".tiff", ".dem", ".dtm", ".dsm", ".hgt", ".asc", ".img", ".nc", ".hdf", ".vrt", ".jp2"]:
                self.layer_panel.load_raster(file_path)
            elif ext in [".shp", ".gpkg", ".geojson", ".json", ".kml", ".gml", ".tab"]:
                self.layer_panel.load_vector(file_path)
            elif ext == ".csv":
                self.layer_panel.load_point_cloud(file_path)
        event.acceptProposedAction()
