# -*- coding: utf-8 -*-
"""
GeoStudio / GeoAnalytica - Data Import / Export Module
Import/Export: Shapefile, GeoPackage, GeoJSON, CSV, KML, DXF.
"""

import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QComboBox, QGroupBox, QFileDialog, QMessageBox,
    QProgressBar, QCheckBox, QLineEdit, QTabWidget
)
from qgis.core import QgsProject, QgsMapLayer, QgsVectorLayer
from core.style import MODULE_STYLE
from .io_operations import export_vector_layer, reproject_vector_layer, merge_vector_layers

STYLE = MODULE_STYLE

FORMAT_MAP = {
    "GeoPackage (.gpkg)":       ("GPKG",    "*.gpkg"),
    "Shapefile (.shp)":         ("ESRI Shapefile", "*.shp"),
    "GeoJSON (.geojson)":       ("GeoJSON", "*.geojson"),
    "KML (.kml)":               ("KML",     "*.kml"),
    "CSV (.csv)":               ("CSV",     "*.csv"),
    "GML (.gml)":               ("GML",     "*.gml"),
    "MapInfo TAB (.tab)":       ("MapInfo File", "*.tab"),
    "DXF (.dxf)":               ("DXF",     "*.dxf"),
    "SQLite (.sqlite)":         ("SQLite",  "*.sqlite"),
    "FlatGeobuf (.fgb)":        ("FlatGeobuf", "*.fgb"),
}


