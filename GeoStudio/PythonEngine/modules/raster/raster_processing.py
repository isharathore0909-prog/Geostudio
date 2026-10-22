# -*- coding: utf-8 -*-
"""
GeoStudio - Raster & DEM Processing Module
Global Mapper & ArcGIS Style Elevation Rendering, Slope, Aspect, Hillshade, Contours, Reclassify, Focal Statistics.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QPushButton,
    QComboBox, QDoubleSpinBox, QGroupBox, QMessageBox, QProgressBar, QHBoxLayout
)
from qgis.core import QgsProject, QgsMapLayer
from core.elevation_styler import ElevationStyler
from core.style import MODULE_STYLE
from app.modules.raster_operations import run_raster_processing_algo, get_raster_stats_text

STYLE = MODULE_STYLE


class RasterProcessingWidget(QWidget):
    """Raster & DEM Processing: elevation styling, slope, aspect, hillshade, contours, reclassify, focal stats."""

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

        # Input Raster
        input_box = QGroupBox("Input Raster / DEM Layer")
        input_form = QFormLayout()
        self.raster_combo = QComboBox()
        self.band_combo = QComboBox()
        input_form.addRow("Raster:", self.raster_combo)
        input_form.addRow("Band:", self.band_combo)
        self.raster_combo.currentIndexChanged.connect(self._on_raster_changed)
        input_box.setLayout(input_form)
        layout.addWidget(input_box)

        # Elevation Symbology
        style_box = QGroupBox("🏔 Elevation Symbology (Global Mapper / ArcGIS)")
        style_layout = QVBoxLayout()

        btn_full_dialog = QPushButton("⛰ Open Elevation & 3D Dialog...")
        btn_full_dialog.setObjectName("blueBtn")
        btn_full_dialog.clicked.connect(self.open_elevation_dialog)
        style_layout.addWidget(btn_full_dialog)

        quick_row1 = QHBoxLayout()
        btn_gm = QPushButton("🏔 GM Atlas")
        btn_gm.setObjectName("grayBtn")
        btn_gm.clicked.connect(lambda: self._apply_quick_preset("GLOBAL_MAPPER_ATLAS"))
        
        btn_arc = QPushButton("🌍 ArcGIS Earth")
        btn_arc.setObjectName("grayBtn")
        btn_arc.clicked.connect(lambda: self._apply_quick_preset("ARCGIS_ELEVATION"))
        quick_row1.addWidget(btn_gm)
        quick_row1.addWidget(btn_arc)
        style_layout.addLayout(quick_row1)

        quick_row2 = QHBoxLayout()
        btn_hs = QPushButton("💡 3D Hillshade")
        btn_hs.setObjectName("grayBtn")
        btn_hs.clicked.connect(self._apply_quick_hillshade)

        btn_gray = QPushButton("🌓 Auto Contrast")
        btn_gray.setObjectName("grayBtn")
        btn_gray.clicked.connect(self._apply_quick_gray)
        quick_row2.addWidget(btn_hs)
        quick_row2.addWidget(btn_gray)
        style_layout.addLayout(quick_row2)

        style_box.setLayout(style_layout)
        layout.addWidget(style_box)

        # DEM Analysis
        dem_box = QGroupBox("DEM Terrain Analysis")
        dem_layout = QVBoxLayout()

        z_form = QFormLayout()
        self.z_factor = QDoubleSpinBox()
        self.z_factor.setRange(0.0001, 100.0)
        self.z_factor.setValue(1.0)
        self.z_factor.setDecimals(4)
        z_form.addRow("Z Factor:", self.z_factor)
        dem_layout.addLayout(z_form)

        ops = [
            ("🏔 Slope Map", self.run_slope),
            ("🧭 Aspect Map", self.run_aspect),
            ("💡 Generate Hillshade Layer", self.run_hillshade),
            ("📏 Roughness", self.run_roughness),
            ("🌊 TWI", self.run_twi),
        ]
        for label, func in ops:
            btn = QPushButton(label)
            btn.clicked.connect(func)
            dem_layout.addWidget(btn)

        dem_box.setLayout(dem_layout)
        layout.addWidget(dem_box)

        # Contours
        contour_box = QGroupBox("Contour Lines")
        contour_form = QFormLayout()
        self.contour_interval = QDoubleSpinBox()
        self.contour_interval.setRange(0.1, 5000)
        self.contour_interval.setValue(50)
        self.contour_interval.setSuffix(" m")
        contour_form.addRow("Interval:", self.contour_interval)
        btn_contour = QPushButton("📈 Generate Contours")
        btn_contour.clicked.connect(self.run_contours)
        contour_form.addRow(btn_contour)
        contour_box.setLayout(contour_form)
        layout.addWidget(contour_box)

        # Raster Utilities
        calc_box = QGroupBox("Raster Utilities")
        calc_layout = QVBoxLayout()
        btn_stats = QPushButton("📊 Raster Statistics")
        btn_stats.setObjectName("grayBtn")
        btn_stats.clicked.connect(self.show_raster_stats)
        btn_focal = QPushButton("🔵 Focal Mean (Smooth)")
        btn_focal.setObjectName("grayBtn")
        btn_focal.clicked.connect(self.run_focal_mean)
        btn_reproject = QPushButton("🗺 Reproject Raster")
        btn_reproject.setObjectName("grayBtn")
        btn_reproject.clicked.connect(self.run_reproject)
        calc_layout.addWidget(btn_stats)
        calc_layout.addWidget(btn_focal)
        calc_layout.addWidget(btn_reproject)
        calc_box.setLayout(calc_layout)
        layout.addWidget(calc_box)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Ready")
        layout.addWidget(self.progress)

        layout.addStretch()
        self.setLayout(layout)

    def _refresh_layers(self):
        layers = [l for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.RasterLayer]
        current = self.raster_combo.currentText()
        self.raster_combo.clear()
        self.raster_combo.addItem("-- None --", None)
        for l in layers:
            is_dem = ElevationStyler.is_dem_or_elevation(l)
            prefix = "🏔 [DEM] " if is_dem else "🗺 "
            self.raster_combo.addItem(f"{prefix}{l.name()}", l.id())
        idx = self.raster_combo.findText(current)
        if idx >= 0:
            self.raster_combo.setCurrentIndex(idx)

    def _on_raster_changed(self):
        self.band_combo.clear()
        layer = self._get_raster()
        if layer:
            for b in range(1, layer.bandCount() + 1):
                self.band_combo.addItem(f"Band {b}: {layer.bandName(b)}", b)

    def _get_raster(self):
        layer_id = self.raster_combo.currentData()
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def open_elevation_dialog(self):
        layer = self._get_raster()
        try:
            from ui.dialogs.dem_elevation_dialog import DEMElevationDialog
            dlg = DEMElevationDialog(
                map_canvas=getattr(self.iface, "mapCanvas", None),
                target_layer=layer,
                parent=self
            )
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open DEM styling: {e}")

    def _apply_quick_preset(self, preset_key):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer first."); return
        ElevationStyler.apply_elevation_colormap(layer, preset_key=preset_key)
        if hasattr(self.iface, "mapCanvas") and self.iface.mapCanvas():
            self.iface.mapCanvas().refresh()

    def _apply_quick_hillshade(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer first."); return
        ElevationStyler.apply_hillshade(layer, band=1, z_factor=self.z_factor.value(), multidirectional=True)
        if hasattr(self.iface, "mapCanvas") and self.iface.mapCanvas():
            self.iface.mapCanvas().refresh()

    def _apply_quick_gray(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer first."); return
        ElevationStyler.apply_grayscale_contrast(layer, band=1, stretch_type="cumulative_cut")
        if hasattr(self.iface, "mapCanvas") and self.iface.mapCanvas():
            self.iface.mapCanvas().refresh()

    def _run(self, algo, params, name):
        run_raster_processing_algo(algo, params, name, progress_bar=self.progress, iface=self.iface, parent_widget=self)

    def run_slope(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "BAND": 1, "SCALE": self.z_factor.value(), "AS_PERCENT": False,
                  "COMPUTE_EDGES": False, "ZEVENBERGEN": False, "OUTPUT": "TEMPORARY_OUTPUT"}
        self._run("native:slope", params, f"{layer.name()}_slope")

    def run_aspect(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "BAND": 1, "TRIG_ANGLE": False, "ZERO_FLAT": False,
                  "COMPUTE_EDGES": False, "ZEVENBERGEN": False, "OUTPUT": "TEMPORARY_OUTPUT"}
        self._run("native:aspect", params, f"{layer.name()}_aspect")

    def run_hillshade(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "BAND": 1, "Z_FACTOR": self.z_factor.value(),
                  "SCALE": 1.0, "AZIMUTH": 315, "ALTITUDE": 45,
                  "COMPUTE_EDGES": False, "ZEVENBERGEN": False,
                  "MULTIDIRECTIONAL": True, "OUTPUT": "TEMPORARY_OUTPUT"}
        self._run("native:hillshade", params, f"{layer.name()}_hillshade")

    def run_roughness(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "BAND": 1, "COMPUTE_EDGES": False, "OUTPUT": "TEMPORARY_OUTPUT"}
        self._run("native:roughness", params, f"{layer.name()}_roughness")

    def run_twi(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        try:
            params = {"DEM": layer, "TWI": "TEMPORARY_OUTPUT"}
            self._run("saga:topographicwetnessindextwi", params, f"{layer.name()}_TWI")
        except Exception:
            QMessageBox.information(self, "TWI", "SAGA provider not available. Please install SAGA in QGIS.")

    def run_contours(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "BAND": 1, "INTERVAL": self.contour_interval.value(),
                  "FIELD_NAME": "ELEV", "CREATE_3D": False, "IGNORE_NODATA": False,
                  "NODATA": None, "OFFSET": 0, "OUTPUT": "memory:"}
        self._run("gdal:contour", params, f"{layer.name()}_contours")

    def show_raster_stats(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        text = get_raster_stats_text(layer)
        QMessageBox.information(self, "Raster & DEM Statistics", text)

    def run_focal_mean(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "BAND": 1, "NEIGHBORHOOD": 0, "NEIGHBORHOOD_SIZE": 3,
                  "KERNEL_RADIUS": 1, "PIXEL_SIZE": 0, "OUTPUT_TYPE": 5, "OUTPUT": "TEMPORARY_OUTPUT"}
        try:
            self._run("native:focalstatistics", params, f"{layer.name()}_focal_mean")
        except Exception:
            QMessageBox.information(self, "Focal Mean", "Focal statistics not available in this QGIS build.")

    def run_reproject(self):
        layer = self._get_raster()
        if not layer:
            QMessageBox.warning(self, "No Raster", "Select a raster layer."); return
        params = {"INPUT": layer, "TARGET_CRS": "EPSG:4326", "RESAMPLING": 0, "NODATA": None,
                  "TARGET_RESOLUTION": None, "OPTIONS": "", "DATA_TYPE": 0, "TARGET_EXTENT": None,
                  "TARGET_EXTENT_CRS": None, "MULTITHREADING": False, "EXTRA": "", "OUTPUT": "TEMPORARY_OUTPUT"}
        self._run("gdal:warpreproject", params, f"{layer.name()}_WGS84")
