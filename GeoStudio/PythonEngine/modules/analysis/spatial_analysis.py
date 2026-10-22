# -*- coding: utf-8 -*-
"""
GeoAnalytica - Spatial Analysis Module
Buffer, Intersect, Union, Clip, Dissolve, Convex Hull, Voronoi, Centroid.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox, QFileDialog,
    QFormLayout, QMessageBox, QProgressBar, QCheckBox, QGridLayout
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.core import (
    QgsProject, QgsMapLayer, QgsVectorLayer, QgsProcessingFeedback,
    QgsCoordinateReferenceSystem
)
import processing
from core.style import MODULE_STYLE

STYLE = MODULE_STYLE


class SpatialAnalysisWidget(QWidget):
    """Spatial Analysis: buffer, intersect, clip, dissolve, union, voronoi, centroid, convex hull."""

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

        # --- Input Layer ---
        input_box = QGroupBox("Input Layer")
        input_form = QFormLayout()
        self.input_combo = QComboBox()
        input_form.addRow("Input:", self.input_combo)
        self.overlay_combo = QComboBox()
        input_form.addRow("Overlay:", self.overlay_combo)
        input_box.setLayout(input_form)
        layout.addWidget(input_box)

        # --- Buffer ---
        buf_box = QGroupBox("Buffer")
        buf_layout = QFormLayout()
        self.buf_dist = QDoubleSpinBox()
        self.buf_dist.setRange(0.001, 1_000_000)
        self.buf_dist.setValue(1000)
        self.buf_dist.setDecimals(3)
        self.buf_dist.setSuffix(" m")
        self.buf_segs = QDoubleSpinBox()
        self.buf_segs.setRange(4, 128)
        self.buf_segs.setValue(16)
        self.buf_segs.setDecimals(0)
        buf_layout.addRow("Distance:", self.buf_dist)
        buf_layout.addRow("Segments:", self.buf_segs)
        buf_btn = QPushButton("▶ Run Buffer")
        buf_btn.setObjectName("blueBtn")
        buf_btn.clicked.connect(self.run_buffer)
        buf_layout.addRow(buf_btn)
        buf_box.setLayout(buf_layout)
        layout.addWidget(buf_box)

        # --- Geoprocessing Operations ---
        ops_box = QGroupBox("Geoprocessing Operations")
        ops_grid = QGridLayout()
        ops_grid.setSpacing(6)
        ops = [
            ("✂ Clip",         self.run_clip),
            ("∩ Intersect",    self.run_intersect),
            ("∪ Union",        self.run_union),
            ("⊘ Difference",   self.run_difference),
            ("◉ Dissolve",     self.run_dissolve),
            ("⌂ Convex Hull",  self.run_convex_hull),
            ("• Centroid",     self.run_centroid),
            ("☆ Voronoi",      self.run_voronoi),
        ]
        for i, (label, func) in enumerate(ops):
            btn = QPushButton(label)
            btn.setObjectName("toolBtn")
            btn.clicked.connect(func)
            row = i // 2
            col = i % 2
            ops_grid.addWidget(btn, row, col)
        ops_box.setLayout(ops_grid)
        layout.addWidget(ops_box)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Ready")
        layout.addWidget(self.progress)

        layout.addStretch()
        self.setLayout(layout)

    def _refresh_layers(self):
        """Populate layer combos with current vector layers."""
        layers = [
            l for l in QgsProject.instance().mapLayers().values()
            if l.type() == QgsMapLayer.VectorLayer
        ]
        for combo in (self.input_combo, self.overlay_combo):
            current = combo.currentText()
            combo.clear()
            combo.addItem("-- None --", None)
            for l in layers:
                combo.addItem(l.name(), l.id())
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _get_input_layer(self):
        layer_id = self.input_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "No Layer", "Please select an input layer.")
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def _get_overlay_layer(self):
        layer_id = self.overlay_combo.currentData()
        if not layer_id:
            QMessageBox.warning(self, "No Overlay", "Please select an overlay layer.")
            return None
        return QgsProject.instance().mapLayer(layer_id)

    def _run_algo(self, algo, params, result_name):
        """Run a processing algorithm and add result to project."""
        self.progress.setFormat(f"Running {result_name}...")
        self.progress.setValue(10)
        try:
            feedback = QgsProcessingFeedback()
            result = processing.run(algo, params, feedback=feedback)
            output = result.get("OUTPUT") or result.get("output")
            if output:
                if isinstance(output, QgsVectorLayer):
                    output.setName(result_name)
                    QgsProject.instance().addMapLayer(output)
                elif isinstance(output, str):
                    layer = QgsVectorLayer(output, result_name, "ogr")
                    if layer.isValid():
                        QgsProject.instance().addMapLayer(layer)
                self.progress.setValue(100)
                self.progress.setFormat(f"✓ {result_name} done")
                self.iface.messageBar().pushSuccess("GeoAnalytica", f"{result_name} completed!")
            else:
                self.progress.setFormat("No output produced")
        except Exception as e:
            self.progress.setFormat("Error")
            QMessageBox.critical(self, "Processing Error", str(e))

    def focus_buffer(self):
        if hasattr(self, "buf_dist"):
            self.buf_dist.setFocus()
            self.buf_dist.selectAll()

    def run_buffer(self):
        layer = self._get_input_layer()
        if not layer:
            return
        params = {
            "INPUT": layer,
            "DISTANCE": self.buf_dist.value(),
            "SEGMENTS": int(self.buf_segs.value()),
            "END_CAP_STYLE": 0,
            "JOIN_STYLE": 0,
            "MITER_LIMIT": 2,
            "DISSOLVE": False,
            "OUTPUT": "memory:",
        }
        self._run_algo("native:buffer", params, f"{layer.name()}_buffer")

    def run_clip(self):
        input_l = self._get_input_layer()
        overlay_l = self._get_overlay_layer()
        if not input_l or not overlay_l:
            return
        params = {"INPUT": input_l, "OVERLAY": overlay_l, "OUTPUT": "memory:"}
        self._run_algo("native:clip", params, f"{input_l.name()}_clip")

    def run_intersect(self):
        input_l = self._get_input_layer()
        overlay_l = self._get_overlay_layer()
        if not input_l or not overlay_l:
            return
        params = {"INPUT": input_l, "OVERLAY": overlay_l, "OUTPUT": "memory:"}
        self._run_algo("native:intersection", params, f"{input_l.name()}_intersect")

    def run_union(self):
        input_l = self._get_input_layer()
        overlay_l = self._get_overlay_layer()
        if not input_l or not overlay_l:
            return
        params = {"INPUT": input_l, "OVERLAY": overlay_l, "OUTPUT": "memory:"}
        self._run_algo("native:union", params, f"{input_l.name()}_union")

    def run_difference(self):
        input_l = self._get_input_layer()
        overlay_l = self._get_overlay_layer()
        if not input_l or not overlay_l:
            return
        params = {"INPUT": input_l, "OVERLAY": overlay_l, "OUTPUT": "memory:"}
        self._run_algo("native:difference", params, f"{input_l.name()}_diff")

    def run_dissolve(self):
        layer = self._get_input_layer()
        if not layer:
            return
        params = {"INPUT": layer, "FIELD": [], "OUTPUT": "memory:"}
        self._run_algo("native:dissolve", params, f"{layer.name()}_dissolve")

    def run_convex_hull(self):
        layer = self._get_input_layer()
        if not layer:
            return
        params = {"INPUT": layer, "OUTPUT": "memory:"}
        self._run_algo("native:convexhull", params, f"{layer.name()}_convexhull")

    def run_centroid(self):
        layer = self._get_input_layer()
        if not layer:
            return
        params = {"INPUT": layer, "ALL_PARTS": False, "OUTPUT": "memory:"}
        self._run_algo("native:centroids", params, f"{layer.name()}_centroids")

    def run_voronoi(self):
        layer = self._get_input_layer()
        if not layer:
            return
        params = {"INPUT": layer, "BUFFER": 0, "OUTPUT": "memory:"}
        self._run_algo("native:voronoipolygons", params, f"{layer.name()}_voronoi")
