# -*- coding: utf-8 -*-
"""
GeoStudio - Volumetric Analysis Dialog UI Layout
Constructs main window layout, configuration forms, summary cards, and stage capacity tabs.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QPushButton,
    QTabWidget, QTableWidget, QTextEdit, QGroupBox, QHeaderView, QFrame
)
from ui.canvas.stage_storage_plot_canvas import StageStoragePlotCanvas


def create_metric_card(title: str, init_val: str, color_hex: str) -> QFrame:
    """Constructs a modern styled KPI telemetry card."""
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-left: 4px solid {color_hex};
            border-radius: 4px;
            padding: 4px 8px;
        }}
    """)
    l = QVBoxLayout(card)
    l.setContentsMargins(2, 2, 2, 2)
    l.setSpacing(2)

    t_lbl = QLabel(title)
    t_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 500;")
    v_lbl = QLabel(init_val)
    v_lbl.setStyleSheet(f"color: {color_hex}; font-size: 13px; font-weight: bold;")
    v_lbl.setObjectName("val_label")

    l.addWidget(t_lbl)
    l.addWidget(v_lbl)
    return card


def build_volumetric_ui(dlg):
    """Builds full layout for VolumetricAnalysisDialog."""
    main_layout = QVBoxLayout(dlg)
    main_layout.setContentsMargins(14, 14, 14, 14)
    main_layout.setSpacing(10)

    # Header Banner
    header = QFrame()
    header.setStyleSheet("background: #0f172a; border-radius: 6px; padding: 8px;")
    h_layout = QHBoxLayout(header)
    h_layout.setContentsMargins(12, 6, 12, 6)

    title_lbl = QLabel("📐 Volumetric Analysis & Hypsometric Stage-Storage Capacity")
    title_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold;")
    h_layout.addWidget(title_lbl)
    h_layout.addStretch()

    badge_lbl = QLabel("Single-Surface Volumetrics")
    badge_lbl.setStyleSheet("background: #1e293b; color: #94a3b8; border-radius: 4px; padding: 2px 8px; font-size: 10px;")
    h_layout.addWidget(badge_lbl)
    main_layout.addWidget(header)

    # Configuration Panel
    config_group = QGroupBox("Analysis Parameters")
    config_layout = QFormLayout(config_group)
    config_layout.setContentsMargins(10, 10, 10, 10)
    config_layout.setSpacing(8)

    dlg.layer_combo = QComboBox()
    dlg.layer_combo.currentIndexChanged.connect(dlg._on_layer_changed)
    config_layout.addRow("Input DEM Layer:", dlg.layer_combo)

    datum_row = QHBoxLayout()
    dlg.datum_spin = QDoubleSpinBox()
    dlg.datum_spin.setRange(-2000.0, 10000.0)
    dlg.datum_spin.setDecimals(2)
    dlg.datum_spin.setValue(100.0)
    dlg.datum_spin.setSuffix(" m")
    datum_row.addWidget(dlg.datum_spin)

    btn_min = QPushButton("Min Elev")
    btn_min.setStyleSheet("padding: 3px 6px; font-size: 10px;")
    btn_min.clicked.connect(dlg._set_datum_min)
    datum_row.addWidget(btn_min)

    btn_mean = QPushButton("Mean Elev")
    btn_mean.setStyleSheet("padding: 3px 6px; font-size: 10px;")
    btn_mean.clicked.connect(dlg._set_datum_mean)
    datum_row.addWidget(btn_mean)

    btn_max = QPushButton("Max Elev")
    btn_max.setStyleSheet("padding: 3px 6px; font-size: 10px;")
    btn_max.clicked.connect(dlg._set_datum_max)
    datum_row.addWidget(btn_max)

    config_layout.addRow("Reference Datum Plane:", datum_row)

    stages_row = QHBoxLayout()
    dlg.stages_spin = QSpinBox()
    dlg.stages_spin.setRange(10, 100)
    dlg.stages_spin.setValue(30)
    stages_row.addWidget(dlg.stages_spin)
    stages_row.addWidget(QLabel("incremental elevation intervals for capacity curve"))
    stages_row.addStretch()

    dlg.btn_calculate = QPushButton("▶ Run Volumetric Analysis")
    dlg.btn_calculate.setObjectName("blueBtn")
    dlg.btn_calculate.clicked.connect(dlg._run_analysis)
    stages_row.addWidget(dlg.btn_calculate)

    config_layout.addRow("Stage Resolution:", stages_row)
    main_layout.addWidget(config_group)

    # Live Summary Cards
    cards_row = QHBoxLayout()
    cards_row.setSpacing(8)

    dlg.card_vol_above = create_metric_card("Volume Above Datum", "0.00 m³", "#0284c7")
    dlg.card_vol_below = create_metric_card("Volume Below (Capacity)", "0.00 m³", "#0d9488")
    dlg.card_total_area = create_metric_card("Surface Area", "0.00 ha", "#64748b")
    dlg.card_stockpile = create_metric_card("Stockpile Est. Volume", "0.00 m³", "#d97706")

    cards_row.addWidget(dlg.card_vol_above)
    cards_row.addWidget(dlg.card_vol_below)
    cards_row.addWidget(dlg.card_total_area)
    cards_row.addWidget(dlg.card_stockpile)
    main_layout.addLayout(cards_row)

    # Results Tabs
    dlg.tabs = QTabWidget()
    dlg.tabs.setStyleSheet("""
        QTabWidget::pane { border: 1px solid #cbd5e1; background: #ffffff; border-radius: 4px; }
        QTabBar::tab { background: #f1f5f9; color: #475569; padding: 6px 14px; font-size: 11px; font-weight: 500; }
        QTabBar::tab:selected { background: #ffffff; color: #0f172a; font-weight: bold; border-bottom: 2px solid #0284c7; }
    """)

    chart_widget = QWidget()
    chart_layout = QVBoxLayout(chart_widget)
    chart_layout.setContentsMargins(6, 6, 6, 6)
    dlg.plot_canvas = StageStoragePlotCanvas(dlg)
    chart_layout.addWidget(dlg.plot_canvas)
    dlg.tabs.addTab(chart_widget, "📈 Stage-Storage & Capacity Curve")

    table_widget = QWidget()
    table_layout = QVBoxLayout(table_widget)
    table_layout.setContentsMargins(6, 6, 6, 6)
    dlg.table = QTableWidget()
    dlg.table.setColumnCount(6)
    dlg.table.setHorizontalHeaderLabels([
        "Stage #", "Elevation (m)", "Stage Height (m)",
        "Submerged Area (ha)", "Capacity Volume (m³)", "Volume Above (m³)"
    ])
    dlg.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    dlg.table.setAlternatingRowColors(True)
    dlg.table.setStyleSheet("QTableWidget { font-size: 11px; background: #ffffff; }")
    table_layout.addWidget(dlg.table)
    dlg.tabs.addTab(table_widget, "📊 Stage Capacity Data Table")

    report_widget = QWidget()
    report_layout = QVBoxLayout(report_widget)
    report_layout.setContentsMargins(6, 6, 6, 6)
    dlg.report_edit = QTextEdit()
    dlg.report_edit.setReadOnly(True)
    dlg.report_edit.setStyleSheet("font-family: monospace; font-size: 11px; background: #ffffff; color: #0f172a;")
    report_layout.addWidget(dlg.report_edit)
    dlg.tabs.addTab(report_widget, "📄 Full Engineering Report")

    main_layout.addWidget(dlg.tabs)

    # Bottom Action Bar
    bottom_row = QHBoxLayout()
    dlg.btn_export_csv = QPushButton("💾 Export CSV Table...")
    dlg.btn_export_csv.clicked.connect(dlg._export_csv)
    dlg.btn_export_csv.setEnabled(False)
    bottom_row.addWidget(dlg.btn_export_csv)

    dlg.btn_export_report = QPushButton("📄 Save Report...")
    dlg.btn_export_report.clicked.connect(dlg._export_report)
    dlg.btn_export_report.setEnabled(False)
    bottom_row.addWidget(dlg.btn_export_report)

    bottom_row.addStretch()

    dlg.btn_close = QPushButton("Close")
    dlg.btn_close.setObjectName("grayBtn")
    dlg.btn_close.clicked.connect(dlg.close)
    bottom_row.addWidget(dlg.btn_close)

    main_layout.addLayout(bottom_row)
