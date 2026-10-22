# -*- coding: utf-8 -*-
"""
GeoStudio - Cut & Fill Dialog UI Layout Helpers
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QComboBox,
    QDoubleSpinBox, QCheckBox, QPushButton, QTabWidget, QTextEdit,
    QProgressBar, QGroupBox, QFrame, QRadioButton, QButtonGroup, QLineEdit
)
from PyQt5.QtCore import Qt


def build_cut_fill_ui(dlg):
    """Builds the main layout, widgets, summary cards, and tabs for CutFillDialog."""
    main_layout = QVBoxLayout(dlg)
    main_layout.setContentsMargins(14, 14, 14, 14)
    main_layout.setSpacing(10)

    # Header Banner
    header = QFrame()
    header.setStyleSheet("background: #0f172a; border-radius: 6px; padding: 8px;")
    h_layout = QHBoxLayout(header)
    h_layout.setContentsMargins(12, 6, 12, 6)

    title_lbl = QLabel("🚜 Earthwork Cut & Fill Volumetrics & Grading Optimization")
    title_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold;")
    h_layout.addWidget(title_lbl)
    h_layout.addStretch()

    badge_lbl = QLabel("Dual Surface & Datum Earthworks")
    badge_lbl.setStyleSheet("background: #1e293b; color: #94a3b8; border-radius: 4px; padding: 2px 8px; font-size: 10px;")
    h_layout.addWidget(badge_lbl)
    main_layout.addWidget(header)

    # Configuration Group
    config_group = QGroupBox("Surfaces & Parameters")
    config_layout = QFormLayout(config_group)
    config_layout.setContentsMargins(10, 10, 10, 10)
    config_layout.setSpacing(8)

    mode_row = QHBoxLayout()
    dlg.rb_datum = QRadioButton("Base DEM vs Fixed Elevation Datum Plane")
    dlg.rb_surface = QRadioButton("Base DEM (Existing) vs Comparison DEM (Design Grade)")
    dlg.rb_datum.setChecked(True)

    dlg.mode_group = QButtonGroup(dlg)
    dlg.mode_group.addButton(dlg.rb_datum, 0)
    dlg.mode_group.addButton(dlg.rb_surface, 1)
    dlg.mode_group.buttonClicked.connect(dlg._on_mode_changed)

    mode_row.addWidget(dlg.rb_datum)
    mode_row.addWidget(dlg.rb_surface)
    mode_row.addStretch()
    config_layout.addRow("Calculation Mode:", mode_row)

    dlg.base_combo = QComboBox()
    dlg.base_combo.currentIndexChanged.connect(dlg._on_base_changed)
    config_layout.addRow("Base (Existing Ground) DEM:", dlg.base_combo)

    datum_row = QHBoxLayout()
    dlg.datum_spin = QDoubleSpinBox()
    dlg.datum_spin.setRange(-2000.0, 10000.0)
    dlg.datum_spin.setDecimals(2)
    dlg.datum_spin.setValue(100.0)
    dlg.datum_spin.setSuffix(" m")
    datum_row.addWidget(dlg.datum_spin)

    btn_balance = QPushButton("⚖ Find Balance Plane")
    btn_balance.setToolTip("Solve for flat elevation level that yields zero net earthwork (Cut = Fill)")
    btn_balance.setStyleSheet("background: #e2e8f0; color: #0f172a; font-weight: 600; padding: 3px 8px; font-size: 10px;")
    btn_balance.clicked.connect(dlg._solve_balance_plane)
    datum_row.addWidget(btn_balance)
    config_layout.addRow("Target Datum Elevation:", datum_row)

    dlg.comp_combo = QComboBox()
    dlg.comp_combo.setEnabled(False)
    config_layout.addRow("Comparison (Design) DEM:", dlg.comp_combo)

    factors_row = QHBoxLayout()
    dlg.swell_spin = QDoubleSpinBox()
    dlg.swell_spin.setRange(0.5, 3.0)
    dlg.swell_spin.setValue(1.0)
    dlg.swell_spin.setSingleStep(0.05)

    dlg.shrink_spin = QDoubleSpinBox()
    dlg.shrink_spin.setRange(0.5, 3.0)
    dlg.shrink_spin.setValue(1.0)
    dlg.shrink_spin.setSingleStep(0.05)

    factors_row.addWidget(QLabel("Excavation Swell Factor:"))
    factors_row.addWidget(dlg.swell_spin)
    factors_row.addSpacing(16)
    factors_row.addWidget(QLabel("Embankment Compaction Factor:"))
    factors_row.addWidget(dlg.shrink_spin)
    factors_row.addStretch()
    config_layout.addRow("Material Factors:", factors_row)

    main_layout.addWidget(config_group)

    # Live Summary Cards
    cards_row = QHBoxLayout()
    cards_row.setSpacing(8)

    def create_card(title, bg_color, text_color):
        card = QFrame()
        card.setStyleSheet(f"background: {bg_color}; border-radius: 6px; padding: 6px; border: 1px solid #e2e8f0;")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(6, 4, 6, 4)
        c_layout.setSpacing(2)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 600; text-transform: uppercase;")
        lbl_v = QLabel("--")
        lbl_v.setStyleSheet(f"color: {text_color}; font-size: 14px; font-weight: bold;")
        lbl_s = QLabel("--")
        lbl_s.setStyleSheet("color: #475569; font-size: 10px;")
        c_layout.addWidget(lbl_t)
        c_layout.addWidget(lbl_v)
        c_layout.addWidget(lbl_s)
        return card, lbl_v, lbl_s

    c_cut, dlg.val_cut, dlg.sub_cut = create_card("Cut (Excavation)", "#fef2f2", "#dc2626")
    c_fill, dlg.val_fill, dlg.sub_fill = create_card("Fill (Embankment)", "#eff6ff", "#2563eb")
    c_net, dlg.val_net, dlg.sub_net = create_card("Net Earthwork Balance", "#f8fafc", "#0f172a")

    cards_row.addWidget(c_cut)
    cards_row.addWidget(c_fill)
    cards_row.addWidget(c_net)
    main_layout.addLayout(cards_row)

    # Tabs
    dlg.tabs = QTabWidget()
    dlg.tabs.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #e2e8f0; background: #ffffff; border-radius: 6px; }
        QTabBar::tab { background: #f8fafc; color: #64748b; padding: 6px 14px; font-size: 11px; font-weight: 500; border: 1px solid #e2e8f0; border-top-left-radius: 5px; border-top-right-radius: 5px; }
        QTabBar::tab:selected { background: #ffffff; color: #0f172a; font-weight: 700; border-bottom: 1px solid #ffffff; }
    """)

    dlg.report_edit = QTextEdit()
    dlg.report_edit.setReadOnly(True)
    dlg.report_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background: #0f172a; color: #f8fafc; padding: 8px; border-radius: 4px;")
    dlg.tabs.addTab(dlg.report_edit, "📄 Volumetric Engineering Report")

    main_layout.addWidget(dlg.tabs, 1)

    # Progress bar
    dlg.progress_bar = QProgressBar()
    dlg.progress_bar.setValue(0)
    dlg.progress_bar.setFixedHeight(14)
    dlg.progress_bar.setTextVisible(False)
    main_layout.addWidget(dlg.progress_bar)

    # Action Buttons
    action_row = QHBoxLayout()
    dlg.cb_open_diff = QCheckBox("Add 3-Tone Difference Raster to Canvas (Red = Cut, Blue = Fill)")
    dlg.cb_open_diff.setChecked(True)
    dlg.cb_daylight = QCheckBox("Generate Zero-Grade Daylight Line")
    dlg.cb_daylight.setChecked(True)

    action_row.addWidget(dlg.cb_open_diff)
    action_row.addWidget(dlg.cb_daylight)
    action_row.addStretch()

    btn_calc = QPushButton("▶ Calculate Earthwork")
    btn_calc.setObjectName("blueBtn")
    btn_calc.setStyleSheet("background: #0284c7; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
    btn_calc.clicked.connect(dlg._run_calculation)
    action_row.addWidget(btn_calc)

    btn_csv = QPushButton("💾 Export CSV")
    btn_csv.clicked.connect(dlg._export_csv)
    action_row.addWidget(btn_csv)

    btn_close = QPushButton("Close")
    btn_close.clicked.connect(dlg.close)
    action_row.addWidget(btn_close)

    main_layout.addLayout(action_row)
