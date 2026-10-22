# -*- coding: utf-8 -*-
"""
GeoStudio - Crop / Clip Raster by Polygon Tool & Dialog
Supports:
- Clipping raster orthomosaics & DEMs using vector polygon layers
- Clipping by selected polygon feature on map
- Interactive on-screen polygon drawing for instant raster cropping
- Automatic NoData transparency and CRS re-alignment
"""

import os
import tempfile
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFileDialog, QCheckBox, QGroupBox, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QSize
from qgis.core import (
    QgsProject, QgsMapLayer, QgsGeometry, QgsCoordinateTransform,
    QgsRasterLayer, QgsVectorLayer
)
from osgeo import gdal, ogr

from resources.icons.icon_provider import get_icon


class CropRasterDialog(QDialog):
    """Interactive dialog to crop/clip any raster image by a polygon mask or drawn polygon."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.mw = main_window
        self.setWindowTitle("✂ Crop / Clip Raster by Polygon")
        self.resize(520, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._drawn_geom = None
        self._build_ui()
        self._populate_layers()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # ── 1. Input Raster Layer ─────────────────────────
        grp_raster = QGroupBox("1. Input Raster / Orthomosaic / DEM", self)
        v_raster = QVBoxLayout(grp_raster)
        self.cmb_raster = QComboBox(grp_raster)
        self.cmb_raster.setMinimumHeight(28)
        v_raster.addWidget(self.cmb_raster)
        layout.addWidget(grp_raster)

        # ── 2. Crop Mask Source ───────────────────────────
        grp_mask = QGroupBox("2. Crop Polygon Mask Source", self)
        v_mask = QVBoxLayout(grp_mask)

        h_mask_src = QHBoxLayout()
        self.cmb_mask_mode = QComboBox(grp_mask)
        self.cmb_mask_mode.addItems([
            "Vector Layer (or Selected Feature)",
            "Draw Crop Polygon Interactively on Map"
        ])
        self.cmb_mask_mode.currentIndexChanged.connect(self._on_mode_changed)
        h_mask_src.addWidget(self.cmb_mask_mode)
        v_mask.addLayout(h_mask_src)

        # Vector layer selector row
        self.cmb_vector_layer = QComboBox(grp_mask)
        self.cmb_vector_layer.setMinimumHeight(28)
        v_mask.addWidget(self.cmb_vector_layer)

        # Interactive draw button
        self.btn_draw = QPushButton("  Draw Polygon on Map Canvas", grp_mask)
        self.btn_draw.setIcon(get_icon("add_poly"))
        self.btn_draw.setMinimumHeight(32)
        self.btn_draw.clicked.connect(self._start_interactive_draw)
        self.btn_draw.hide()
        v_mask.addWidget(self.btn_draw)

        self.lbl_drawn_status = QLabel("", grp_mask)
        self.lbl_drawn_status.setStyleSheet("color: #10b981; font-weight: bold;")
        self.lbl_drawn_status.hide()
        v_mask.addWidget(self.lbl_drawn_status)

        layout.addWidget(grp_mask)

        # ── 3. Options ────────────────────────────────────
        grp_opts = QGroupBox("3. Crop Options", self)
        v_opts = QVBoxLayout(grp_opts)

        self.chk_cutline = QCheckBox("Crop to exact polygon shape (mask outside with transparency)", grp_opts)
        self.chk_cutline.setChecked(True)
        v_opts.addWidget(self.chk_cutline)

        self.chk_selected_only = QCheckBox("Use only selected polygon feature(s) from vector layer", grp_opts)
        self.chk_selected_only.setChecked(True)
        v_opts.addWidget(self.chk_selected_only)

        layout.addWidget(grp_opts)

        # ── Progress Bar ──────────────────────────────────
        self.prog = QProgressBar(self)
        self.prog.setRange(0, 0)
        self.prog.setTextVisible(False)
        self.prog.hide()
        layout.addWidget(self.prog)

        # ── 4. Action Buttons ─────────────────────────────
        h_btns = QHBoxLayout()
        h_btns.addStretch()

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        h_btns.addWidget(self.btn_cancel)

        self.btn_crop = QPushButton(" ✂ Crop Raster ", self)
        self.btn_crop.setIcon(get_icon("clip"))
        self.btn_crop.setMinimumHeight(34)
        self.btn_crop.setStyleSheet("background-color: #2563eb; color: white; font-weight: 700; border-radius: 4px; padding: 6px 16px;")
        self.btn_crop.clicked.connect(self._execute_crop)
        h_btns.addWidget(self.btn_crop)

        layout.addLayout(h_btns)

    def _populate_layers(self):
        self.cmb_raster.clear()
        self.cmb_vector_layer.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.RasterLayer and layer.isValid():
                self.cmb_raster.addItem(layer.name(), layer.id())
            elif layer.type() == QgsMapLayer.VectorLayer and layer.isValid():
                self.cmb_vector_layer.addItem(layer.name(), layer.id())

        # Pre-select active layer if raster
        active = self.mw.layer_panel.get_active_layer() if hasattr(self.mw, "layer_panel") else None
        if active and active.type() == QgsMapLayer.RasterLayer:
            idx = self.cmb_raster.findData(active.id())
            if idx >= 0:
                self.cmb_raster.setCurrentIndex(idx)

    def _on_mode_changed(self, idx):
        if idx == 0:  # Vector layer
            self.cmb_vector_layer.show()
            self.chk_selected_only.show()
            self.btn_draw.hide()
            self.lbl_drawn_status.hide()
        else:  # Draw polygon
            self.cmb_vector_layer.hide()
            self.chk_selected_only.hide()
            self.btn_draw.show()
            self.lbl_drawn_status.show()

    def _start_interactive_draw(self):
        self.hide()
        from tools.interactive_tools import GeoMeasureTool

        class DrawCropTool(GeoMeasureTool):
            def __init__(tool_self, canvas, dialog):
                super().__init__(canvas, dialog.mw, measure_type="area")
                tool_self.dialog = dialog

            def canvasPressEvent(tool_self, event):
                super().canvasPressEvent(event)
                if event.button() == Qt.RightButton and len(tool_self._pts) >= 3:
                    closed = list(tool_self._pts) + [tool_self._pts[0]]
                    geom = QgsGeometry.fromPolygonXY([closed])
                    tool_self.dialog.set_drawn_polygon(geom)
                    tool_self.dialog.show()
                    tool_self.dialog.raise_()
                    tool_self.dialog.activateWindow()
                    tool_self.canvas.unsetMapTool(tool_self)

        tool = DrawCropTool(self.mw.map_canvas.canvas, self)
        self.mw.map_canvas.canvas.setMapTool(tool)
        self.mw.geo_status.showMessage("✂ Draw Crop Polygon: Click vertices on map. Right-click to complete crop boundary.", 6000)

    def set_drawn_polygon(self, geom):
        self._drawn_geom = geom
        self.lbl_drawn_status.setText("✓ Custom polygon boundary captured on map!")
        self.lbl_drawn_status.show()

    def _execute_crop(self):
        raster_id = self.cmb_raster.currentData()
        if not raster_id:
            QMessageBox.warning(self, "Missing Input", "Please select an input raster layer.")
            return

        raster_layer = QgsProject.instance().mapLayer(raster_id)
        if not raster_layer or not raster_layer.isValid():
            QMessageBox.warning(self, "Invalid Layer", "Selected raster layer is not valid.")
            return

        src_path = raster_layer.source()
        if not os.path.exists(src_path):
            QMessageBox.warning(self, "File Not Found", f"Raster source file not found on disk:\n{src_path}")
            return

        mode = self.cmb_mask_mode.currentIndex()
        mask_geojson_path = None

        try:
            if mode == 1:  # Drawn polygon
                if not self._drawn_geom:
                    QMessageBox.warning(self, "Missing Polygon", "Please click 'Draw Polygon on Map Canvas' to define the crop boundary first.")
                    return
                # Convert drawn geometry to GeoJSON mask file
                geom_wgs = QgsGeometry(self._drawn_geom)
                dest_crs = self.mw.map_canvas.canvas.mapSettings().destinationCrs()
                if dest_crs.isValid() and raster_layer.crs().isValid() and dest_crs != raster_layer.crs():
                    tr = QgsCoordinateTransform(dest_crs, raster_layer.crs(), QgsProject.instance())
                    geom_wgs.transform(tr)

                mask_geojson_path = os.path.join(tempfile.gettempdir(), f"crop_mask_{os.getpid()}.geojson")
                with open(mask_geojson_path, "w", encoding="utf-8") as f:
                    f.write(f'{{"type": "FeatureCollection", "features": [{{"type": "Feature", "geometry": {geom_wgs.asJson()}}}]}}')

            else:  # Vector layer
                vector_id = self.cmb_vector_layer.currentData()
                if not vector_id:
                    QMessageBox.warning(self, "Missing Vector Layer", "Please select a vector polygon mask layer.")
                    return
                vec_layer = QgsProject.instance().mapLayer(vector_id)
                if not vec_layer or not vec_layer.isValid():
                    QMessageBox.warning(self, "Invalid Layer", "Selected vector mask layer is not valid.")
                    return

                # If selected features only
                if self.chk_selected_only.isChecked() and vec_layer.selectedFeatureCount() > 0:
                    geoms = [f.geometry() for f in vec_layer.selectedFeatures() if f.geometry()]
                    if not geoms:
                        QMessageBox.warning(self, "No Geometry", "Selected features have no geometry.")
                        return
                    merged = geoms[0]
                    for g in geoms[1:]:
                        merged = merged.combine(g)
                    mask_geojson_path = os.path.join(tempfile.gettempdir(), f"crop_mask_{os.getpid()}.geojson")
                    with open(mask_geojson_path, "w", encoding="utf-8") as f:
                        f.write(f'{{"type": "FeatureCollection", "features": [{{"type": "Feature", "geometry": {merged.asJson()}}}]}}')
                else:
                    mask_geojson_path = vec_layer.source()

            # Output cropped raster path
            base_dir = os.path.dirname(src_path)
            if not os.path.isdir(base_dir):
                base_dir = tempfile.gettempdir()
            stem = os.path.splitext(os.path.basename(src_path))[0]
            out_path = os.path.join(base_dir, f"{stem}_cropped.tif")

            # Let user confirm or change output path
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Cropped Raster As", out_path, "GeoTIFF (*.tif *.tiff)")
            if not save_path:
                return

            self.prog.show()
            self.btn_crop.setEnabled(False)

            # Perform GDAL Warp Cutline Clipping
            warp_opts = {
                "cutlineDSName": mask_geojson_path,
                "cropToCutline": self.chk_cutline.isChecked(),
                "dstNodata": 0,
                "format": "GTiff",
                "creationOptions": ["COMPRESS=LZW", "TILED=YES"]
            }

            res = gdal.Warp(save_path, src_path, **warp_opts)
            res = None  # Flush GDAL handle

            # Load cropped raster into canvas
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                crop_name = f"{stem} (Cropped)"
                new_layer = QgsRasterLayer(save_path, crop_name)
                if new_layer.isValid():
                    QgsProject.instance().addMapLayer(new_layer)
                    self.mw.layer_panel.refresh()
                    self.mw.map_canvas.refresh_canvas()
                    self.mw.geo_status.showMessage(f"✓ Cropped raster loaded as '{crop_name}'.", 4000)
                    self.accept()
                else:
                    QMessageBox.warning(self, "Layer Load Error", "Cropped raster was created but could not be loaded into project.")
            else:
                QMessageBox.warning(self, "Crop Failed", "Could not generate cropped raster output.")

        except Exception as e:
            QMessageBox.critical(self, "Crop Error", f"An error occurred while cropping raster:\n{e}")
        finally:
            self.prog.hide()
            self.btn_crop.setEnabled(True)
            if mask_geojson_path and mask_geojson_path.startswith(tempfile.gettempdir()) and os.path.exists(mask_geojson_path):
                try:
                    os.remove(mask_geojson_path)
                except Exception:
                    pass
