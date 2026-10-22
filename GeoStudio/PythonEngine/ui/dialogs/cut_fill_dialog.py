# -*- coding: utf-8 -*-
"""
GeoStudio - Dedicated Earthwork Cut & Fill Dialog
Interactive dual-surface earthwork quantification, balance plane solver, 3-tone difference styling.
"""

import os
import tempfile
from typing import Optional
from PyQt5.QtWidgets import QDialog, QLabel, QMessageBox, QFileDialog

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
from core.earthworks.cut_fill_engine import CutFillEngine, CutFillResult
from core.elevation.elevation_styler import ElevationStyler
from core.style import MODULE_STYLE
from app.ui.dialogs.cut_fill_dialog_ui import build_cut_fill_ui, create_metric_card


class CutFillDialog(QDialog):
    """Interactive Earthwork Cut & Fill Engineering Dialog."""

    def __init__(self, map_canvas=None, target_layer=None, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self.initial_layer = target_layer
        self.current_result: Optional[CutFillResult] = None

        self.setWindowTitle("🚜 Earthwork Cut & Fill Volumetric Calculator")
        self.setMinimumSize(800, 650)
        self.resize(840, 690)
        self.setStyleSheet(MODULE_STYLE)

        self._init_ui()
        self._populate_layers()
        if self.initial_layer:
            self._select_base_layer(self.initial_layer)

    def _init_ui(self):
        build_cut_fill_ui(self)

    def _create_metric_card(self, title: str, init_val: str, color_hex: str):
        return create_metric_card(title, init_val, color_hex)

    def _populate_layers(self):
        self.base_combo.clear()
        self.comp_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer) and layer.isValid():
                self.base_combo.addItem(f"⛰ {layer.name()}", layer.id())
                self.comp_combo.addItem(f"📐 {layer.name()}", layer.id())

    def _select_base_layer(self, layer):
        idx = self.base_combo.findData(layer.id())
        if idx >= 0:
            self.base_combo.setCurrentIndex(idx)

    def _get_base_layer(self) -> Optional[QgsRasterLayer]:
        lid = self.base_combo.currentData()
        if lid:
            l = QgsProject.instance().mapLayer(lid)
            if isinstance(l, QgsRasterLayer) and l.isValid():
                return l
        return None

    def _get_comp_layer(self) -> Optional[QgsRasterLayer]:
        lid = self.comp_combo.currentData()
        if lid:
            l = QgsProject.instance().mapLayer(lid)
            if isinstance(l, QgsRasterLayer) and l.isValid():
                return l
        return None

    def _on_mode_changed(self):
        is_surface = self.rb_surface.isChecked()
        self.comp_combo.setEnabled(is_surface)
        self.datum_spin.setEnabled(not is_surface)

    def _on_base_changed(self):
        layer = self._get_base_layer()
        if layer:
            stats = ElevationStyler.get_valid_elevation_stats(layer)
            if stats and "mean" in stats:
                self.datum_spin.setValue(stats["mean"])

    def _solve_balance_plane(self):
        layer = self._get_base_layer()
        if not layer:
            QMessageBox.warning(self, "No Base Layer", "Please select a base DEM first.")
            return
        try:
            swell = self.swell_spin.value()
            shrink = self.shrink_spin.value()
            balance_elev = CutFillEngine.find_optimal_balance_plane(
                base_source=layer,
                swell_factor=swell,
                shrinkage_factor=shrink
            )
            self.datum_spin.setValue(balance_elev)
            QMessageBox.information(
                self,
                "Optimal Balance Plane Found",
                f"Calculated zero-net-earthwork balance plane elevation:\n\n"
                f"Elevation: {balance_elev:.3f} m\n"
                f"(Factored Cut Volume will approximately equal Factored Fill Volume)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Solver Error", f"Could not solve balance plane:\n{e}")

    def _browse_diff_path(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Difference GeoTIFF", "cut_fill_diff.tif", "GeoTIFF (*.tif)")
        if path:
            self.out_diff_edit.setText(path)

    def _run_calculation(self):
        base_layer = self._get_base_layer()
        if not base_layer:
            QMessageBox.warning(self, "Error", "Please select a valid Base DEM layer.")
            return

        is_surface = self.rb_surface.isChecked()
        comp_layer = self._get_comp_layer() if is_surface else None

        if is_surface and not comp_layer:
            QMessageBox.warning(self, "Error", "Please select a valid Comparison Design DEM layer.")
            return

        if is_surface and base_layer.id() == comp_layer.id():
            QMessageBox.warning(self, "Error", "Base DEM and Comparison DEM cannot be the same layer.")
            return

        datum = self.datum_spin.value() if not is_surface else None
        swell = self.swell_spin.value()
        shrink = self.shrink_spin.value()

        out_path = self.out_diff_edit.text().strip()
        if not out_path or out_path == "[Create temporary difference layer]":
            out_path = tempfile.mktemp(suffix=".tif")

        def progress_cb(pct, msg):
            self.progress_bar.setValue(int(pct))
            self.progress_bar.setFormat(msg)

        try:
            res = CutFillEngine.compute_cut_fill(
                base_source=base_layer,
                comp_source=comp_layer,
                datum_elevation=datum,
                swell_factor=swell,
                shrinkage_factor=shrink,
                output_diff_path=out_path,
                generate_daylight_vector=self.cb_daylight.isChecked(),
                progress_callback=progress_cb
            )
            self.current_result = res

            # Update Metric Cards
            self.card_cut_vol.findChild(QLabel, "val_label").setText(f"{res.factored_cut_volume_m3:,.1f} m³")
            self.card_fill_vol.findChild(QLabel, "val_label").setText(f"{res.factored_fill_volume_m3:,.1f} m³")
            
            net_sign = "+" if res.net_earthwork_volume_m3 > 0 else ""
            self.card_net_vol.findChild(QLabel, "val_label").setText(f"{net_sign}{res.net_earthwork_volume_m3:,.1f} m³")
            self.card_ratio.findChild(QLabel, "val_label").setText(f"{res.cut_fill_ratio:.3f}")

            # Update Report
            report_txt = CutFillEngine.generate_report_text(res)
            self.report_edit.setText(report_txt)

            # Load into map canvas if checked
            if self.cb_load.isChecked() and os.path.exists(out_path):
                clean_name = base_layer.name().replace(" [DEM]", "").replace(" [3D Relief]", "")
                diff_lyr = QgsRasterLayer(out_path, f"{clean_name}_cut_fill_diff")
                if diff_lyr.isValid():
                    diff_lyr._is_analysis_result = True
                    diff_lyr._is_sub_relief_layer = True
                    if self.cb_style.isChecked():
                        ElevationStyler.apply_cut_fill_colormap(diff_lyr)
                    QgsProject.instance().addMapLayer(diff_lyr)

                if res.daylight_vector_path and os.path.exists(res.daylight_vector_path):
                    daylight_lyr = QgsVectorLayer(res.daylight_vector_path, f"{clean_name}_daylight_boundary", "ogr")
                    if daylight_lyr.isValid():
                        daylight_lyr._is_analysis_result = True
                        QgsProject.instance().addMapLayer(daylight_lyr)

                if self.map_canvas and hasattr(self.map_canvas, "refresh_canvas"):
                    self.map_canvas.refresh_canvas()

            self.btn_export_csv.setEnabled(True)
            self.btn_export_report.setEnabled(True)
            self.progress_bar.setFormat("✓ Computation completed successfully")

        except Exception as e:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Error")
            QMessageBox.critical(self, "Earthwork Error", f"Cut & Fill calculation failed:\n{e}")

    def _export_csv(self):
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Cut & Fill CSV", "cut_fill_quantities.csv", "CSV Files (*.csv)")
        if path:
            try:
                CutFillEngine.export_csv(self.current_result, path)
                QMessageBox.information(self, "Success", f"Exported Cut & Fill quantities to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Could not write CSV:\n{e}")

    def _export_report(self):
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Earthwork Report", "cut_fill_report.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.report_edit.toPlainText())
                QMessageBox.information(self, "Success", f"Saved engineering report to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save report:\n{e}")
