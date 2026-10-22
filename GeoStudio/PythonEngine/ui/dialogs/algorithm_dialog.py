
# -*- coding: utf-8 -*-
"""
GeoStudio - Universal QGIS Algorithm Execution Dialog
Clean parameter dialog with input parameters, output path, execution log, and help.
"""

import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QRadioButton, QButtonGroup, QTextEdit, QProgressBar,
    QPushButton, QTabWidget, QFileDialog, QGroupBox, QScrollArea, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer

from core.gpu.cuda_detector import CudaDetector
from core.processing.algorithm_registry import AlgorithmDefinition
from core.style import MODULE_STYLE
from ui.runners.algorithm_forms import build_parameters_form
from ui.runners.algorithm_executor import AlgorithmExecutor


class QgisAlgorithmDialog(QDialog):
    """
    Universal QGIS Algorithm Parameter Dialog:
    - Real-time parameter forms
    - Optional processing engine selection for supported algorithms
    - [Parameters], [Log], [Help] tabs
    """

    def __init__(self, algo_def: AlgorithmDefinition, map_canvas=None, main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.algo = algo_def
        self.map_canvas = map_canvas
        self.main_window = main_window or parent

        self.setWindowTitle(f"{self.algo.name}")
        self.setMinimumSize(640, 580)
        self.resize(680, 720)
        self.setStyleSheet(MODULE_STYLE)

        self._init_ui()
        self._refresh_layers()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Tabs (Parameters, Log, Help)
        self.tabs = QTabWidget()

        # Tab 1: Parameters (inside smooth QScrollArea so form inputs never get crushed!)
        self.param_scroll = QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_scroll.setFrameShape(QFrame.NoFrame)
        self.param_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.param_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { width: 8px; }")

        self.param_tab = QWidget()
        param_layout = QVBoxLayout(self.param_tab)
        param_layout.setContentsMargins(14, 14, 14, 14)
        param_layout.setSpacing(10)

        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        build_parameters_form(self)
        param_layout.addLayout(self.form_layout)

        # Processing Engine Group Box (GPU/CPU Acceleration)
        if self.algo.supports_gpu:
            engine_box = QGroupBox("Processing Acceleration Engine")
            engine_box.setStyleSheet("QGroupBox { font-weight: 600; border: 1px solid #e2e8f0; border-radius: 6px; margin-top: 8px; padding-top: 14px; background: #f8fafc; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #0f172a; }")
            engine_layout = QHBoxLayout(engine_box)
            engine_layout.setContentsMargins(10, 8, 10, 8)

            self.engine_btn_group = QButtonGroup(self)
            self.rb_auto = QRadioButton("⚡ Auto (Fastest)")
            self.rb_auto.setChecked(True)
            self.rb_gpu = QRadioButton("🚀 NVIDIA CUDA (GPU)")
            self.rb_cpu = QRadioButton("💻 Multi-Core CPU (C++ / OpenMP)")

            if not CudaDetector.is_cuda_available():
                self.rb_gpu.setEnabled(False)
                self.rb_gpu.setText("🚀 NVIDIA CUDA (Not Detected)")

            self.engine_btn_group.addButton(self.rb_auto)
            self.engine_btn_group.addButton(self.rb_gpu)
            self.engine_btn_group.addButton(self.rb_cpu)

            engine_layout.addWidget(self.rb_auto)
            engine_layout.addWidget(self.rb_gpu)
            engine_layout.addWidget(self.rb_cpu)
            engine_layout.addStretch()

            param_layout.addWidget(engine_box)
        else:
            self.rb_auto = QRadioButton()
            self.rb_auto.setChecked(True)
            self.rb_gpu = QRadioButton()
            self.rb_cpu = QRadioButton()

        # Output Path Selection
        out_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("[Create temporary layer]")
        btn_out_browse = QPushButton("Browse...")
        btn_out_browse.setMinimumWidth(85)
        btn_out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_edit)
        out_row.addWidget(btn_out_browse)

        self.form_layout.addRow("Save Output As:", out_row)

        from PyQt5.QtWidgets import QCheckBox
        self.open_output_cb = QCheckBox("Open output file after running algorithm")
        self.open_output_cb.setChecked(True)
        param_layout.addWidget(self.open_output_cb)
        self.param_scroll.setWidget(self.param_tab)
        self.tabs.addTab(self.param_scroll, "Parameters")

        # Tab 2: Log
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        log_layout.setContentsMargins(12, 12, 12, 12)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setStyleSheet("background: #0f172a; color: #f8fafc; font-family: Consolas, monospace; font-size: 11px; border-radius: 4px; padding: 8px;")
        log_layout.addWidget(self.log_edit)
        self.tabs.addTab(self.log_tab, "Log")

        # Tab 3: Help / Description
        self.help_tab = QWidget()
        help_layout = QVBoxLayout(self.help_tab)
        help_layout.setContentsMargins(14, 14, 14, 14)
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        grp = getattr(self.algo, "group", None) or getattr(self.algo, "category", "Processing")
        help_content = f"<h3>{self.algo.name}</h3><p><b>Group:</b> {grp}</p><p><b>Algorithm ID:</b> <code>{self.algo.algo_id}</code></p><p>{self.algo.description}</p>"
        help_text.setHtml(help_content)
        help_layout.addWidget(help_text)
        self.tabs.addTab(self.help_tab, "Help")

        main_layout.addWidget(self.tabs)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid #cbd5e1; border-radius: 4px; background-color: #f1f5f9; text-align: center; font-size: 10px; font-weight: 600; color: #0f172a; } QProgressBar::chunk { background-color: #0284c7; border-radius: 3px; }")
        main_layout.addWidget(self.progress_bar)

        # Bottom Action Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_run = QPushButton("▶ Run")
        self.btn_run.setObjectName("blueBtn")
        self.btn_run.clicked.connect(self._run_algorithm)
        btn_box.addWidget(self.btn_run)

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("grayBtn")
        self.btn_close.clicked.connect(self.close)
        btn_box.addWidget(self.btn_close)

        main_layout.addLayout(btn_box)

    def _browse_mtl_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Landsat MTL Metadata File", "", "Landsat Metadata (*_MTL.txt);;Text Files (*.txt);;All Files (*.*)")
        if path:
            self.mtl_path_edit.setText(path)
            fn = os.path.basename(path).upper()
            if "LC08" in fn or "LC09" in fn or "LO08" in fn or "LO09" in fn:
                self.sensor_detect_lbl.setText("Auto-detected Sensor: <b>Landsat 8-9 OLI/TIRS</b> (11 Bands)")
            elif "LE07" in fn:
                self.sensor_detect_lbl.setText("Auto-detected Sensor: <b>Landsat 7 ETM+</b> (8 Bands)")
            elif "LT05" in fn or "LT04" in fn:
                self.sensor_detect_lbl.setText("Auto-detected Sensor: <b>Landsat 4-5 TM</b> (7 Bands)")
            else:
                self.sensor_detect_lbl.setText("Auto-detected Sensor: <b>Generic Landsat Scene</b>")

    def _browse_raw_img(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Unreferenced Image", "", "Raster Images (*.tif *.tiff *.jpg *.jpeg *.png *.bmp);;All Files (*.*)")
        if path:
            self.raw_img_edit.setText(path)

    def _get_active_layer(self):
        """Retrieve the currently selected/active layer from layer panel or canvas."""
        try:
            candidates = [
                getattr(self, "main_window", None),
                self.parent(),
                getattr(self.parent(), "main_window", None) if self.parent() else None,
            ]
            for cand in candidates:
                if cand and hasattr(cand, "layer_panel") and hasattr(cand.layer_panel, "get_active_layer"):
                    act = cand.layer_panel.get_active_layer()
                    if act and act.isValid():
                        return act

            if self.map_canvas and hasattr(self.map_canvas, "currentLayer"):
                act = self.map_canvas.currentLayer()
                if act and act.isValid():
                    return act
        except Exception:
            pass
        return None

    def _resolve_lidar_path(self, lyr):
        """Extract a valid LAS/LAZ file path from a QGIS layer."""
        if not lyr or not lyr.isValid():
            return None

        # 1. Custom properties set during layer loading
        for prop in ("original_las_path", "copc_path", "las_path"):
            val = lyr.customProperty(prop)
            if val and os.path.exists(str(val)):
                return str(val)

        # 2. Layer source path
        src = lyr.source() if hasattr(lyr, "source") else ""
        if src:
            clean_src = src.split("|")[0].strip()
            if os.path.exists(clean_src) and clean_src.lower().endswith((".las", ".laz", ".copc.laz", ".e57")):
                return clean_src
            if os.path.exists(src) and src.lower().endswith((".las", ".laz", ".copc.laz", ".e57")):
                return src
            if "_surface.tif" in clean_src:
                for cand_ext in [".copc.laz", ".laz", ".las"]:
                    cand = clean_src.replace("_surface.tif", cand_ext)
                    if os.path.exists(cand):
                        return cand

        # 3. Search common directories by layer base name
        name = lyr.name().replace(" [LiDAR]", "").replace(" [DEM]", "").replace(" [CHM]", "").strip()
        search_dirs = [
            os.path.expanduser(r"~\Downloads"),
            os.path.dirname(src) if src else "",
            os.getcwd(),
        ]
        for folder in search_dirs:
            if not folder or not os.path.isdir(folder):
                continue
            for ext in [".copc.laz", ".laz", ".las"]:
                cand = os.path.join(folder, name + ext)
                if os.path.exists(cand):
                    return cand

        if src and os.path.exists(src) and src.lower().endswith((".las", ".laz", ".copc.laz", ".e57")):
            return src
        return None

    def _refresh_layers(self):
        """Populate layers in raster / point cloud / vector combo boxes and select active layer."""
        try:
            from qgis.core import QgsPointCloudLayer, QgsVectorLayer
        except ImportError:
            QgsPointCloudLayer = None
            QgsVectorLayer = None

        layers = list(QgsProject.instance().mapLayers().values())
        active_lyr = self._get_active_layer()

        # 1. Point Cloud / LiDAR Combos (las_combo)
        if hasattr(self, "las_combo"):
            self.las_combo.clear()
            active_idx = -1
            for lyr in layers:
                if QgsVectorLayer and isinstance(lyr, QgsVectorLayer):
                    continue
                las_path = self._resolve_lidar_path(lyr)
                is_pc = (
                    (QgsPointCloudLayer and isinstance(lyr, QgsPointCloudLayer))
                    or "[lidar]" in lyr.name().lower()
                    or bool(las_path)
                )
                if is_pc and lyr.isValid():
                    target_path = las_path or lyr.source()
                    idx = self.las_combo.count()
                    self.las_combo.addItem(f"☁️ {lyr.name()}", target_path)
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx

            if active_idx >= 0:
                self.las_combo.setCurrentIndex(active_idx)
            elif self.las_combo.count() > 0:
                self.las_combo.setCurrentIndex(0)

        # 2. Conductor Wires Combos (wire_combo)
        if hasattr(self, "wire_combo"):
            self.wire_combo.clear()
            active_idx = -1
            for lyr in layers:
                if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                    idx = self.wire_combo.count()
                    self.wire_combo.addItem(f"⚡ {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx
            for lyr in layers:
                las_path = self._resolve_lidar_path(lyr)
                if las_path or (QgsPointCloudLayer and isinstance(lyr, QgsPointCloudLayer)) or "[lidar]" in lyr.name().lower():
                    idx = self.wire_combo.count()
                    self.wire_combo.addItem(f"☁️ {lyr.name()}", las_path or lyr.source())
                    if active_lyr and lyr.id() == active_lyr.id() and active_idx < 0:
                        active_idx = idx
            if active_idx >= 0:
                self.wire_combo.setCurrentIndex(active_idx)
            elif self.wire_combo.count() > 0:
                self.wire_combo.setCurrentIndex(0)

        # 3. Vegetation / Canopy Combos (veg_combo)
        if hasattr(self, "veg_combo"):
            self.veg_combo.clear()
            active_idx = -1
            for lyr in layers:
                if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                    idx = self.veg_combo.count()
                    self.veg_combo.addItem(f"🌲 {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx
                elif isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                    idx = self.veg_combo.count()
                    self.veg_combo.addItem(f"📍 {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id() and active_idx < 0:
                        active_idx = idx
            for lyr in layers:
                las_path = self._resolve_lidar_path(lyr)
                if las_path or (QgsPointCloudLayer and isinstance(lyr, QgsPointCloudLayer)) or "[lidar]" in lyr.name().lower():
                    idx = self.veg_combo.count()
                    self.veg_combo.addItem(f"☁️ {lyr.name()}", las_path or lyr.source())
            if active_idx >= 0:
                self.veg_combo.setCurrentIndex(active_idx)
            elif self.veg_combo.count() > 0:
                self.veg_combo.setCurrentIndex(0)

        # 4. Raster Combos (raster_combo)
        if hasattr(self, "raster_combo"):
            self.raster_combo.clear()
            active_idx = -1
            for lyr in layers:
                idx = self.raster_combo.count()
                if QgsPointCloudLayer and isinstance(lyr, QgsPointCloudLayer) and lyr.isValid():
                    self.raster_combo.addItem(f"☁️ {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx
                elif isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                    self.raster_combo.addItem(f"🗺 {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx
            if active_idx >= 0:
                self.raster_combo.setCurrentIndex(active_idx)
            elif self.raster_combo.count() > 0:
                self.raster_combo.setCurrentIndex(0)

        # 5. Compare DEM Combo (compare_dem_combo)
        if hasattr(self, "compare_dem_combo"):
            self.compare_dem_combo.clear()
            for lyr in layers:
                if isinstance(lyr, QgsRasterLayer) and lyr.isValid():
                    self.compare_dem_combo.addItem(f"🗺 {lyr.name()}", lyr.id())
            if self.compare_dem_combo.count() > 1:
                self.compare_dem_combo.setCurrentIndex(1)

        # 6. Vector Combos (vector_combo)
        if hasattr(self, "vector_combo"):
            self.vector_combo.clear()
            active_idx = -1
            for lyr in layers:
                if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                    idx = self.vector_combo.count()
                    self.vector_combo.addItem(f"📍 {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx
            if active_idx >= 0:
                self.vector_combo.setCurrentIndex(active_idx)
            elif self.vector_combo.count() > 0:
                self.vector_combo.setCurrentIndex(0)

        # 7. Road Data Combos (road_combo)
        if hasattr(self, "road_combo"):
            self.road_combo.clear()
            active_idx = -1
            # Vectors first (centerlines, polygons, etc.)
            for lyr in layers:
                if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                    idx = self.road_combo.count()
                    self.road_combo.addItem(f"🛣️ {lyr.name()}", lyr.id())
                    if active_lyr and lyr.id() == active_lyr.id():
                        active_idx = idx
            # Point cloud / LiDAR layers next
            for lyr in layers:
                las_path = self._resolve_lidar_path(lyr)
                if las_path or (QgsPointCloudLayer and isinstance(lyr, QgsPointCloudLayer)) or "[lidar]" in lyr.name().lower():
                    idx = self.road_combo.count()
                    self.road_combo.addItem(f"☁️ {lyr.name()}", las_path or lyr.source())
                    if active_lyr and lyr.id() == active_lyr.id() and active_idx < 0:
                        active_idx = idx
            if active_idx >= 0:
                self.road_combo.setCurrentIndex(active_idx)
            elif self.road_combo.count() > 0:
                self.road_combo.setCurrentIndex(0)

        # 8. Reference Centerline Guidance (ref_centerline_combo)
        if hasattr(self, "ref_centerline_combo"):
            self.ref_centerline_combo.clear()
            self.ref_centerline_combo.addItem("[None - Autonomous Corridor Extraction]", "")
            for lyr in layers:
                if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
                    self.ref_centerline_combo.addItem(f"🛣️ {lyr.name()}", lyr.source())

    def _set_observer_to_dem_center(self):
        if not hasattr(self, "raster_combo") or not hasattr(self, "observer_x_spin"):
            return
        r_id = self.raster_combo.currentData()
        if not r_id:
            return
        layer = QgsProject.instance().mapLayer(r_id)
        if layer and layer.isValid():
            ext = layer.extent()
            cx = ext.center().x()
            cy = ext.center().y()
            self.observer_x_spin.setValue(cx)
            self.observer_y_spin.setValue(cy)
            self.log(f"Observer set to DEM Center: ({cx:.2f}, {cy:.2f})")

    def _browse_output(self):
        suffix = "tif" if "raster" in self.algo.dialog_type or "terrain" in self.algo.dialog_type else "gpkg"
        filt = "GeoTIFF Raster (*.tif);;All Files (*.*)" if suffix == "tif" else "GeoPackage (*.gpkg);;Shapefile (*.shp);;All Files (*.*)"
        path, _ = QFileDialog.getSaveFileName(self, f"Save {self.algo.name} Output", "", filt)
        if path:
            self.output_edit.setText(path)

    def log(self, text: str):
        self.log_edit.append(text)
        QApplication.processEvents()

    def _run_algorithm(self):
        AlgorithmExecutor.execute(self)
