# -*- coding: utf-8 -*-
"""
GeoStudio - Universal Algorithm Parameter Form Builders
Builds UI form fields dynamically based on dialog_type (terrain, hydro, contours, landsat, earthworks, etc.).
"""

import os
import sys

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QFileDialog
)


def build_parameters_form(dialog):
    """Construct parameter inputs dynamically on dialog.form_layout based on algorithm type."""
    dtype = dialog.algo.dialog_type

    # ── 1. Landsat Specialized Dialogs ──
    if dtype == "landsat_mtl":
        mtl_row = QHBoxLayout()
        dialog.mtl_path_edit = QLineEdit()
        dialog.mtl_path_edit.setPlaceholderText("Select Landsat *_MTL.txt metadata file...")
        btn_mtl = QPushButton("Browse...")
        btn_mtl.setMinimumWidth(85)
        btn_mtl.clicked.connect(dialog._browse_mtl_file)
        mtl_row.addWidget(dialog.mtl_path_edit)
        mtl_row.addWidget(btn_mtl)
        dialog.form_layout.addRow("MTL Metadata File:", mtl_row)

        dialog.calib_mode_combo = QComboBox()
        dialog.calib_mode_combo.addItems([
            "Top of Atmosphere (TOA) Reflectance + Sun Elevation Correction",
            "Top of Atmosphere (TOA) Spectral Radiance",
            "Digital Number (DN) Calibrated Output"
        ])
        dialog.form_layout.addRow("Calibration Mode:", dialog.calib_mode_combo)

        dialog.sensor_detect_lbl = QLabel("Auto-detected Sensor: <i>(Select MTL file to detect)</i>")
        dialog.sensor_detect_lbl.setStyleSheet("color: #0284c7; font-weight: 500;")
        dialog.form_layout.addRow("Sensor:", dialog.sensor_detect_lbl)

    elif dtype == "landsat_lst":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Landsat Scene / Thermal Band:", dialog.raster_combo)

        dialog.lst_method_combo = QComboBox()
        dialog.lst_method_combo.addItems([
            "Single-Channel Split-Window (Band 10/11) with FVC Emissivity",
            "Mono-Window Algorithm (Landsat 4/5/7 Band 6)",
            "Direct Brightness Temperature Conversion"
        ])
        dialog.form_layout.addRow("Retrieval Method:", dialog.lst_method_combo)

        dialog.temp_unit_combo = QComboBox()
        dialog.temp_unit_combo.addItems(["Celsius (°C)", "Kelvin (K)", "Fahrenheit (°F)"])
        dialog.form_layout.addRow("Temperature Unit:", dialog.temp_unit_combo)

    elif dtype == "landsat_generic":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input Landsat Layer:", dialog.raster_combo)

    # ── 2. Terrain & Earthworks (Global Mapper) ──
    elif dtype == "terrain_profile":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input DEM Raster:", dialog.raster_combo)

        dialog.sample_step_spin = QDoubleSpinBox()
        dialog.sample_step_spin.setRange(1.0, 1000.0)
        dialog.sample_step_spin.setValue(10.0)
        dialog.sample_step_spin.setSuffix(" m")
        dialog.form_layout.addRow("Sampling Interval:", dialog.sample_step_spin)

    elif dtype == "terrain_cutfill":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Base / Before DEM:", dialog.raster_combo)

        dialog.compare_mode_combo = QComboBox()
        dialog.compare_mode_combo.addItems([
            "Compare Against Fixed Elevation Datum Plane",
            "Compare Against Second DEM Surface"
        ])
        dialog.form_layout.addRow("Calculation Mode:", dialog.compare_mode_combo)

        dialog.datum_height_spin = QDoubleSpinBox()
        dialog.datum_height_spin.setRange(-500.0, 9000.0)
        dialog.datum_height_spin.setValue(100.0)
        dialog.datum_height_spin.setSuffix(" m")
        dialog.form_layout.addRow("Datum Elevation (Plane):", dialog.datum_height_spin)

        dialog.compare_dem_combo = QComboBox()
        dialog.form_layout.addRow("Comparison / After DEM:", dialog.compare_dem_combo)
        dialog.compare_dem_combo.setEnabled(False)

        dialog.compare_mode_combo.currentIndexChanged.connect(
            lambda idx: (
                dialog.datum_height_spin.setEnabled(idx == 0),
                dialog.compare_dem_combo.setEnabled(idx == 1)
            )
        )

    elif dtype == "terrain_flood":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input Elevation DEM:", dialog.raster_combo)

        dialog.water_level_spin = QDoubleSpinBox()
        dialog.water_level_spin.setRange(-500.0, 9000.0)
        dialog.water_level_spin.setValue(50.0)
        dialog.water_level_spin.setSuffix(" m")
        dialog.form_layout.addRow("Target Water Level:", dialog.water_level_spin)

    elif dtype == "raster_viewshed":
        dialog.raster_combo = QComboBox()
        dialog.raster_combo.currentIndexChanged.connect(dialog._set_observer_to_dem_center)
        dialog.form_layout.addRow("Input DEM Raster:", dialog.raster_combo)

        obs_coord_row = QHBoxLayout()
        dialog.observer_x_spin = QDoubleSpinBox()
        dialog.observer_x_spin.setRange(-20000000.0, 20000000.0)
        dialog.observer_x_spin.setDecimals(4)
        dialog.observer_y_spin = QDoubleSpinBox()
        dialog.observer_y_spin.setRange(-20000000.0, 20000000.0)
        dialog.observer_y_spin.setDecimals(4)
        obs_coord_row.addWidget(QLabel("X:"))
        obs_coord_row.addWidget(dialog.observer_x_spin)
        obs_coord_row.addWidget(QLabel("Y:"))
        obs_coord_row.addWidget(dialog.observer_y_spin)
        dialog.form_layout.addRow("Observer Position:", obs_coord_row)

        btn_set_center = QPushButton("🎯 Set Observer to Center of DEM")
        btn_set_center.setStyleSheet("background: #e2e8f0; color: #0f172a; font-weight: normal; padding: 2px 6px; font-size: 11px;")
        btn_set_center.clicked.connect(dialog._set_observer_to_dem_center)
        dialog.form_layout.addRow("", btn_set_center)

        dialog.observer_h_spin = QDoubleSpinBox()
        dialog.observer_h_spin.setRange(0.0, 500.0)
        dialog.observer_h_spin.setValue(1.8)
        dialog.observer_h_spin.setSuffix(" m")
        dialog.form_layout.addRow("Observer Height (Above Ground):", dialog.observer_h_spin)

        dialog.target_h_spin = QDoubleSpinBox()
        dialog.target_h_spin.setRange(0.0, 500.0)
        dialog.target_h_spin.setValue(0.0)
        dialog.target_h_spin.setSuffix(" m")
        dialog.form_layout.addRow("Target Object Height:", dialog.target_h_spin)

        dialog.max_dist_spin = QDoubleSpinBox()
        dialog.max_dist_spin.setRange(0.0, 1000000.0)
        dialog.max_dist_spin.setValue(5000.0)
        dialog.max_dist_spin.setSuffix(" m")
        dialog.max_dist_spin.setToolTip("Set to 0 for unlimited / full DEM extent")
        dialog.form_layout.addRow("Max Visibility Radius:", dialog.max_dist_spin)

    elif dtype == "terrain_georef":
        img_row = QHBoxLayout()
        dialog.raw_img_edit = QLineEdit()
        dialog.raw_img_edit.setPlaceholderText("Select unreferenced image/map...")
        btn_raw = QPushButton("Browse...")
        btn_raw.setMinimumWidth(85)
        btn_raw.clicked.connect(dialog._browse_raw_img)
        img_row.addWidget(dialog.raw_img_edit)
        img_row.addWidget(btn_raw)
        dialog.form_layout.addRow("Input Image:", img_row)

        dialog.transform_combo = QComboBox()
        dialog.transform_combo.addItems(["Thin Plate Spline (TPS - Local rubber-sheeting)", "Polynomial 2nd Order (Quadratic)", "Affine (1st Order - Rotation/Scale/Shift)"])
        dialog.form_layout.addRow("Transformation Method:", dialog.transform_combo)

    # ── 3. Spatial Interpolation (ArcGIS) ──
    elif dtype == "spatial_interp":
        dialog.vector_combo = QComboBox()
        dialog.form_layout.addRow("Sample Points Layer:", dialog.vector_combo)

        dialog.power_spin = QDoubleSpinBox()
        dialog.power_spin.setRange(0.5, 10.0)
        dialog.power_spin.setValue(2.0)
        dialog.form_layout.addRow("Power / Variogram Weight:", dialog.power_spin)

    # ── 4. Raster Terrain & Surface Analysis ──
    elif dtype == "raster_terrain":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input Elevation DEM:", dialog.raster_combo)

        dialog.z_factor_spin = QDoubleSpinBox()
        dialog.z_factor_spin.setRange(0.0001, 1000.0)
        dialog.z_factor_spin.setValue(1.0)
        dialog.z_factor_spin.setDecimals(4)
        dialog.z_factor_spin.setToolTip("Vertical exaggeration factor (Z scale)")
        dialog.form_layout.addRow("Z Factor (Vertical Scale):", dialog.z_factor_spin)

    # ── 5. Hydrological Modeling Suite ──
    elif dtype == "raster_hydro":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input Elevation DEM:", dialog.raster_combo)

        if dialog.algo.algo_id in ("hydrology:stream_network", "hydrology:watershed"):
            thresh_row = QHBoxLayout()
            dialog.thresh_type_combo = QComboBox()
            dialog.thresh_type_combo.addItems([
                "Detailed (Minor streams & gullies - 500 cells)",
                "Standard (Medium rivers & tributaries - 2,000 cells)",
                "Major Catchments (Principal rivers - 10,000 cells)",
                "Custom Minimum Upslope Threshold"
            ])
            dialog.thresh_type_combo.setCurrentIndex(1)
            thresh_row.addWidget(dialog.thresh_type_combo)

            dialog.stream_thresh_spin = QSpinBox()
            dialog.stream_thresh_spin.setRange(10, 10000000)
            dialog.stream_thresh_spin.setValue(2000)
            dialog.stream_thresh_spin.setSuffix(" cells")
            dialog.stream_thresh_spin.setEnabled(False)
            thresh_row.addWidget(dialog.stream_thresh_spin)

            def _on_thresh_preset_changed(idx):
                dialog.stream_thresh_spin.setEnabled(idx == 3)
                if idx == 0:
                    dialog.stream_thresh_spin.setValue(500)
                elif idx == 1:
                    dialog.stream_thresh_spin.setValue(2000)
                elif idx == 2:
                    dialog.stream_thresh_spin.setValue(10000)

            dialog.thresh_type_combo.currentIndexChanged.connect(_on_thresh_preset_changed)
            dialog.form_layout.addRow("Stream Accumulation Threshold:", thresh_row)

        if dialog.algo.algo_id != "hydrology:fillsinks":
            dialog.cb_autofill = QCheckBox("Automatically fill depressions and sinks before routing (Barnes Priority-Flood)")
            dialog.cb_autofill.setChecked(True)
            dialog.form_layout.addRow("", dialog.cb_autofill)

    # ── 6. Contours & Isolines ──
    elif dtype == "raster_contours":
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input Elevation DEM:", dialog.raster_combo)

        interval_row = QHBoxLayout()
        dialog.interval_preset_combo = QComboBox()
        dialog.interval_preset_combo.addItems([
            "1 meter (Ultra-detailed)",
            "5 meters (Detailed topographic)",
            "10 meters (Standard topographic)",
            "20 meters (Medium terrain)",
            "50 meters (Mountainous terrain)",
            "100 meters (Regional elevation)",
            "Custom Contour Interval..."
        ])
        dialog.interval_preset_combo.setCurrentIndex(3)
        interval_row.addWidget(dialog.interval_preset_combo)

        dialog.interval_spin = QDoubleSpinBox()
        dialog.interval_spin.setRange(0.1, 10000.0)
        dialog.interval_spin.setValue(20.0)
        dialog.interval_spin.setSuffix(" m")
        dialog.interval_spin.setEnabled(False)
        interval_row.addWidget(dialog.interval_spin)

        def _on_contour_preset(idx):
            dialog.interval_spin.setEnabled(idx == 6)
            vals = [1.0, 5.0, 10.0, 20.0, 50.0, 100.0]
            if idx < len(vals):
                dialog.interval_spin.setValue(vals[idx])

        dialog.interval_preset_combo.currentIndexChanged.connect(_on_contour_preset)
        dialog.form_layout.addRow("Contour Interval:", interval_row)

        dialog.base_spin = QDoubleSpinBox()
        dialog.base_spin.setRange(-10000.0, 10000.0)
        dialog.base_spin.setValue(0.0)
        dialog.base_spin.setSuffix(" m")
        dialog.form_layout.addRow("Base Contour Elevation:", dialog.base_spin)

    # ── 7. Vector Dialogs ──
    elif dtype == "vector_buffer":
        dialog.vector_combo = QComboBox()
        dialog.form_layout.addRow("Input Layer:", dialog.vector_combo)

        dialog.dist_spin = QDoubleSpinBox()
        dialog.dist_spin.setRange(0.01, 1000000.0)
        dialog.dist_spin.setValue(10.0)
        dialog.dist_spin.setSuffix(" m")
        dialog.form_layout.addRow("Distance:", dialog.dist_spin)

        dialog.seg_spin = QSpinBox()
        dialog.seg_spin.setRange(1, 100)
        dialog.seg_spin.setValue(5)
        dialog.form_layout.addRow("Segments:", dialog.seg_spin)

    # ── 8. Forestry & Tree Metrics Suite ──
    elif dtype == "forestry_detect":
        from PyQt5.QtWidgets import QFileDialog

        input_row = QHBoxLayout()
        dialog.raster_combo = QComboBox()
        btn_input_browse = QPushButton("Browse...")
        btn_input_browse.setMinimumWidth(85)

        def _browse_input_cloud_or_chm():
            filt = "Point Cloud / CHM (*.laz *.las *.copc.laz *.tif);;LiDAR Point Cloud (*.laz *.las *.copc.laz);;Canopy Height Raster (*.tif);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Point Cloud or CHM File", "", filt)
            if path:
                dialog.raster_combo.insertItem(0, f"📁 {os.path.basename(path)}", path)
                dialog.raster_combo.setCurrentIndex(0)

        btn_input_browse.clicked.connect(_browse_input_cloud_or_chm)
        input_row.addWidget(dialog.raster_combo, 1)
        input_row.addWidget(btn_input_browse)
        dialog.form_layout.addRow("Input Point Cloud / CHM:", input_row)

        dialog.min_tree_height_spin = QDoubleSpinBox()
        dialog.min_tree_height_spin.setRange(0.5, 120.0)
        dialog.min_tree_height_spin.setValue(2.0)
        dialog.min_tree_height_spin.setSuffix(" m")
        dialog.min_tree_height_spin.setToolTip("Minimum height threshold to eliminate brush, grass, and ground clutter")
        dialog.form_layout.addRow("Minimum Tree Height:", dialog.min_tree_height_spin)

        dialog.search_mode_combo = QComboBox()
        dialog.search_mode_combo.addItems([
            "🌲 Adaptive Variable Window (VWF - Mixed Stand)",
            "🌲 Adaptive Variable Window (VWF - Conifer)",
            "🌳 Adaptive Variable Window (VWF - Deciduous / Broadleaf)",
            "✏️ Custom Calibrated Allometry (a · H + b)",
            "⚙ Standard Fixed Window (5×5 LMF)",
            "⚙ Detailed Fixed Window (3×3 LMF - Dense Stand)",
            "⚙ Large Fixed Window (7×7 LMF - Mature Canopy)"
        ])
        dialog.search_mode_combo.setCurrentIndex(0)
        dialog.search_mode_combo.setToolTip("Variable Window Filter (VWF) dynamically scales crown search window based on height allometry.")
        dialog.form_layout.addRow("Apex Search Model:", dialog.search_mode_combo)

        # Custom VWF row
        vwf_custom_row = QHBoxLayout()
        dialog.vwf_a_spin = QDoubleSpinBox()
        dialog.vwf_a_spin.setRange(0.01, 3.0)
        dialog.vwf_a_spin.setValue(0.28)
        dialog.vwf_a_spin.setSingleStep(0.02)
        dialog.vwf_a_spin.setDecimals(3)

        dialog.vwf_b_spin = QDoubleSpinBox()
        dialog.vwf_b_spin.setRange(0.0, 20.0)
        dialog.vwf_b_spin.setValue(1.5)
        dialog.vwf_b_spin.setSingleStep(0.1)
        dialog.vwf_b_spin.setSuffix(" m")

        dialog.vwf_min_win_spin = QSpinBox()
        dialog.vwf_min_win_spin.setRange(3, 31)
        dialog.vwf_min_win_spin.setSingleStep(2)
        dialog.vwf_min_win_spin.setValue(3)
        dialog.vwf_min_win_spin.setSuffix(" px")

        dialog.vwf_max_win_spin = QSpinBox()
        dialog.vwf_max_win_spin.setRange(5, 51)
        dialog.vwf_max_win_spin.setSingleStep(2)
        dialog.vwf_max_win_spin.setValue(15)
        dialog.vwf_max_win_spin.setSuffix(" px")

        vwf_custom_row.addWidget(QLabel("a (Slope):"))
        vwf_custom_row.addWidget(dialog.vwf_a_spin)
        vwf_custom_row.addWidget(QLabel("b (Offset):"))
        vwf_custom_row.addWidget(dialog.vwf_b_spin)
        vwf_custom_row.addWidget(QLabel("Min:"))
        vwf_custom_row.addWidget(dialog.vwf_min_win_spin)
        vwf_custom_row.addWidget(QLabel("Max:"))
        vwf_custom_row.addWidget(dialog.vwf_max_win_spin)

        dialog.vwf_custom_widget = QWidget()
        dialog.vwf_custom_widget.setLayout(vwf_custom_row)
        dialog.vwf_custom_widget.setVisible(False)
        dialog.vwf_custom_label = QLabel("Custom VWF Parameters:")
        dialog.vwf_custom_label.setVisible(False)
        dialog.form_layout.addRow(dialog.vwf_custom_label, dialog.vwf_custom_widget)

        def _on_search_mode_changed(idx):
            is_custom = (idx == 3)
            dialog.vwf_custom_widget.setVisible(is_custom)
            dialog.vwf_custom_label.setVisible(is_custom)

        dialog.search_mode_combo.currentIndexChanged.connect(_on_search_mode_changed)

        dialog.smoothing_spin = QDoubleSpinBox()
        dialog.smoothing_spin.setRange(0.0, 5.0)
        dialog.smoothing_spin.setValue(0.8)
        dialog.smoothing_spin.setSingleStep(0.1)
        dialog.smoothing_spin.setSuffix(" σ")
        dialog.smoothing_spin.setToolTip("Gaussian smoothing kernel to suppress noise on individual leaves")
        dialog.form_layout.addRow("Canopy Smoothing Sigma:", dialog.smoothing_spin)

        dialog.min_prominence_spin = QDoubleSpinBox()
        dialog.min_prominence_spin.setRange(0.05, 15.0)
        dialog.min_prominence_spin.setValue(0.35)
        dialog.min_prominence_spin.setSingleStep(0.05)
        dialog.min_prominence_spin.setSuffix(" m")
        dialog.min_prominence_spin.setToolTip("Minimum absolute topological elevation drop from tree apex to crown saddle col")
        dialog.form_layout.addRow("Crown Saddle Prominence (P_min):", dialog.min_prominence_spin)

        dialog.alpha_prominence_spin = QDoubleSpinBox()
        dialog.alpha_prominence_spin.setRange(0.0, 0.50)
        dialog.alpha_prominence_spin.setValue(0.10)
        dialog.alpha_prominence_spin.setSingleStep(0.02)
        dialog.alpha_prominence_spin.setMinimumWidth(140)
        dialog.alpha_prominence_spin.setSuffix(" · H_apex")
        dialog.alpha_prominence_spin.setToolTip("Relative prominence factor (alpha): Criterion is P >= max(P_min, alpha * H_apex)")
        dialog.form_layout.addRow("Relative Prominence (α):", dialog.alpha_prominence_spin)

        dialog.ground_coverage_spin = QDoubleSpinBox()
        dialog.ground_coverage_spin.setRange(5.0, 50.0)
        dialog.ground_coverage_spin.setValue(15.0)
        dialog.ground_coverage_spin.setSingleStep(1.0)
        dialog.ground_coverage_spin.setSuffix(" %")
        dialog.ground_coverage_spin.setToolTip("Ground Coverage Threshold: Minimum occupied coarse ground cells required to trust ASPRS Class 2 before falling back to morphological filtering")
        dialog.form_layout.addRow("Ground Coverage Threshold:", dialog.ground_coverage_spin)

        dialog.cb_delineate_crowns = QCheckBox("Delineate Individual Crown Polygons (Marker-Controlled Watershed)")
        dialog.cb_delineate_crowns.setChecked(True)
        dialog.form_layout.addRow(dialog.cb_delineate_crowns)

        dialog.cb_generate_png = QCheckBox("Generate High-Resolution Labeled Summary PNG Map")
        dialog.cb_generate_png.setChecked(True)
        dialog.form_layout.addRow(dialog.cb_generate_png)

        png_row = QHBoxLayout()
        dialog.png_path_edit = QLineEdit()
        dialog.png_path_edit.setPlaceholderText("[Auto-generate alongside vector output]")
        btn_png = QPushButton("Browse...")
        btn_png.setMinimumWidth(85)

        def _browse_png():
            path, _ = QFileDialog.getSaveFileName(dialog, "Save Summary PNG Map", "", "PNG Image (*.png);;All Files (*.*)")
            if path:
                dialog.png_path_edit.setText(path)

        btn_png.clicked.connect(_browse_png)
        png_row.addWidget(dialog.png_path_edit)
        png_row.addWidget(btn_png)
        dialog.form_layout.addRow("Output PNG Path:", png_row)

        dialog.label_style_combo = QComboBox()
        dialog.label_style_combo.addItems([
            "Tree Number Only (#1, #2...) [Decluttered, No Overlap]",
            "Clean Points Only (Total Count in Card, No Text Overlap)",
            "Number + Height (#1 - 24.6m) [Small Plots Only]"
        ])
        dialog.label_style_combo.setCurrentIndex(0)
        dialog.form_layout.addRow("Map Tree Label Style:", dialog.label_style_combo)

    elif dtype == "forestry_heights":
        from PyQt5.QtWidgets import QFileDialog

        dialog.vector_combo = QComboBox()
        dialog.form_layout.addRow("Input Detected Trees Layer:", dialog.vector_combo)

        chm_row = QHBoxLayout()
        dialog.raster_combo = QComboBox()
        btn_h_browse = QPushButton("Browse...")
        btn_h_browse.setMinimumWidth(85)

        def _browse_h_cloud_or_chm():
            filt = "Point Cloud / CHM (*.laz *.las *.copc.laz *.tif);;LiDAR Point Cloud (*.laz *.las *.copc.laz);;Canopy Height Raster (*.tif);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Point Cloud or CHM File", "", filt)
            if path:
                dialog.raster_combo.insertItem(0, f"📁 {os.path.basename(path)}", path)
                dialog.raster_combo.setCurrentIndex(0)

        btn_h_browse.clicked.connect(_browse_h_cloud_or_chm)
        chm_row.addWidget(dialog.raster_combo, 1)
        chm_row.addWidget(btn_h_browse)
        dialog.form_layout.addRow("Input Point Cloud / CHM:", chm_row)

        dialog.height_radius_spin = QDoubleSpinBox()
        dialog.height_radius_spin.setRange(0.0, 20.0)
        dialog.height_radius_spin.setValue(1.0)
        dialog.height_radius_spin.setSuffix(" m")
        dialog.height_radius_spin.setToolTip("Apex search neighborhood radius around each tree coordinate")
        dialog.form_layout.addRow("Neighborhood Search Radius:", dialog.height_radius_spin)

    elif dtype == "forestry_crown":
        from PyQt5.QtWidgets import QFileDialog

        dialog.vector_combo = QComboBox()
        dialog.form_layout.addRow("Input Detected Trees Layer:", dialog.vector_combo)

        crown_chm_row = QHBoxLayout()
        dialog.raster_combo = QComboBox()
        btn_c_browse = QPushButton("Browse...")
        btn_c_browse.setMinimumWidth(85)

        def _browse_c_cloud_or_chm():
            filt = "Point Cloud / CHM (*.laz *.las *.copc.laz *.tif);;LiDAR Point Cloud (*.laz *.las *.copc.laz);;Canopy Height Raster (*.tif);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Point Cloud or CHM File", "", filt)
            if path:
                dialog.raster_combo.insertItem(0, f"📁 {os.path.basename(path)}", path)
                dialog.raster_combo.setCurrentIndex(0)

        btn_c_browse.clicked.connect(_browse_c_cloud_or_chm)
        crown_chm_row.addWidget(dialog.raster_combo, 1)
        crown_chm_row.addWidget(btn_c_browse)
        dialog.form_layout.addRow("Input Point Cloud / CHM:", crown_chm_row)


        dialog.max_crown_radius_spin = QDoubleSpinBox()
        dialog.max_crown_radius_spin.setRange(1.0, 50.0)
        dialog.max_crown_radius_spin.setValue(12.0)
        dialog.max_crown_radius_spin.setSuffix(" m")
        dialog.max_crown_radius_spin.setToolTip("Maximum allowable radius when delineating crown boundary")
        dialog.form_layout.addRow("Max Crown Radius Cutoff:", dialog.max_crown_radius_spin)

        dialog.crown_base_spin = QDoubleSpinBox()
        dialog.crown_base_spin.setRange(10.0, 80.0)
        dialog.crown_base_spin.setValue(35.0)
        dialog.crown_base_spin.setSuffix(" %")
        dialog.crown_base_spin.setToolTip("Percentage of apex height where crown boundary stops expanding downward")
        dialog.form_layout.addRow("Crown Base Ratio Cutoff:", dialog.crown_base_spin)

    elif dtype == "forestry_dbh":
        dialog.vector_combo = QComboBox()
        dialog.form_layout.addRow("Input Trees Layer (with Height / Crown):", dialog.vector_combo)

        dialog.dbh_preset_combo = QComboBox()
        dialog.dbh_preset_combo.addItems([
            "Temperate Coniferous (Pine, Spruce, Fir)",
            "Temperate Deciduous (Oak, Maple, Hardwood)",
            "Tropical Broadleaf (Rainforest)",
            "Eucalyptus / Fast-Growing Plantation",
            "Custom Allometric Equation"
        ])
        dialog.dbh_preset_combo.setCurrentIndex(0)
        dialog.form_layout.addRow("Forest Allometry Model:", dialog.dbh_preset_combo)

        custom_row = QHBoxLayout()
        dialog.custom_a_spin = QDoubleSpinBox()
        dialog.custom_a_spin.setRange(-10.0, 10.0)
        dialog.custom_a_spin.setValue(0.85)
        dialog.custom_a_spin.setSingleStep(0.05)

        dialog.custom_b_spin = QDoubleSpinBox()
        dialog.custom_b_spin.setRange(-10.0, 10.0)
        dialog.custom_b_spin.setValue(0.72)
        dialog.custom_b_spin.setSingleStep(0.05)

        dialog.custom_c_spin = QDoubleSpinBox()
        dialog.custom_c_spin.setRange(-10.0, 10.0)
        dialog.custom_c_spin.setValue(0.38)
        dialog.custom_c_spin.setSingleStep(0.05)

        custom_row.addWidget(QLabel("a:"))
        custom_row.addWidget(dialog.custom_a_spin)
        custom_row.addWidget(QLabel("b (Height):"))
        custom_row.addWidget(dialog.custom_b_spin)
        custom_row.addWidget(QLabel("c (Crown):"))
        custom_row.addWidget(dialog.custom_c_spin)
        dialog.form_layout.addRow("Custom Coeffs ln(DBH)=a+b·ln(H)+c·ln(CD):", custom_row)

        dialog.custom_a_spin.setEnabled(False)
        dialog.custom_b_spin.setEnabled(False)
        dialog.custom_c_spin.setEnabled(False)

        def _on_dbh_preset_changed(idx):
            is_custom = (idx == 4)
            dialog.custom_a_spin.setEnabled(is_custom)
            dialog.custom_b_spin.setEnabled(is_custom)
            dialog.custom_c_spin.setEnabled(is_custom)

        dialog.dbh_preset_combo.currentIndexChanged.connect(_on_dbh_preset_changed)

        dialog.wood_density_spin = QDoubleSpinBox()
        dialog.wood_density_spin.setRange(0.1, 1.5)
        dialog.wood_density_spin.setValue(0.55)
        dialog.wood_density_spin.setSingleStep(0.05)
        dialog.wood_density_spin.setSuffix(" g/cm³")
        dialog.wood_density_spin.setToolTip("Wood density used for individual tree biomass estimation (Chave model)")
        dialog.form_layout.addRow("Wood Specific Gravity (Density):", dialog.wood_density_spin)

    elif dtype == "forestry_validate":
        from PyQt5.QtWidgets import QFileDialog

        # Detected trees input
        det_row = QHBoxLayout()
        dialog.detected_combo = QComboBox()
        btn_det_browse = QPushButton("Browse...")
        btn_det_browse.setMinimumWidth(85)

        def _browse_det_vec():
            filt = "Vector Layer (*.gpkg *.shp *.geojson);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Detected Trees Layer", "", filt)
            if path:
                dialog.detected_combo.insertItem(0, f"🌲 {os.path.basename(path)}", path)
                dialog.detected_combo.setCurrentIndex(0)

        btn_det_browse.clicked.connect(_browse_det_vec)
        det_row.addWidget(dialog.detected_combo, 1)
        det_row.addWidget(btn_det_browse)
        dialog.form_layout.addRow("Detected Trees Layer:", det_row)

        # Reference ground truth input
        ref_row = QHBoxLayout()
        dialog.reference_combo = QComboBox()
        btn_ref_browse = QPushButton("Browse...")
        btn_ref_browse.setMinimumWidth(85)

        def _browse_ref_vec():
            filt = "Reference Vector Layer (*.gpkg *.shp *.geojson);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Ground Truth Reference Trees", "", filt)
            if path:
                dialog.reference_combo.insertItem(0, f"🎯 {os.path.basename(path)}", path)
                dialog.reference_combo.setCurrentIndex(0)

        btn_ref_browse.clicked.connect(_browse_ref_vec)
        ref_row.addWidget(dialog.reference_combo, 1)
        ref_row.addWidget(btn_ref_browse)
        dialog.form_layout.addRow("Ground Truth Reference:", ref_row)

        dialog.match_dist_spin = QDoubleSpinBox()
        dialog.match_dist_spin.setRange(0.2, 20.0)
        dialog.match_dist_spin.setValue(2.0)
        dialog.match_dist_spin.setSingleStep(0.2)
        dialog.match_dist_spin.setSuffix(" m")
        dialog.match_dist_spin.setToolTip("Maximum spatial offset distance to consider a detected tree as matching a reference tree")
        dialog.form_layout.addRow("Spatial Match Tolerance:", dialog.match_dist_spin)

        dialog.h_tol_spin = QDoubleSpinBox()
        dialog.h_tol_spin.setRange(5.0, 100.0)
        dialog.h_tol_spin.setValue(30.0)
        dialog.h_tol_spin.setSingleStep(5.0)
        dialog.h_tol_spin.setSuffix(" %")
        dialog.h_tol_spin.setToolTip("Maximum allowed percentage height discrepancy between matched trees (if reference contains height attributes)")
        dialog.form_layout.addRow("Height Error Tolerance:", dialog.h_tol_spin)

    elif dtype == "forestry_report":
        from PyQt5.QtWidgets import QFileDialog

        # Tree inventory layer
        t_row = QHBoxLayout()
        dialog.trees_combo = QComboBox()
        btn_t_browse = QPushButton("Browse...")
        btn_t_browse.setMinimumWidth(85)

        def _browse_trees_vec():
            filt = "Vector Layer (*.gpkg *.shp *.geojson);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Tree Inventory Layer", "", filt)
            if path:
                dialog.trees_combo.insertItem(0, f"🌲 {os.path.basename(path)}", path)
                dialog.trees_combo.setCurrentIndex(0)

        btn_t_browse.clicked.connect(_browse_trees_vec)
        t_row.addWidget(dialog.trees_combo, 1)
        t_row.addWidget(btn_t_browse)
        dialog.form_layout.addRow("Tree Inventory Layer:", t_row)

        # Optional validation results layer
        v_row = QHBoxLayout()
        dialog.validation_combo = QComboBox()
        dialog.validation_combo.addItem("[None - No validation benchmark]", None)
        btn_v_browse = QPushButton("Browse...")
        btn_v_browse.setMinimumWidth(85)

        def _browse_val_vec():
            filt = "Validation Vector Layer (*.gpkg *.shp *.geojson);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Validation Benchmark Layer", "", filt)
            if path:
                dialog.validation_combo.insertItem(0, f"🎯 {os.path.basename(path)}", path)
                dialog.validation_combo.setCurrentIndex(0)

        btn_v_browse.clicked.connect(_browse_val_vec)
        v_row.addWidget(dialog.validation_combo, 1)
        v_row.addWidget(btn_v_browse)
        dialog.form_layout.addRow("Validation Benchmark (Optional):", v_row)

        dialog.cb_export_json = QCheckBox("Export GeoStudio_ITD_Report.json alongside output")
        dialog.cb_export_json.setChecked(True)
        dialog.form_layout.addRow("", dialog.cb_export_json)

    elif dtype == "forestry_carbon":
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QFileDialog

        dialog.carbon_input_type_group = QButtonGroup(dialog)
        dialog.rb_carbon_chm = QRadioButton("Canopy Height Model (CHM Raster)")
        dialog.rb_carbon_vec = QRadioButton("Detected Trees / Inventory Vector")
        dialog.rb_carbon_chm.setChecked(True)
        dialog.carbon_input_type_group.addButton(dialog.rb_carbon_chm)
        dialog.carbon_input_type_group.addButton(dialog.rb_carbon_vec)

        in_type_row = QHBoxLayout()
        in_type_row.addWidget(dialog.rb_carbon_chm)
        in_type_row.addWidget(dialog.rb_carbon_vec)
        dialog.form_layout.addRow("Input Data Type:", in_type_row)

        # Raster picker
        r_row = QHBoxLayout()
        dialog.raster_combo = QComboBox()
        btn_r_browse = QPushButton("Browse...")
        btn_r_browse.setMinimumWidth(85)
        def _browse_chm_carbon():
            p, _ = QFileDialog.getOpenFileName(dialog, "Select CHM Raster", "", "Raster (*.tif *.tiff *.img);;All Files (*.*)")
            if p:
                dialog.raster_combo.insertItem(0, f"🌲 {os.path.basename(p)}", p)
                dialog.raster_combo.setCurrentIndex(0)
        btn_r_browse.clicked.connect(_browse_chm_carbon)
        r_row.addWidget(dialog.raster_combo, 1)
        r_row.addWidget(btn_r_browse)
        dialog.chm_row_widget = QWidget()
        chm_l = QHBoxLayout(dialog.chm_row_widget)
        chm_l.setContentsMargins(0, 0, 0, 0)
        chm_l.addWidget(dialog.raster_combo, 1)
        chm_l.addWidget(btn_r_browse)
        dialog.form_layout.addRow("Input Canopy Height Model (CHM):", dialog.chm_row_widget)

        # Vector picker
        v_row = QHBoxLayout()
        dialog.vector_combo = QComboBox()
        btn_v_browse = QPushButton("Browse...")
        btn_v_browse.setMinimumWidth(85)
        def _browse_vec_carbon():
            p, _ = QFileDialog.getOpenFileName(dialog, "Select Trees Vector", "", "Vector (*.gpkg *.shp *.geojson);;All Files (*.*)")
            if p:
                dialog.vector_combo.insertItem(0, f"📍 {os.path.basename(p)}", p)
                dialog.vector_combo.setCurrentIndex(0)
        btn_v_browse.clicked.connect(_browse_vec_carbon)
        dialog.vec_row_widget = QWidget()
        vec_l = QHBoxLayout(dialog.vec_row_widget)
        vec_l.setContentsMargins(0, 0, 0, 0)
        vec_l.addWidget(dialog.vector_combo, 1)
        vec_l.addWidget(btn_v_browse)
        dialog.form_layout.addRow("Input Trees Vector Layer:", dialog.vec_row_widget)
        dialog.vec_row_widget.setVisible(False)

        def _on_carbon_type_toggled():
            is_chm = dialog.rb_carbon_chm.isChecked()
            dialog.chm_row_widget.setVisible(is_chm)
            dialog.vec_row_widget.setVisible(not is_chm)
        dialog.rb_carbon_chm.toggled.connect(_on_carbon_type_toggled)

        # Preset Allometry
        dialog.preset_combo = QComboBox()
        dialog.preset_combo.addItems([
            "Temperate Mixed & Conifer (Lefsky et al.)",
            "Tropical & Subtropical Rainforest (Asner et al.)",
            "Boreal Taiga Forest (Baccini / IPCC)",
            "Commercial Fast Plantation (Eucalyptus / Poplar)",
            "Custom Allometric Power-Law Model"
        ])
        dialog.preset_combo.setCurrentIndex(0)
        dialog.form_layout.addRow("Forest Allometry Preset:", dialog.preset_combo)

        # Wood density
        dialog.wood_density_spin = QDoubleSpinBox()
        dialog.wood_density_spin.setRange(0.1, 1.5)
        dialog.wood_density_spin.setValue(0.52)
        dialog.wood_density_spin.setSingleStep(0.05)
        dialog.wood_density_spin.setSuffix(" g/cm³")
        dialog.form_layout.addRow("Wood Specific Gravity:", dialog.wood_density_spin)

        # Root-to-shoot ratio
        dialog.root_shoot_spin = QDoubleSpinBox()
        dialog.root_shoot_spin.setRange(0.05, 0.60)
        dialog.root_shoot_spin.setValue(0.235)
        dialog.root_shoot_spin.setSingleStep(0.01)
        dialog.root_shoot_spin.setToolTip("IPCC Cairns et al. Belowground Biomass ratio (BGB = R * AGB)")
        dialog.form_layout.addRow("Root-to-Shoot Ratio (BGB):", dialog.root_shoot_spin)

        # Carbon fraction
        dialog.carbon_fraction_spin = QDoubleSpinBox()
        dialog.carbon_fraction_spin.setRange(0.30, 0.60)
        dialog.carbon_fraction_spin.setValue(0.47)
        dialog.carbon_fraction_spin.setSingleStep(0.01)
        dialog.carbon_fraction_spin.setToolTip("IPCC Tier 1/2 standard carbon fraction in dry biomass (0.47)")
        dialog.form_layout.addRow("Carbon Fraction (fC):", dialog.carbon_fraction_spin)

        # Carbon price
        dialog.carbon_price_spin = QDoubleSpinBox()
        dialog.carbon_price_spin.setRange(0.0, 500.0)
        dialog.carbon_price_spin.setValue(25.0)
        dialog.carbon_price_spin.setSingleStep(5.0)
        dialog.carbon_price_spin.setPrefix("$ ")
        dialog.carbon_price_spin.setSuffix(" / tonne CO2e")
        dialog.form_layout.addRow("Carbon Credit Market Price:", dialog.carbon_price_spin)

    elif dtype == "lidar_powerline":
        from PyQt5.QtWidgets import QFileDialog

        p_row = QHBoxLayout()
        dialog.las_combo = QComboBox()
        btn_las = QPushButton("Browse...")
        btn_las.setMinimumWidth(85)
        def _browse_las():
            filt = "LiDAR Point Cloud (*.las *.laz *.copc.laz);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select LiDAR Point Cloud", "", filt)
            if path:
                dialog.las_combo.insertItem(0, f"☁ {os.path.basename(path)}", path)
                dialog.las_combo.setCurrentIndex(0)
        btn_las.clicked.connect(_browse_las)
        p_row.addWidget(dialog.las_combo, 1)
        p_row.addWidget(btn_las)
        dialog.form_layout.addRow("Input LiDAR Point Cloud (LAS/LAZ):", p_row)

        dialog.min_wire_h_spin = QDoubleSpinBox()
        dialog.min_wire_h_spin.setRange(1.0, 30.0)
        dialog.min_wire_h_spin.setValue(4.0)
        dialog.min_wire_h_spin.setSuffix(" m")
        dialog.form_layout.addRow("Minimum Wire Clearance Height:", dialog.min_wire_h_spin)

        dialog.max_wire_h_spin = QDoubleSpinBox()
        dialog.max_wire_h_spin.setRange(10.0, 200.0)
        dialog.max_wire_h_spin.setValue(65.0)
        dialog.max_wire_h_spin.setSuffix(" m")
        dialog.form_layout.addRow("Maximum Conductor Wire Height:", dialog.max_wire_h_spin)

        dialog.linearity_spin = QDoubleSpinBox()
        dialog.linearity_spin.setRange(0.40, 0.95)
        dialog.linearity_spin.setValue(0.70)
        dialog.linearity_spin.setSingleStep(0.05)
        dialog.linearity_spin.setToolTip("Minimum 3D eigenvalue linearity threshold (L1-L2)/L1 for wire detection")
        dialog.form_layout.addRow("Conductor Linearity Threshold:", dialog.linearity_spin)

        dialog.min_span_len_spin = QDoubleSpinBox()
        dialog.min_span_len_spin.setRange(5.0, 150.0)
        dialog.min_span_len_spin.setValue(20.0)
        dialog.min_span_len_spin.setSuffix(" m")
        dialog.min_span_len_spin.setToolTip("Minimum continuous 3D length of a wire span to filter out short tree branches")
        dialog.form_layout.addRow("Minimum Conductor Span Length:", dialog.min_span_len_spin)

        dialog.min_tower_h_spin = QDoubleSpinBox()
        dialog.min_tower_h_spin.setRange(5.0, 150.0)
        dialog.min_tower_h_spin.setValue(12.0)
        dialog.min_tower_h_spin.setSuffix(" m")
        dialog.form_layout.addRow("Minimum Transmission Tower Height:", dialog.min_tower_h_spin)

        dialog.cb_exclude_veg = QCheckBox("Exclude Pre-Classified Vegetation (Classes 3, 4, 5)")
        dialog.cb_exclude_veg.setChecked(True)
        dialog.cb_exclude_veg.setToolTip("Skip points already identified as vegetation to eliminate canopy false positives")
        dialog.form_layout.addRow("", dialog.cb_exclude_veg)

        dialog.cb_require_tower_wire = QCheckBox("Require Wire Connection for Transmission Towers")
        dialog.cb_require_tower_wire.setChecked(True)
        dialog.cb_require_tower_wire.setToolTip("Ensure detected towers connect to overhead wires to prevent mistaking tree trunks for pylons")
        dialog.form_layout.addRow("", dialog.cb_require_tower_wire)

        dialog.cb_export_vectors = QCheckBox("Export 3D Conductor Lines & Tower Footprints Vector Layers")
        dialog.cb_export_vectors.setChecked(True)
        dialog.form_layout.addRow("", dialog.cb_export_vectors)

    elif dtype == "lidar_clearance":
        from PyQt5.QtWidgets import QFileDialog

        w_row = QHBoxLayout()
        dialog.wire_combo = QComboBox()
        btn_w = QPushButton("Browse...")
        btn_w.setMinimumWidth(85)
        def _browse_wire():
            filt = "Conductor Source (*.gpkg *.shp *.las *.laz);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Conductors Layer / LAS", "", filt)
            if path:
                dialog.wire_combo.insertItem(0, f"⚡ {os.path.basename(path)}", path)
                dialog.wire_combo.setCurrentIndex(0)
        btn_w.clicked.connect(_browse_wire)
        w_row.addWidget(dialog.wire_combo, 1)
        w_row.addWidget(btn_w)
        dialog.form_layout.addRow("Conductor Wires (Vector / LAS):", w_row)

        v_row = QHBoxLayout()
        dialog.veg_combo = QComboBox()
        btn_v = QPushButton("Browse...")
        btn_v.setMinimumWidth(85)
        def _browse_veg():
            filt = "Vegetation Source (*.gpkg *.shp *.tif *.las *.laz);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Trees / Canopy Source", "", filt)
            if path:
                dialog.veg_combo.insertItem(0, f"🌲 {os.path.basename(path)}", path)
                dialog.veg_combo.setCurrentIndex(0)
        btn_v.clicked.connect(_browse_veg)
        v_row.addWidget(dialog.veg_combo, 1)
        v_row.addWidget(btn_v)
        dialog.form_layout.addRow("Trees / Canopy Vegetation Layer:", v_row)

        dialog.crit_dist_spin = QDoubleSpinBox()
        dialog.crit_dist_spin.setRange(0.5, 10.0)
        dialog.crit_dist_spin.setValue(3.0)
        dialog.crit_dist_spin.setSuffix(" m")
        dialog.crit_dist_spin.setToolTip("Critical flashover danger threshold")
        dialog.form_layout.addRow("Critical Clearance Buffer (<):", dialog.crit_dist_spin)

        dialog.warn_dist_spin = QDoubleSpinBox()
        dialog.warn_dist_spin.setRange(1.0, 20.0)
        dialog.warn_dist_spin.setValue(5.0)
        dialog.warn_dist_spin.setSuffix(" m")
        dialog.warn_dist_spin.setToolTip("Warning / Encroachment buffer zone")
        dialog.form_layout.addRow("Warning Encroachment Buffer (<):", dialog.warn_dist_spin)

        dialog.advisory_dist_spin = QDoubleSpinBox()
        dialog.advisory_dist_spin.setRange(2.0, 50.0)
        dialog.advisory_dist_spin.setValue(8.0)
        dialog.advisory_dist_spin.setSuffix(" m")
        dialog.form_layout.addRow("Advisory Corridor Boundary (<):", dialog.advisory_dist_spin)

        dialog.fall_buf_spin = QDoubleSpinBox()
        dialog.fall_buf_spin.setRange(0.0, 10.0)
        dialog.fall_buf_spin.setValue(1.5)
        dialog.fall_buf_spin.setSuffix(" m")
        dialog.fall_buf_spin.setToolTip("Safety clearance buffer added to tree height for fall-in danger trees")
        dialog.form_layout.addRow("Danger Tree Fall-In Safety Margin:", dialog.fall_buf_spin)

        dialog.cb_corridor_buffers = QCheckBox("Generate Corridor Buffer Hazard Polygons (Critical, Warning, Advisory)")
        dialog.cb_corridor_buffers.setChecked(True)
        dialog.form_layout.addRow("", dialog.cb_corridor_buffers)

    elif dtype == "lidar_roofs":
        from PyQt5.QtWidgets import QFileDialog

        r_row = QHBoxLayout()
        dialog.las_combo = QComboBox()
        btn_r = QPushButton("Browse...")
        btn_r.setMinimumWidth(85)
        def _browse_roof_las():
            filt = "LiDAR Point Cloud (*.las *.laz *.copc.laz);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Building LiDAR File", "", filt)
            if path:
                dialog.las_combo.insertItem(0, f"🏛 {os.path.basename(path)}", path)
                dialog.las_combo.setCurrentIndex(0)
        btn_r.clicked.connect(_browse_roof_las)
        r_row.addWidget(dialog.las_combo, 1)
        r_row.addWidget(btn_r)
        dialog.form_layout.addRow("Input LiDAR Point Cloud (LAS/LAZ):", r_row)

        dialog.bldg_class_combo = QComboBox()
        dialog.bldg_class_combo.addItems([
            "Class 6: Building Points (Standard ASPRS)",
            "Elevated Non-Ground (Height > Min + 2.5m)",
            "All Point Classes (Direct Fit)"
        ])
        dialog.bldg_class_combo.setCurrentIndex(0)
        dialog.form_layout.addRow("Target Building Classification:", dialog.bldg_class_combo)

        dialog.min_bldg_h_spin = QDoubleSpinBox()
        dialog.min_bldg_h_spin.setRange(1.0, 15.0)
        dialog.min_bldg_h_spin.setValue(2.20)
        dialog.min_bldg_h_spin.setSingleStep(0.20)
        dialog.min_bldg_h_spin.setSuffix(" m")
        dialog.min_bldg_h_spin.setToolTip("Minimum height above local terrain required to recognize a building structure (rejects ground berms, mounds, and vehicles)")
        dialog.form_layout.addRow("Minimum Building Height (HAG):", dialog.min_bldg_h_spin)

        dialog.dist_thresh_spin = QDoubleSpinBox()
        dialog.dist_thresh_spin.setRange(0.05, 1.0)
        dialog.dist_thresh_spin.setValue(0.20)
        dialog.dist_thresh_spin.setSingleStep(0.05)
        dialog.dist_thresh_spin.setSuffix(" m")
        dialog.dist_thresh_spin.setToolTip("RANSAC point-to-plane residual distance threshold")
        dialog.form_layout.addRow("Plane Fitting Tolerance (Distance):", dialog.dist_thresh_spin)

        dialog.angle_dev_spin = QDoubleSpinBox()
        dialog.angle_dev_spin.setRange(5.0, 45.0)
        dialog.angle_dev_spin.setValue(15.0)
        dialog.angle_dev_spin.setSuffix(" °")
        dialog.form_layout.addRow("Max Normal Angle Deviation:", dialog.angle_dev_spin)

        dialog.min_facet_area_spin = QDoubleSpinBox()
        dialog.min_facet_area_spin.setRange(1.0, 50.0)
        dialog.min_facet_area_spin.setValue(4.0)
        dialog.min_facet_area_spin.setSuffix(" m²")
        dialog.form_layout.addRow("Minimum Roof Facet Area:", dialog.min_facet_area_spin)

        dialog.cb_solar_analysis = QCheckBox("Calculate Solar PV Insolation Potential Rating")
        dialog.cb_solar_analysis.setChecked(True)
        dialog.form_layout.addRow("", dialog.cb_solar_analysis)

    elif dtype == "lidar_road_surface":
        p_row = QHBoxLayout()
        dialog.las_combo = QComboBox()
        btn_las = QPushButton("Browse...")
        btn_las.setMinimumWidth(85)
        def _browse_road_las():
            filt = "LiDAR Point Cloud (*.las *.laz *.copc.laz);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Road LiDAR File", "", filt)
            if path:
                dialog.las_combo.insertItem(0, f"🛣️ {os.path.basename(path)}", path)
                dialog.las_combo.setCurrentIndex(0)
        btn_las.clicked.connect(_browse_road_las)
        p_row.addWidget(dialog.las_combo, 1)
        p_row.addWidget(btn_las)
        dialog.form_layout.addRow("Input LiDAR Point Cloud (LAS/LAZ):", p_row)

        # Optional reference centerline vector
        ref_row = QHBoxLayout()
        dialog.ref_centerline_combo = QComboBox()
        dialog.ref_centerline_combo.addItem("[None - Autonomous Corridor Extraction]", "")
        btn_ref_cl = QPushButton("Browse...")
        btn_ref_cl.setMinimumWidth(85)
        def _browse_ref_cl():
            filt = "Vector Lines (*.gpkg *.shp *.geojson);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Road Centerline / Alignment Vector", "", filt)
            if path:
                dialog.ref_centerline_combo.insertItem(1, f"🛣️ {os.path.basename(path)}", path)
                dialog.ref_centerline_combo.setCurrentIndex(1)
        btn_ref_cl.clicked.connect(_browse_ref_cl)
        ref_row.addWidget(dialog.ref_centerline_combo, 1)
        ref_row.addWidget(btn_ref_cl)
        dialog.form_layout.addRow("Road Alignment Vector (Optional Guidance):", ref_row)

        dialog.max_corridor_width_spin = QDoubleSpinBox()
        dialog.max_corridor_width_spin.setRange(3.0, 30.0)
        dialog.max_corridor_width_spin.setValue(12.0)
        dialog.max_corridor_width_spin.setSingleStep(1.0)
        dialog.max_corridor_width_spin.setSuffix(" m")
        dialog.max_corridor_width_spin.setToolTip("Maximum road corridor width. Broad agricultural fields and pastures exceeding this width are strictly excluded.")
        dialog.form_layout.addRow("Max Road Corridor Width (Reject Fields):", dialog.max_corridor_width_spin)

        dialog.max_hag_spin = QDoubleSpinBox()
        dialog.max_hag_spin.setRange(0.05, 1.50)
        dialog.max_hag_spin.setValue(0.35)
        dialog.max_hag_spin.setSingleStep(0.05)
        dialog.max_hag_spin.setSuffix(" m")
        dialog.max_hag_spin.setToolTip("Maximum height above local ground baseline for pavement surface detection")
        dialog.form_layout.addRow("Max Height Above Ground (HAG):", dialog.max_hag_spin)

        dialog.min_planarity_spin = QDoubleSpinBox()
        dialog.min_planarity_spin.setRange(0.30, 0.98)
        dialog.min_planarity_spin.setValue(0.65)
        dialog.min_planarity_spin.setSingleStep(0.05)
        dialog.min_planarity_spin.setToolTip("Minimum 3D eigenvalue planarity tensor (L2 - L3) / L1 threshold")
        dialog.form_layout.addRow("Pavement Planarity Threshold:", dialog.min_planarity_spin)

        dialog.max_roughness_spin = QDoubleSpinBox()
        dialog.max_roughness_spin.setRange(0.01, 0.30)
        dialog.max_roughness_spin.setValue(0.08)
        dialog.max_roughness_spin.setSingleStep(0.01)
        dialog.max_roughness_spin.setSuffix(" m")
        dialog.max_roughness_spin.setToolTip("Maximum local elevation standard deviation (sigma Z) for asphalt flatness")
        dialog.form_layout.addRow("Max Surface Roughness (sigma Z):", dialog.max_roughness_spin)

        dialog.min_vert_spin = QDoubleSpinBox()
        dialog.min_vert_spin.setRange(0.50, 0.99)
        dialog.min_vert_spin.setValue(0.85)
        dialog.min_vert_spin.setSingleStep(0.05)
        dialog.min_vert_spin.setToolTip("Normal vector verticality |Nz| threshold to reject steep embankments and curbs")
        dialog.form_layout.addRow("Normal Verticality Threshold (|Nz|):", dialog.min_vert_spin)

        dialog.min_road_area_spin = QDoubleSpinBox()
        dialog.min_road_area_spin.setRange(5.0, 1000.0)
        dialog.min_road_area_spin.setValue(50.0)
        dialog.min_road_area_spin.setSingleStep(10.0)
        dialog.min_road_area_spin.setSuffix(" m²")
        dialog.min_road_area_spin.setToolTip("Minimum continuous corridor area (m²) to reject isolated tractor furrows, ruts, and field patches (e.g. 50-100 m² for rural surveys)")
        dialog.form_layout.addRow("Minimum Road Corridor Area:", dialog.min_road_area_spin)

        dialog.cb_export_corridor_vec = QCheckBox("Export Road Pavement Boundary Polygon Vector (GPKG)")
        dialog.cb_export_corridor_vec.setChecked(True)
        dialog.form_layout.addRow("", dialog.cb_export_corridor_vec)

    elif dtype == "lidar_road_corridor":
        r_row = QHBoxLayout()
        dialog.road_combo = QComboBox()
        btn_r = QPushButton("Browse...")
        btn_r.setMinimumWidth(85)
        def _browse_road_src():
            filt = "Road Source (*.las *.laz *.gpkg *.shp);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Road Data Source", "", filt)
            if path:
                dialog.road_combo.insertItem(0, f"🛣️ {os.path.basename(path)}", path)
                dialog.road_combo.setCurrentIndex(0)
        btn_r.clicked.connect(_browse_road_src)
        r_row.addWidget(dialog.road_combo, 1)
        r_row.addWidget(btn_r)
        dialog.form_layout.addRow("Input Road Surface (LAS/Vector):", r_row)

        dialog.station_interval_spin = QDoubleSpinBox()
        dialog.station_interval_spin.setRange(5.0, 200.0)
        dialog.station_interval_spin.setValue(25.0)
        dialog.station_interval_spin.setSingleStep(5.0)
        dialog.station_interval_spin.setSuffix(" m")
        dialog.station_interval_spin.setToolTip("Interval spacing for equidistant station chainage markers (e.g. 0+000, 0+025)")
        dialog.form_layout.addRow("Chainage Station Interval:", dialog.station_interval_spin)

        dialog.corridor_step_spin = QDoubleSpinBox()
        dialog.corridor_step_spin.setRange(1.0, 20.0)
        dialog.corridor_step_spin.setValue(5.0)
        dialog.corridor_step_spin.setSuffix(" m")
        dialog.corridor_step_spin.setToolTip("Cross-section segmentation step along the principal corridor axis")
        dialog.form_layout.addRow("Corridor Tracing Step Size:", dialog.corridor_step_spin)

        dialog.cb_detect_curbs = QCheckBox("Extract Left & Right Road Curb / Edge Lines")
        dialog.cb_detect_curbs.setChecked(True)
        dialog.form_layout.addRow("", dialog.cb_detect_curbs)

    elif dtype == "lidar_road_condition":
        # Road centerline vector
        c_row = QHBoxLayout()
        dialog.road_combo = QComboBox()
        btn_c = QPushButton("Browse...")
        btn_c.setMinimumWidth(85)
        def _browse_cl_src():
            filt = "Road Centerline (*.gpkg *.shp *.geojson);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Road Centerline Layer", "", filt)
            if path:
                dialog.road_combo.insertItem(0, f"🛣️ {os.path.basename(path)}", path)
                dialog.road_combo.setCurrentIndex(0)
        btn_c.clicked.connect(_browse_cl_src)
        c_row.addWidget(dialog.road_combo, 1)
        c_row.addWidget(btn_c)
        dialog.form_layout.addRow("Road Centerline Alignment (Vector):", c_row)

        # Full LiDAR Point Cloud
        l_row = QHBoxLayout()
        dialog.las_combo = QComboBox()
        btn_l = QPushButton("Browse...")
        btn_l.setMinimumWidth(85)
        def _browse_cond_las():
            filt = "LiDAR Point Cloud (*.las *.laz *.copc.laz);;All Files (*.*)"
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Full LiDAR File", "", filt)
            if path:
                dialog.las_combo.insertItem(0, f"☁️ {os.path.basename(path)}", path)
                dialog.las_combo.setCurrentIndex(0)
        btn_l.clicked.connect(_browse_cond_las)
        l_row.addWidget(dialog.las_combo, 1)
        l_row.addWidget(btn_l)
        dialog.form_layout.addRow("Full Corridor LiDAR (LAS/LAZ):", l_row)

        dialog.corridor_width_spin = QDoubleSpinBox()
        dialog.corridor_width_spin.setRange(3.0, 50.0)
        dialog.corridor_width_spin.setValue(8.0)
        dialog.corridor_width_spin.setSuffix(" m")
        dialog.corridor_width_spin.setToolTip("Total corridor width to scan for overhead obstructions and surface roughness")
        dialog.form_layout.addRow("Road Corridor Inspection Width:", dialog.corridor_width_spin)

        dialog.clearance_height_spin = QDoubleSpinBox()
        dialog.clearance_height_spin.setRange(3.0, 10.0)
        dialog.clearance_height_spin.setValue(4.80)
        dialog.clearance_height_spin.setSuffix(" m")
        dialog.clearance_height_spin.setToolTip("Required overhead vehicle clearance envelope height (standard 4.8m - 5.0m)")
        dialog.form_layout.addRow("Required Vehicle Clearance Height:", dialog.clearance_height_spin)

        dialog.crit_clearance_spin = QDoubleSpinBox()
        dialog.crit_clearance_spin.setRange(2.0, 6.0)
        dialog.crit_clearance_spin.setValue(4.00)
        dialog.crit_clearance_spin.setSuffix(" m")
        dialog.crit_clearance_spin.setToolTip("Critical collision danger threshold for commercial trucks & buses (< 4.0m)")
        dialog.form_layout.addRow("Critical Collision Clearance (<):", dialog.crit_clearance_spin)

        dialog.max_grade_spin = QDoubleSpinBox()
        dialog.max_grade_spin.setRange(2.0, 25.0)
        dialog.max_grade_spin.setValue(8.0)
        dialog.max_grade_spin.setSuffix(" %")
        dialog.max_grade_spin.setToolTip("Design threshold for steep longitudinal slopes / grades")
        dialog.form_layout.addRow("Maximum Design Grade (Warning):", dialog.max_grade_spin)

        dialog.crit_grade_spin = QDoubleSpinBox()
        dialog.crit_grade_spin.setRange(5.0, 35.0)
        dialog.crit_grade_spin.setValue(12.0)
        dialog.crit_grade_spin.setSuffix(" %")
        dialog.crit_grade_spin.setToolTip("Critical steep grade hazard limit")
        dialog.form_layout.addRow("Critical Grade Violation Limit:", dialog.crit_grade_spin)

    else:
        dialog.raster_combo = QComboBox()
        dialog.form_layout.addRow("Input Layer:", dialog.raster_combo)


