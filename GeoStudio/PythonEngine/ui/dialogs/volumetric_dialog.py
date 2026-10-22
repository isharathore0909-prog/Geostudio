# -*- coding: utf-8 -*-
"""
GeoStudio - Volumetric Analysis & Stage-Storage Capacity Dialog
Rich interactive dialog with live hypsometric capacity curves, metric cards, and table exports.
"""

from typing import Optional
from PyQt5.QtWidgets import QDialog, QLabel, QTableWidgetItem, QFileDialog, QMessageBox

from qgis.core import QgsProject, QgsRasterLayer
from core.earthworks.volumetrics import VolumetricEngine, VolumetricResult
from core.elevation.elevation_styler import ElevationStyler
from core.style import MODULE_STYLE
from app.ui.dialogs.volumetric_dialog_ui import build_volumetric_ui, create_metric_card


class VolumetricAnalysisDialog(QDialog):
    """Interactive Volumetric & Stage-Storage Analysis Dialog."""

    def __init__(self, map_canvas=None, target_layer=None, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self.initial_layer = target_layer
        self.current_result: Optional[VolumetricResult] = None

        self.setWindowTitle("📐 Volumetric Analysis & Stage-Storage Capacity Engine")
        self.setMinimumSize(820, 640)
        self.resize(860, 680)
        self.setStyleSheet(MODULE_STYLE)

        self._init_ui()
        self._populate_layers()
        if self.initial_layer:
            self._select_layer(self.initial_layer)

    def _init_ui(self):
        build_volumetric_ui(self)

    def _create_metric_card(self, title: str, init_val: str, color_hex: str):
        return create_metric_card(title, init_val, color_hex)

    def _populate_layers(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer) and layer.isValid():
                self.layer_combo.addItem(f"⛰ {layer.name()}", layer.id())

    def _select_layer(self, layer):
        idx = self.layer_combo.findData(layer.id())
        if idx >= 0:
            self.layer_combo.setCurrentIndex(idx)

    def _get_current_layer(self) -> Optional[QgsRasterLayer]:
        lid = self.layer_combo.currentData()
        if lid:
            l = QgsProject.instance().mapLayer(lid)
            if isinstance(l, QgsRasterLayer) and l.isValid():
                return l
        return None

    def _on_layer_changed(self):
        layer = self._get_current_layer()
        if layer:
            self._set_datum_mean()

    def _set_datum_min(self):
        layer = self._get_current_layer()
        if layer:
            stats = ElevationStyler.get_valid_elevation_stats(layer)
            if stats and "min" in stats:
                self.datum_spin.setValue(stats["min"])

    def _set_datum_mean(self):
        layer = self._get_current_layer()
        if layer:
            stats = ElevationStyler.get_valid_elevation_stats(layer)
            if stats and "mean" in stats:
                self.datum_spin.setValue(stats["mean"])

    def _set_datum_max(self):
        layer = self._get_current_layer()
        if layer:
            stats = ElevationStyler.get_valid_elevation_stats(layer)
            if stats and "max" in stats:
                self.datum_spin.setValue(stats["max"])

    def _run_analysis(self):
        layer = self._get_current_layer()
        if not layer:
            QMessageBox.warning(self, "No DEM Layer", "Please select a valid DEM elevation raster layer.")
            return

        try:
            datum = self.datum_spin.value()
            stages = self.stages_spin.value()

            res = VolumetricEngine.compute_volumetrics(
                raster_source=layer,
                datum_elevation=datum,
                num_stages=stages
            )
            self.current_result = res

            # Update Metric Cards
            self.card_vol_above.findChild(QLabel, "val_label").setText(f"{res.volume_above_m3:,.1f} m³")
            self.card_vol_below.findChild(QLabel, "val_label").setText(f"{res.volume_below_m3:,.1f} m³")
            self.card_total_area.findChild(QLabel, "val_label").setText(f"{res.total_surface_area_ha:,.2f} ha")
            self.card_stockpile.findChild(QLabel, "val_label").setText(f"{res.stockpile_estimated_volume_m3:,.1f} m³")

            # Update Plot Canvas
            self.plot_canvas.set_data(res.stage_storage_curve)

            # Update Table
            self.table.setRowCount(len(res.stage_storage_curve))
            for r_idx, step in enumerate(res.stage_storage_curve):
                self.table.setItem(r_idx, 0, QTableWidgetItem(str(step.stage_index)))
                self.table.setItem(r_idx, 1, QTableWidgetItem(f"{step.elevation_m:.2f}"))
                self.table.setItem(r_idx, 2, QTableWidgetItem(f"{step.stage_height_m:.2f}"))
                self.table.setItem(r_idx, 3, QTableWidgetItem(f"{step.surface_area_ha:.3f}"))
                self.table.setItem(r_idx, 4, QTableWidgetItem(f"{step.cumulative_capacity_m3:,.1f}"))
                self.table.setItem(r_idx, 5, QTableWidgetItem(f"{step.volume_above_m3:,.1f}"))

            # Update Report
            report_txt = VolumetricEngine.generate_report_text(res)
            self.report_edit.setText(report_txt)

            self.btn_export_csv.setEnabled(True)
            self.btn_export_report.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Volumetric analysis failed:\n{e}")

    def _export_csv(self):
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Stage-Storage Table", "stage_storage_capacity.csv", "CSV Files (*.csv)")
        if path:
            try:
                VolumetricEngine.export_csv(self.current_result, path)
                QMessageBox.information(self, "Success", f"Exported Stage-Storage CSV to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Could not write CSV:\n{e}")

    def _export_report(self):
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Volumetric Report", "volumetric_report.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.report_edit.toPlainText())
                QMessageBox.information(self, "Success", f"Saved engineering report to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save report:\n{e}")


# Backward compatibility alias
VolumetricDialog = VolumetricAnalysisDialog
