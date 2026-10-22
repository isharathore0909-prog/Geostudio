# -*- coding: utf-8 -*-
"""
GeoStudio - Elevation Profile Dialog
Provides interactive 2D elevation profile extraction, visualization,
terrain statistics (gain/loss/slope), and CSV/PNG export.
"""

import math
import csv
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QFileDialog, QMessageBox, QFrame
)
from PyQt5.QtGui import QImage
from qgis.core import (
    QgsProject, QgsMapLayer, QgsPointXY, QgsDistanceArea
)

from ui.canvas.elevation_plot_canvas import ElevationPlotCanvas


class ElevationProfileDialog(QDialog):
    """Main Elevation Profile Window."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.mw = main_window
        self.setWindowTitle("Elevation Profile & Terrain Transect")
        self.resize(960, 580)
        self.setMinimumSize(800, 450)

        self._distances = []
        self._elevations = []
        self._pts = []

        self._init_ui()
        self._populate_layers()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # ── Header & Toolbar ──────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        lbl_dem = QLabel("DEM Surface:")
        lbl_dem.setStyleSheet("font-weight: 600; color: #334155;")
        top_bar.addWidget(lbl_dem)

        self.combo_layer = QComboBox()
        self.combo_layer.setMinimumWidth(180)
        self.combo_layer.setStyleSheet("padding: 4px 8px; font-size: 12px;")
        top_bar.addWidget(self.combo_layer, 2)

        lbl_samp = QLabel("Samples:")
        lbl_samp.setStyleSheet("font-weight: 600; color: #334155;")
        top_bar.addWidget(lbl_samp)

        self.spin_samples = QSpinBox()
        self.spin_samples.setRange(50, 2000)
        self.spin_samples.setValue(300)
        self.spin_samples.setSingleStep(50)
        self.spin_samples.setFixedWidth(75)
        self.spin_samples.setStyleSheet("padding: 3px 6px; font-size: 12px;")
        top_bar.addWidget(self.spin_samples)

        btn_draw = QPushButton("✏ Draw Profile")
        btn_draw.setToolTip("Draw interactive transect line across map canvas")
        btn_draw.setStyleSheet(
            "background: #0284c7; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px; font-size: 12px;"
        )
        btn_draw.clicked.connect(self._activate_draw_tool)
        top_bar.addWidget(btn_draw)

        btn_invert = QPushButton("⇄ Invert")
        btn_invert.setToolTip("Reverse profile direction (A ⇄ B)")
        btn_invert.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        btn_invert.clicked.connect(self._invert_transect)
        top_bar.addWidget(btn_invert)

        top_bar.addStretch(1)

        btn_export_csv = QPushButton("📊 Export CSV")
        btn_export_csv.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        btn_export_csv.clicked.connect(self._export_csv)
        top_bar.addWidget(btn_export_csv)

        btn_export_img = QPushButton("📷 Export PNG")
        btn_export_img.setStyleSheet("padding: 5px 10px; font-size: 12px;")
        btn_export_img.clicked.connect(self._export_image)
        top_bar.addWidget(btn_export_img)

        layout.addLayout(top_bar)

        # ── Plot Canvas ───────────────────────────────────
        self.plot_canvas = ElevationPlotCanvas(self)
        layout.addWidget(self.plot_canvas, 1)

        # ── Terrain Statistics Bar ────────────────────────
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            "background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px;"
        )
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_length = QLabel("Length: --")
        self.lbl_min_e = QLabel("Min Elev: --")
        self.lbl_max_e = QLabel("Max Elev: --")
        self.lbl_gain = QLabel("Gain (+): --")
        self.lbl_loss = QLabel("Loss (-): --")
        self.lbl_slope = QLabel("Max Slope: --")

        for lbl in [self.lbl_length, self.lbl_min_e, self.lbl_max_e, self.lbl_gain, self.lbl_loss, self.lbl_slope]:
            lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #1e293b;")
            stats_layout.addWidget(lbl)
            stats_layout.addStretch()

        layout.addWidget(stats_frame)

    def _populate_layers(self):
        self.combo_layer.clear()
        layers = list(QgsProject.instance().mapLayers().values())
        for l in layers:
            if l.type() == QgsMapLayer.RasterLayer and l.isValid():
                self.combo_layer.addItem(l.name(), l.id())

        active = self.mw.layer_panel.get_active_layer() if hasattr(self.mw, "layer_panel") else None
        if active and active.type() == QgsMapLayer.RasterLayer:
            idx = self.combo_layer.findData(active.id())
            if idx >= 0:
                self.combo_layer.setCurrentIndex(idx)

    def _activate_draw_tool(self):
        from tools.profile_line_tool import GeoProfileLineTool
        tool = GeoProfileLineTool(self.mw.map_canvas.canvas, self.mw)
        tool.profile_line_drawn.connect(self.calculate_profile)
        self.mw.map_canvas.canvas.setMapTool(tool)
        self.mw.geo_status.showMessage("Click on map to draw transect line. Right-click when finished.", 5000)

    def calculate_profile(self, pts):
        if not pts or len(pts) < 2:
            return
        self._pts = pts
        layer_id = self.combo_layer.currentData()
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            self._populate_layers()
            layer_id = self.combo_layer.currentData()
            layer = QgsProject.instance().mapLayer(layer_id)

        if not layer:
            QMessageBox.warning(self, "No DEM Layer", "Please load or select a DEM raster layer first.")
            return

        from core.elevation_styler import ElevationStyler
        num_samples = self.spin_samples.value()

        da = QgsDistanceArea()
        dest_crs = self.mw.map_canvas.canvas.mapSettings().destinationCrs()
        da.setSourceCrs(dest_crs, QgsProject.instance().transformContext())
        da.setEllipsoid("WGS84")

        is_geographic = dest_crs.isGeographic() or (abs(pts[0].x()) <= 180.0 and abs(pts[0].y()) <= 90.0)

        def seg_dist(p1, p2):
            if is_geographic:
                lat1, lon1 = math.radians(p1.y()), math.radians(p1.x())
                lat2, lon2 = math.radians(p2.y()), math.radians(p2.x())
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat / 2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0)**2
                c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
                return 6378137.0 * c
            return float(da.measureLine(p1, p2))

        segment_lengths = [seg_dist(pts[i - 1], pts[i]) for i in range(1, len(pts))]
        total_len = sum(segment_lengths)

        if total_len <= 0:
            return

        distances = []
        elevations = []

        step_dist = total_len / (num_samples - 1)
        seg_idx = 0
        seg_accum = 0.0

        for s in range(num_samples):
            target_d = s * step_dist
            while seg_idx < len(segment_lengths) - 1 and target_d > (seg_accum + segment_lengths[seg_idx]):
                seg_accum += segment_lengths[seg_idx]
                seg_idx += 1

            p1 = pts[seg_idx]
            p2 = pts[seg_idx + 1]
            seg_len = max(1e-6, segment_lengths[seg_idx])
            t = max(0.0, min(1.0, (target_d - seg_accum) / seg_len))

            samp_pt = QgsPointXY(p1.x() + t * (p2.x() - p1.x()), p1.y() + t * (p2.y() - p1.y()))
            val, _ = ElevationStyler.sample_elevation_at_point(layer, samp_pt, map_crs=dest_crs, band=1)

            if val is None:
                val = elevations[-1] if elevations else 0.0

            distances.append(target_d)
            elevations.append(val)

        self._distances = distances
        self._elevations = elevations
        self.plot_canvas.set_data(distances, elevations)
        self._update_statistics(total_len, elevations, distances)
        self.show()
        self.raise_()
        self.activateWindow()

    def _update_statistics(self, total_len, elevations, distances):
        if not elevations:
            return
        min_e = min(elevations)
        max_e = max(elevations)

        gain = sum(max(0.0, elevations[i] - elevations[i - 1]) for i in range(1, len(elevations)))
        loss = sum(max(0.0, elevations[i - 1] - elevations[i]) for i in range(1, len(elevations)))

        max_slope_deg = 0.0
        for i in range(1, len(elevations)):
            diff = abs(elevations[i] - elevations[i - 1])
            dx = distances[i] - distances[i - 1]
            if dx > 0:
                slope = math.degrees(math.atan(diff / dx))
                if slope > max_slope_deg:
                    max_slope_deg = slope

        len_str = f"{total_len/1000:.2f} km" if total_len >= 1000 else f"{total_len:.1f} m"
        self.lbl_length.setText(f"Length: {len_str}")
        self.lbl_min_e.setText(f"Min Elev: {min_e:.1f} m")
        self.lbl_max_e.setText(f"Max Elev: {max_e:.1f} m")
        self.lbl_gain.setText(f"Gain (+): {gain:.1f} m")
        self.lbl_loss.setText(f"Loss (-): {loss:.1f} m")
        self.lbl_slope.setText(f"Max Slope: {max_slope_deg:.1f}°")

    def _invert_transect(self):
        if self._pts:
            self._pts.reverse()
            self.calculate_profile(self._pts)

    def _export_csv(self):
        if not self._distances:
            QMessageBox.information(self, "No Data", "Generate an elevation profile first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Profile CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Distance_m", "Elevation_m"])
                for d, e in zip(self._distances, self._elevations):
                    writer.writerow([f"{d:.3f}", f"{e:.3f}"])
            QMessageBox.information(self, "Exported", f"Successfully exported profile data to:\n{path}")

    def _export_image(self):
        if not self._distances:
            QMessageBox.information(self, "No Data", "Generate an elevation profile first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Profile Image", "", "PNG Image (*.png);;JPEG Image (*.jpg)")
        if path:
            img = QImage(self.plot_canvas.size(), QImage.Format_ARGB32_Premultiplied)
            self.plot_canvas.render(img)
            img.save(path)
            QMessageBox.information(self, "Exported", f"Successfully saved profile plot to:\n{path}")
