# -*- coding: utf-8 -*-
"""
GeoStudio / GeoAnalytica - Satellite & Hyperspectral UI Builders
Tab construction for spectral indices, band math, false color composite, and hyperspectral.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QComboBox, QGroupBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QProgressBar, QListWidget, QLineEdit
)


def build_indices_tab(widget):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 4, 4, 4)

    form = QFormLayout()
    widget.idx_raster_combo = QComboBox()
    form.addRow("Raster:", widget.idx_raster_combo)
    widget.idx_raster_combo.currentIndexChanged.connect(widget._update_index_bands)

    widget.idx_nir_band = QSpinBox(); widget.idx_nir_band.setRange(1, 999); widget.idx_nir_band.setValue(4)
    widget.idx_red_band = QSpinBox(); widget.idx_red_band.setRange(1, 999); widget.idx_red_band.setValue(3)
    widget.idx_green_band = QSpinBox(); widget.idx_green_band.setRange(1, 999); widget.idx_green_band.setValue(2)
    widget.idx_swir1_band = QSpinBox(); widget.idx_swir1_band.setRange(1, 999); widget.idx_swir1_band.setValue(5)
    widget.idx_swir2_band = QSpinBox(); widget.idx_swir2_band.setRange(1, 999); widget.idx_swir2_band.setValue(6)

    form.addRow("NIR Band #:", widget.idx_nir_band)
    form.addRow("Red Band #:", widget.idx_red_band)
    form.addRow("Green Band #:", widget.idx_green_band)
    form.addRow("SWIR1 Band #:", widget.idx_swir1_band)
    form.addRow("SWIR2 Band #:", widget.idx_swir2_band)
    layout.addLayout(form)

    savi_row = QHBoxLayout()
    savi_row.addWidget(QLabel("SAVI L factor:"))
    widget.savi_l = QDoubleSpinBox(); widget.savi_l.setRange(0, 1); widget.savi_l.setValue(0.5); widget.savi_l.setSingleStep(0.1)
    savi_row.addWidget(widget.savi_l)
    layout.addLayout(savi_row)

    indices = [
        ("🌿 NDVI", "(NIR-Red)/(NIR+Red)", widget.run_ndvi),
        ("🌾 EVI", "2.5*(NIR-Red)/(NIR+6*Red-7.5*Blue+1)", widget.run_evi),
        ("🌱 SAVI", "((NIR-Red)/(NIR+Red+L))*(1+L)", widget.run_savi),
        ("💧 NDWI", "(Green-NIR)/(Green+NIR)", widget.run_ndwi),
        ("🏙 NDBI", "(SWIR1-NIR)/(SWIR1+NIR)", widget.run_ndbi),
        ("🔥 NBR", "(NIR-SWIR2)/(NIR+SWIR2)", widget.run_nbr),
        ("❄ NDSI", "(Green-SWIR1)/(Green+SWIR1)", widget.run_ndsi),
    ]

    box = QGroupBox("Spectral Indices")
    box_layout = QVBoxLayout()
    for label, formula, func in indices:
        row = QHBoxLayout()
        btn = QPushButton(label)
        btn.setObjectName("toolBtn")
        btn.setToolTip(formula)
        btn.clicked.connect(func)
        fl = QLabel(formula)
        fl.setStyleSheet("color: #64748b; font-size: 10px; font-style: italic;")
        fl.setWordWrap(True)
        row.addWidget(btn, 1)
        row.addWidget(fl, 2)
        box_layout.addLayout(row)
    box.setLayout(box_layout)
    layout.addWidget(box)

    widget.idx_progress = QProgressBar(); widget.idx_progress.setRange(0, 100)
    widget.idx_progress.setFormat("Ready")
    layout.addWidget(widget.idx_progress)
    layout.addStretch()
    return tab


def build_bandmath_tab(widget):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 4, 4, 4)

    hint = QLabel('Enter formula using QGIS Raster Calculator syntax:\nExample: "layer@1" / "layer@2"')
    hint.setStyleSheet("color: #475569; font-size: 11px; padding: 6px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;")
    layout.addWidget(hint)

    form = QFormLayout()
    widget.bm_raster_combo = QComboBox()
    form.addRow("Reference Layer:", widget.bm_raster_combo)
    layout.addLayout(form)

    widget.formula_edit = QTextEdit()
    widget.formula_edit.setPlaceholderText('e.g. ("Landsat@4" - "Landsat@3") / ("Landsat@4" + "Landsat@3")')
    widget.formula_edit.setFixedHeight(80)
    layout.addWidget(QLabel("Formula:"))
    layout.addWidget(widget.formula_edit)

    name_row = QHBoxLayout()
    name_row.addWidget(QLabel("Output name:"))
    widget.bm_output_name = QLineEdit("band_math_result")
    name_row.addWidget(widget.bm_output_name)
    layout.addLayout(name_row)

    btn_run = QPushButton("▶ Run Band Math")
    btn_run.clicked.connect(widget.run_band_math)
    layout.addWidget(btn_run)

    widget.bm_log = QTextEdit()
    widget.bm_log.setReadOnly(True)
    widget.bm_log.setFixedHeight(100)
    layout.addWidget(QLabel("Log:"))
    layout.addWidget(widget.bm_log)
    layout.addStretch()
    return tab


def build_composite_tab(widget):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 4, 4, 4)

    form = QFormLayout()
    widget.comp_raster_combo = QComboBox()
    form.addRow("Raster:", widget.comp_raster_combo)

    widget.comp_r = QSpinBox(); widget.comp_r.setRange(1, 999); widget.comp_r.setValue(4)
    widget.comp_g = QSpinBox(); widget.comp_g.setRange(1, 999); widget.comp_g.setValue(3)
    widget.comp_b = QSpinBox(); widget.comp_b.setRange(1, 999); widget.comp_b.setValue(2)

    form.addRow("Red channel (band #):", widget.comp_r)
    form.addRow("Green channel (band #):", widget.comp_g)
    form.addRow("Blue channel (band #):", widget.comp_b)
    layout.addLayout(form)

    presets_box = QGroupBox("Quick Presets")
    presets_layout = QVBoxLayout()
    presets = [
        ("🌿 Vegetation (NIR/Red/Green)", 4, 3, 2),
        ("🔥 Urban (SWIR2/SWIR1/Red)", 7, 5, 4),
        ("💧 Water (Green/NIR/SWIR1)", 2, 4, 5),
        ("🌾 Agriculture (SWIR1/NIR/Blue)", 5, 4, 1),
        ("🏔 Geology (SWIR2/SWIR1/Blue)", 7, 5, 2),
    ]
    for label, r, g, b in presets:
        btn = QPushButton(label)
        btn.clicked.connect(lambda checked, rv=r, gv=g, bv=b: widget._apply_preset(rv, gv, bv))
        presets_layout.addWidget(btn)
    presets_box.setLayout(presets_layout)
    layout.addWidget(presets_box)

    btn_apply = QPushButton("🎨 Apply Composite")
    btn_apply.clicked.connect(widget.apply_composite)
    layout.addWidget(btn_apply)
    layout.addStretch()
    return tab


def build_hyperspectral_tab(widget):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(4, 4, 4, 4)

    form = QFormLayout()
    widget.hyp_raster_combo = QComboBox()
    form.addRow("Hyperspectral Raster:", widget.hyp_raster_combo)
    layout.addLayout(form)

    info_box = QGroupBox("Band Information")
    info_layout = QVBoxLayout()
    widget.band_list = QListWidget()
    widget.band_list.setFixedHeight(120)
    btn_refresh_bands = QPushButton("🔄 Refresh Bands")
    btn_refresh_bands.clicked.connect(widget._load_band_list)
    info_layout.addWidget(widget.band_list)
    info_layout.addWidget(btn_refresh_bands)
    info_box.setLayout(info_layout)
    layout.addWidget(info_box)

    ops_box = QGroupBox("Hyperspectral Operations")
    ops_layout = QVBoxLayout()

    btn_pca = QPushButton("📉 PCA (Principal Component Analysis)")
    btn_pca.clicked.connect(widget.run_pca)
    btn_mnf = QPushButton("🔷 MNF Transform (Minimum Noise Fraction)")
    btn_mnf.clicked.connect(widget.show_mnf_info)
    btn_profile = QPushButton("📈 Extract Spectral Profile at Point")
    btn_profile.clicked.connect(widget.extract_spectral_profile)
    btn_band_stats = QPushButton("📊 All-band Statistics")
    btn_band_stats.clicked.connect(widget.show_all_band_stats)

    ops_layout.addWidget(btn_pca)
    ops_layout.addWidget(btn_mnf)
    ops_layout.addWidget(btn_profile)
    ops_layout.addWidget(btn_band_stats)
    ops_box.setLayout(ops_layout)
    layout.addWidget(ops_box)

    widget.hyp_log = QTextEdit()
    widget.hyp_log.setReadOnly(True)
    widget.hyp_log.setFixedHeight(120)
    layout.addWidget(QLabel("Output / Log:"))
    layout.addWidget(widget.hyp_log)
    layout.addStretch()
    return tab
