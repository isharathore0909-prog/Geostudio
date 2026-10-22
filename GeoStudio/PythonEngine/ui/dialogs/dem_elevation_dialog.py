# -*- coding: utf-8 -*-
"""
GeoStudio - DEM / Elevation Symbology & 3D Relief Dialog
Provides full Global Mapper & ArcGIS style elevation styling controls.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QCheckBox,
    QTabWidget, QWidget, QGroupBox, QSlider, QMessageBox
)
from PyQt5.QtCore import Qt
from qgis.core import QgsProject, QgsRasterLayer, QgsMapLayer
from core.elevation_styler import ElevationStyler, ELEVATION_PRESETS
from app.ui.canvas.dem_elevation_preview import ColorRampPreviewWidget, DIALOG_STYLE


class DEMElevationDialog(QDialog):
    """Dedicated dialog for Global Mapper / ArcGIS style DEM, DTM, and DSM elevation symbology."""

    def __init__(self, map_canvas=None, target_layer=None, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self.target_layer = target_layer
        self.setWindowTitle("🏔 DEM / Elevation Symbology & 3D Relief")
        self.setMinimumWidth(560)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()
        self._populate_layers()

        if self.target_layer:
            idx = self.layer_combo.findData(self.target_layer.id())
            if idx >= 0:
                self.layer_combo.setCurrentIndex(idx)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Layer Selection & Quick Stats
        top_group = QGroupBox("Elevation Layer Selection")
        top_form = QFormLayout()
        
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        top_form.addRow("Target DEM/DTM/DSM:", self.layer_combo)

        self.stats_label = QLabel("Min: -- | Max: -- | Mean: -- | NoData: --")
        self.stats_label.setStyleSheet("color: #1e40af; font-size: 11px; font-weight: bold;")
        top_form.addRow("Statistics:", self.stats_label)

        top_group.setLayout(top_form)
        main_layout.addWidget(top_group)

        # Render Modes (Tabs)
        self.tabs = QTabWidget()

        # Tab 1: Topographic / Elevation Colormap
        tab_topo = QWidget()
        layout_topo = QVBoxLayout(tab_topo)
        
        form_topo = QFormLayout()
        self.preset_combo = QComboBox()
        for key, pinfo in ELEVATION_PRESETS.items():
            self.preset_combo.addItem(pinfo["name"], key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        form_topo.addRow("Elevation Palette:", self.preset_combo)

        self.ramp_preview = ColorRampPreviewWidget()
        form_topo.addRow("Color Ramp:", self.ramp_preview)

        range_layout = QHBoxLayout()
        self.spin_min_val = QDoubleSpinBox()
        self.spin_min_val.setRange(-20000.0, 20000.0)
        self.spin_min_val.setDecimals(2)
        self.spin_min_val.setSuffix(" m")

        self.spin_max_val = QDoubleSpinBox()
        self.spin_max_val.setRange(-20000.0, 20000.0)
        self.spin_max_val.setDecimals(2)
        self.spin_max_val.setSuffix(" m")

        range_layout.addWidget(QLabel("Min:"))
        range_layout.addWidget(self.spin_min_val)
        range_layout.addWidget(QLabel("Max:"))
        range_layout.addWidget(self.spin_max_val)
        form_topo.addRow("Elevation Range:", range_layout)

        btn_row_bounds = QHBoxLayout()
        btn_cut_reset = QPushButton("Reset to 2%–98% Cut")
        btn_cut_reset.setObjectName("secondaryBtn")
        btn_cut_reset.clicked.connect(self._reset_to_cut)
        btn_full_reset = QPushButton("Reset to Full Min–Max")
        btn_full_reset.setObjectName("secondaryBtn")
        btn_full_reset.clicked.connect(self._reset_to_full)
        btn_row_bounds.addWidget(btn_cut_reset)
        btn_row_bounds.addWidget(btn_full_reset)
        form_topo.addRow("", btn_row_bounds)

        self.chk_draped_relief = QCheckBox("💡 Blend with 3D Shaded Relief (Global Mapper 3D terrain shadows)")
        self.chk_draped_relief.setChecked(True)
        self.chk_invert = QCheckBox("Invert Colormap Colors")
        self.chk_invert.toggled.connect(self._on_preset_changed)
        self.chk_bilinear = QCheckBox("Smooth Bilinear Resampling (Anti-aliased terrain)")
        self.chk_bilinear.setChecked(True)
        form_topo.addRow("", self.chk_draped_relief)
        form_topo.addRow("", self.chk_invert)
        form_topo.addRow("", self.chk_bilinear)

        # ── Blend Mode (ArcGIS: Appearance → Layer Blend) ──────────────────
        from core.elevation_styler import ElevationStyler
        self.blend_combo = QComboBox()
        self.blend_combo.setToolTip(
            "Layer Blend Mode — how this layer composites over layers beneath it.\n"
            "Multiply: makes white transparent (ideal for draping hillshade shadow over color ramp).\n"
            "Screen: makes black transparent (lightens map).\n"
            "Normal: standard rendering (no blending)."
        )
        self.blend_combo.addItem("Normal (no blend)", "Normal")
        for mode_name in [
            "Multiply  ⭐ (hillshade over color ramp)",
            "Screen  ⭐ (light glow effect)",
            "Overlay", "Hard Light", "Soft Light",
            "Darken", "Lighten",
            "Color Dodge", "Color Burn",
            "Difference", "Exclusion",
        ]:
            key = mode_name.split("  ")[0].split(" ⭐")[0].strip()
            self.blend_combo.addItem(mode_name, key)
        form_topo.addRow("🎨 Layer Blend Mode:", self.blend_combo)


        layout_topo.addLayout(form_topo)
        self.tabs.addTab(tab_topo, "🏔 Topographic Color Ramp")

        # Tab 2: 3D Hillshade
        tab_hillshade = QWidget()
        layout_hillshade = QVBoxLayout(tab_hillshade)
        form_hillshade = QFormLayout()

        az_row = QHBoxLayout()
        self.slider_azimuth = QSlider(Qt.Horizontal)
        self.slider_azimuth.setRange(0, 360)
        self.slider_azimuth.setValue(315)
        self.spin_azimuth = QDoubleSpinBox()
        self.spin_azimuth.setRange(0.0, 360.0)
        self.spin_azimuth.setValue(315.0)
        self.spin_azimuth.setSuffix("°")
        self.slider_azimuth.valueChanged.connect(lambda v: self.spin_azimuth.setValue(float(v)))
        self.spin_azimuth.valueChanged.connect(lambda v: self.slider_azimuth.setValue(int(v)))
        az_row.addWidget(self.slider_azimuth, 1)
        az_row.addWidget(self.spin_azimuth)
        form_hillshade.addRow("Sun Azimuth (Lighting Angle):", az_row)

        alt_row = QHBoxLayout()
        self.slider_altitude = QSlider(Qt.Horizontal)
        self.slider_altitude.setRange(0, 90)
        self.slider_altitude.setValue(45)
        self.spin_altitude = QDoubleSpinBox()
        self.spin_altitude.setRange(0.0, 90.0)
        self.spin_altitude.setValue(45.0)
        self.spin_altitude.setSuffix("°")
        self.slider_altitude.valueChanged.connect(lambda v: self.spin_altitude.setValue(float(v)))
        self.spin_altitude.valueChanged.connect(lambda v: self.slider_altitude.setValue(int(v)))
        alt_row.addWidget(self.slider_altitude, 1)
        alt_row.addWidget(self.spin_altitude)
        form_hillshade.addRow("Sun Altitude (Elevation Angle):", alt_row)

        z_row = QHBoxLayout()
        self.spin_z_factor = QDoubleSpinBox()
        self.spin_z_factor.setRange(0.0001, 100.0)
        self.spin_z_factor.setValue(1.0)
        self.spin_z_factor.setDecimals(4)
        z_row.addWidget(self.spin_z_factor)
        form_hillshade.addRow("Vertical Exaggeration (Z Factor):", z_row)

        self.chk_multidir = QCheckBox("Multi-Directional Hillshade (ArcGIS-style realistic multi-illumination)")
        self.chk_multidir.setChecked(True)
        form_hillshade.addRow("", self.chk_multidir)

        layout_hillshade.addLayout(form_hillshade)
        self.tabs.addTab(tab_hillshade, "💡 3D Hillshade Relief")

        # Tab 3: Grayscale Contrast Stretch
        tab_gray = QWidget()
        layout_gray = QVBoxLayout(tab_gray)
        form_gray = QFormLayout()

        self.gray_mode_combo = QComboBox()
        self.gray_mode_combo.addItem("Cumulative Cut (2% – 98%) [Recommended]", "cumulative_cut")
        self.gray_mode_combo.addItem("Exact Min to Max (Full range)", "min_max")
        form_gray.addRow("Contrast Algorithm:", self.gray_mode_combo)

        layout_gray.addLayout(form_gray)
        self.tabs.addTab(tab_gray, "🌓 High-Contrast Grayscale")

        main_layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("⚡ Apply Now")
        btn_apply.clicked.connect(self.apply_style)

        btn_ok = QPushButton("✓ OK")
        btn_ok.clicked.connect(self._on_ok)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

    def _populate_layers(self):
        self.layer_combo.clear()
        layers = [l for l in QgsProject.instance().mapLayers().values() if l.type() == QgsMapLayer.RasterLayer]
        if not layers:
            self.layer_combo.addItem("-- No Raster Layers in Project --", None)
            return

        for l in layers:
            is_dem = ElevationStyler.is_dem_or_elevation(l)
            prefix = "🏔 [DEM] " if is_dem else "🗺 "
            self.layer_combo.addItem(f"{prefix}{l.name()}", l.id())

    def _get_current_layer(self):
        layer_id = self.layer_combo.currentData()
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def _on_layer_changed(self):
        layer = self._get_current_layer()
        if not layer:
            self.stats_label.setText("Min: -- | Max: -- | Mean: -- | NoData: --")
            return

        stats = ElevationStyler.get_valid_elevation_stats(layer, 1)
        if stats:
            nodata_str = f"{stats['nodata_val']}" if stats['has_nodata'] else "None"
            self.stats_label.setText(
                f"Min: {stats['min']:.1f} m | Max: {stats['max']:.1f} m | "
                f"Mean: {stats['mean']:.1f} m | StdDev: {stats['std_dev']:.1f} | NoData: {nodata_str}"
            )
            self.spin_min_val.setValue(stats["p2"])
            self.spin_max_val.setValue(stats["p98"])

    def _on_preset_changed(self):
        preset_key = self.preset_combo.currentData()
        self.ramp_preview.set_preset(preset_key, self.chk_invert.isChecked())

    def _reset_to_cut(self):
        layer = self._get_current_layer()
        if layer:
            stats = ElevationStyler.get_valid_elevation_stats(layer, 1)
            if stats:
                self.spin_min_val.setValue(stats["p2"])
                self.spin_max_val.setValue(stats["p98"])

    def _reset_to_full(self):
        layer = self._get_current_layer()
        if layer:
            stats = ElevationStyler.get_valid_elevation_stats(layer, 1)
            if stats:
                self.spin_min_val.setValue(stats["min"])
                self.spin_max_val.setValue(stats["max"])

    def apply_style(self):
        layer = self._get_current_layer()
        if not layer:
            QMessageBox.warning(self, "No Layer", "Please select a raster layer.")
            return

        curr_tab = self.tabs.currentIndex()
        if curr_tab == 0:
            preset_key = self.preset_combo.currentData()
            min_val = self.spin_min_val.value()
            max_val = self.spin_max_val.value()
            invert = self.chk_invert.isChecked()
            bilinear = self.chk_bilinear.isChecked()
            use_draped = self.chk_draped_relief.isChecked()

            if use_draped:
                success = ElevationStyler.apply_draped_relief(
                    layer, preset_key=preset_key, band=1, z_factor=1.5, multidirectional=True
                )
            else:
                success = ElevationStyler.apply_elevation_colormap(
                    layer, preset_key=preset_key, band=1, min_val=min_val, max_val=max_val, invert=invert, enable_bilinear=bilinear
                )
        elif curr_tab == 1:
            success = ElevationStyler.apply_hillshade(
                layer, band=1, z_factor=self.spin_z_factor.value(), azimuth=self.spin_azimuth.value(),
                altitude=self.spin_altitude.value(), multidirectional=self.chk_multidir.isChecked()
            )
        else:
            success = ElevationStyler.apply_grayscale_contrast(
                layer, band=1, stretch_type=self.gray_mode_combo.currentData()
            )

        target_l = success if (success and hasattr(success, "isValid")) else layer
        if success and self.map_canvas:
            if hasattr(self.map_canvas, 'update_elevation_legend'):
                self.map_canvas.update_elevation_legend(target_l)
            self.map_canvas.refresh_canvas()

        # Apply blend mode (always — independent of which tab was used)
        blend_mode_key = self.blend_combo.currentData() if hasattr(self, "blend_combo") else "Normal"
        if blend_mode_key and blend_mode_key != "Normal":
            apply_target = target_l if (success and hasattr(success, "isValid")) else layer
            ElevationStyler.apply_blend_mode(apply_target, blend_mode_key)
            if self.map_canvas:
                self.map_canvas.refresh_canvas()

    def _on_ok(self):
        self.apply_style()
        self.accept()


# Backward compatibility alias
DemElevationDialog = DEMElevationDialog