class ImportExportWidget(QWidget):
    """Data Import / Export module for all common geospatial formats."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setStyleSheet(STYLE)
        self._init_ui()
        self._refresh_layers()
        QgsProject.instance().layersAdded.connect(self._refresh_layers)
        QgsProject.instance().layersRemoved.connect(self._refresh_layers)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #e2e8f0; background: #ffffff; border-radius: 4px; top: -1px; }
            QTabWidget::tab-bar { left: 6px; }
            QTabBar::tab { background: #f8fafc; color: #64748b; padding: 6px 14px; font-size: 11px; font-weight: 500; border: 1px solid #e2e8f0; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 4px; margin-top: 2px; }
            QTabBar::tab:selected { background: #ffffff; color: #0f172a; font-weight: bold; border-bottom: 1px solid #ffffff; margin-top: 0px; }
            QTabBar::tab:hover:!selected { background: #f1f5f9; color: #1e293b; }
        """)
        tabs.addTab(self._build_import_tab(), "📥 Import")
        tabs.addTab(self._build_export_tab(), "📤 Export")
        tabs.addTab(self._build_reproject_tab(), "🗺 Reproject & Convert")

        layout.addWidget(tabs)
        self.setLayout(layout)

    def _build_import_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        btn_vector = QPushButton("📂 Import Vector Layer")
        btn_vector.clicked.connect(self._import_vector)
        btn_raster = QPushButton("🏔 Import Raster Layer")
        btn_raster.clicked.connect(self._import_raster)

        csv_box = QGroupBox("Import CSV as Points")
        csv_form = QFormLayout()
        self.csv_x = QLineEdit("longitude")
        self.csv_y = QLineEdit("latitude")
        csv_form.addRow("X/Lon field:", self.csv_x)
        csv_form.addRow("Y/Lat field:", self.csv_y)
        btn_csv = QPushButton("📊 Import CSV as Points")
        btn_csv.clicked.connect(self._import_csv)
        csv_form.addRow(btn_csv)
        csv_box.setLayout(csv_form)

        layout.addWidget(btn_vector)
        layout.addWidget(btn_raster)
        layout.addWidget(csv_box)
        layout.addStretch()
        return widget

    def _build_export_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        form = QFormLayout()
        self.export_layer_combo = QComboBox()
        form.addRow("Layer to Export:", self.export_layer_combo)

        self.export_format_combo = QComboBox()
        for fmt in FORMAT_MAP.keys():
            self.export_format_combo.addItem(fmt)
        form.addRow("Format:", self.export_format_combo)

        self.export_crs_combo = QComboBox()
        common_crs = ["EPSG:4326 (WGS84)", "EPSG:32636 (UTM 36N)", "EPSG:3857 (Web Mercator)", "EPSG:32632 (UTM 32N)", "EPSG:4230 (ED50)"]
        for crs in common_crs:
            self.export_crs_combo.addItem(crs)
        form.addRow("Output CRS:", self.export_crs_combo)

        self.export_selected_only = QCheckBox("Export selected features only")
        form.addRow(self.export_selected_only)

        layout.addLayout(form)
        btn_export = QPushButton("💾 Export Layer")
        btn_export.clicked.connect(self._export_layer)
        layout.addWidget(btn_export)

        self.export_progress = QProgressBar()
        self.export_progress.setRange(0, 100)
        self.export_progress.setFormat("Ready")
        layout.addWidget(self.export_progress)

        layout.addStretch()
        return widget

    def _build_reproject_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        form = QFormLayout()
        self.reproj_layer_combo = QComboBox()
        form.addRow("Layer:", self.reproj_layer_combo)

        self.reproj_crs = QLineEdit("EPSG:4326")
        form.addRow("Target CRS:", self.reproj_crs)

        btn_reproj = QPushButton("🗺 Reproject Layer")
        btn_reproj.clicked.connect(self._reproject_layer)
        form.addRow(btn_reproj)
        layout.addLayout(form)

        merge_box = QGroupBox("Merge Vector Layers")
        merge_layout = QVBoxLayout()
        self.merge_layer1 = QComboBox()
        self.merge_layer2 = QComboBox()
        merge_layout.addWidget(QLabel("Layer 1:"))
        merge_layout.addWidget(self.merge_layer1)
        merge_layout.addWidget(QLabel("Layer 2:"))
        merge_layout.addWidget(self.merge_layer2)
        btn_merge = QPushButton("🔗 Merge Layers")
        btn_merge.clicked.connect(self._merge_layers)
        merge_layout.addWidget(btn_merge)
        merge_box.setLayout(merge_layout)
        layout.addWidget(merge_box)

        layout.addStretch()
        return widget

    def _refresh_layers(self):
        vector_layers = [l for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.VectorLayer]
        all_layers = list(QgsProject.instance().mapLayers().values())

        for combo in (self.export_layer_combo, self.reproj_layer_combo, self.merge_layer1, self.merge_layer2):
            current = combo.currentText()
            combo.clear()
            combo.addItem("-- None --", None)
            source = vector_layers if combo in (self.export_layer_combo, self.merge_layer1, self.merge_layer2) else all_layers
            for l in source:
                combo.addItem(l.name(), l.id())
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _import_vector(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Vector Layer", "", "Vector (*.shp *.gpkg *.geojson *.json *.kml *.gml *.csv *.tab);;All (*)")
        if path:
            name = os.path.splitext(os.path.basename(path))[0]
            layer = QgsVectorLayer(path, name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                if self.iface: self.iface.messageBar().pushSuccess("GeoAnalytica", f"Imported: {name}")
            else:
                QMessageBox.critical(self, "Import Error", f"Could not load: {path}")

    def _import_raster(self):
        from qgis.core import QgsRasterLayer
        path, _ = QFileDialog.getOpenFileName(self, "Import Raster Layer", "", "Raster (*.tif *.tiff *.img *.asc *.nc *.hdf *.vrt);;All (*)")
        if path:
            name = os.path.splitext(os.path.basename(path))[0]
            layer = QgsRasterLayer(path, name)
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                if self.iface: self.iface.messageBar().pushSuccess("GeoAnalytica", f"Imported: {name}")
            else:
                QMessageBox.critical(self, "Import Error", f"Could not load: {path}")

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv);;All (*)")
        if not path:
            return
        x_field, y_field = self.csv_x.text().strip(), self.csv_y.text().strip()
        uri = f"file:///{path}?delimiter=,&xField={x_field}&yField={y_field}&crs=epsg:4326&useHeader=yes"
        name = os.path.splitext(os.path.basename(path))[0]
        layer = QgsVectorLayer(uri, name, "delimitedtext")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            if self.iface: self.iface.messageBar().pushSuccess("GeoAnalytica", f"Imported CSV as points: {name}")
        else:
            QMessageBox.critical(self, "CSV Import Error", f"Could not load CSV. Verify X/Y column names (X={x_field}, Y={y_field}).")

    def _export_layer(self):
        layer_id = self.export_layer_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "No Layer", "Select a layer to export."); return
        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return

        fmt_label = self.export_format_combo.currentText()
        driver_name, ext_filter = FORMAT_MAP[fmt_label]
        ext = ext_filter.replace("*", "")

        path, _ = QFileDialog.getSaveFileName(self, f"Export as {fmt_label}", layer.name() + ext, f"{fmt_label} ({ext_filter})")
        if not path:
            return

        crs_str = self.export_crs_combo.currentText().split(" ")[0]
        self.export_progress.setValue(30)
        self.export_progress.setFormat("Exporting...")

        ok, err_msg = export_vector_layer(layer, path, driver_name, crs_str, self.export_selected_only.isChecked())
        if ok:
            self.export_progress.setValue(100)
            self.export_progress.setFormat("✓ Done")
            if self.iface: self.iface.messageBar().pushSuccess("GeoAnalytica", f"Exported: {os.path.basename(path)}")
        else:
            self.export_progress.setFormat("Error")
            QMessageBox.critical(self, "Export Error", f"Export failed:\n{err_msg}")

    def _reproject_layer(self):
        layer_id = self.reproj_layer_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "No Layer", "Select a layer."); return
        layer = QgsProject.instance().mapLayer(layer_id)
        crs = self.reproj_crs.text().strip()
        try:
            out = reproject_vector_layer(layer, crs)
            if out and self.iface:
                self.iface.messageBar().pushSuccess("GeoAnalytica", f"Reprojected to {crs}")
        except Exception as e:
            QMessageBox.critical(self, "Reproject Error", str(e))

    def _merge_layers(self):
        id1, id2 = self.merge_layer1.currentData(), self.merge_layer2.currentData()
        if not id1 or not id2:
            QMessageBox.warning(self, "No Layers", "Select two layers to merge."); return
        l1 = QgsProject.instance().mapLayer(id1)
        l2 = QgsProject.instance().mapLayer(id2)
        try:
            out = merge_vector_layers(l1, l2)
            if out and self.iface:
                self.iface.messageBar().pushSuccess("GeoAnalytica", "Layers merged!")
        except Exception as e:
            QMessageBox.critical(self, "Merge Error", str(e))
