# -*- coding: utf-8 -*-
"""
GeoStudio - 3D Viewer Side Panel Controls
Builds sidebar widgets for symbology, 3D environment settings, point telemetry, and navigation tips.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QComboBox, QCheckBox, QGroupBox, QFrame
)

COLOR_MODES = [
    "Color Lidar by RGB/Elev",
    "Color Lidar by Elevation",
    "Color Lidar by Intensity",
    "Color Lidar by Classification",
    "Color Lidar by Return Number",
    "Color Lidar by Height Above Ground",
    "Color Lidar by Scan Angle",
    "Color Lidar by Point Source ID",
    "Color Lidar by Source Layer",
    "Color Lidar by Segment",
    "Color Lidar by Point Index",
    "Color Lidar as CIR (Color Infrared)",
    "Color Lidar using NDVI (Vegetation)",
    "Color Lidar using NDWI (Water)",
    "Color Lidar by Point Density",
    "Color Lidar by Withheld Flag",
    "Color Lidar by Key Point Flag",
    "Color Lidar by Overlap Flag",
    "Color Lidar by Return Height Delta"
]

COLOR_MODE_KEYS = [
    "RGB/Elev", "Elevation", "Intensity", "Classification", "Return Number",
    "Height Above Ground", "Scan Angle", "Point Source ID", "Source Layer",
    "Segment", "Point Index", "CIR", "NDVI", "NDWI", "Point Density",
    "Withheld Flag", "Key Point Flag", "Overlap Flag", "Return Height Delta"
]


def build_3d_side_panel(win: QWidget) -> QWidget:
    """Constructs the sidebar panel for 3D visualization controls."""
    side_panel = QWidget()
    side_panel.setFixedWidth(280)
    side_layout = QVBoxLayout(side_panel)
    side_layout.setContentsMargins(6, 0, 0, 0)
    side_layout.setSpacing(10)

    # Group: 3D Symbology & Color
    grp_sym = QGroupBox("🎨 3D Color Symbology")
    vbox_sym = QVBoxLayout(grp_sym)
    vbox_sym.setSpacing(8)

    vbox_sym.addWidget(QLabel("Color Palette:"))
    win.combo_color = QComboBox()
    win.combo_color.addItems(COLOR_MODES)
    win.combo_color.currentIndexChanged.connect(win._on_color_mode_changed)
    vbox_sym.addWidget(win.combo_color)

    vbox_sym.addWidget(QLabel("Point Budget / Quality:"))
    win.combo_budget = QComboBox()
    win.combo_budget.addItems([
        "High Detail (6M Points - Default)",
        "Ultra Detail (10M Points)",
        "Full Cloud (Load All Points)",
        "Balanced (4M Points)",
        "Fast Preview (2M Points)"
    ])
    win.combo_budget.currentIndexChanged.connect(win._on_budget_changed)
    vbox_sym.addWidget(win.combo_budget)

    vbox_sym.addWidget(QLabel("Point Size (px):"))
    win.slider_psize = QSlider(Qt.Horizontal)
    win.slider_psize.setRange(1, 15)
    win.slider_psize.setValue(5)
    win.slider_psize.valueChanged.connect(lambda v: win.canvas.set_point_size(float(v)))
    vbox_sym.addWidget(win.slider_psize)

    vbox_sym.addWidget(QLabel("Z-Exaggeration (1.0x - 8.0x):"))
    win.slider_exag = QSlider(Qt.Horizontal)
    win.slider_exag.setRange(10, 80)
    win.slider_exag.setValue(15)
    win.slider_exag.valueChanged.connect(lambda v: win.canvas.set_z_exaggeration(v / 10.0))
    vbox_sym.addWidget(win.slider_exag)

    side_layout.addWidget(grp_sym)

    # Group: Environment & Guides
    grp_env = QGroupBox("🌐 3D Environment")
    vbox_env = QVBoxLayout(grp_env)
    vbox_env.setSpacing(8)

    win.chk_grid = QCheckBox("Show Ground Plane Grid")
    win.chk_grid.setChecked(True)
    win.chk_grid.toggled.connect(lambda checked: setattr(win.canvas, 'show_grid', checked) or win.canvas.update())
    vbox_env.addWidget(win.chk_grid)

    win.chk_bbox = QCheckBox("Show 3D Bounding Box")
    win.chk_bbox.setChecked(True)
    win.chk_bbox.toggled.connect(lambda checked: setattr(win.canvas, 'show_bbox', checked) or win.canvas.update())
    vbox_env.addWidget(win.chk_bbox)

    vbox_env.addWidget(QLabel("Background Theme:"))
    win.combo_theme = QComboBox()
    win.combo_theme.addItems(["Dark Slate", "Studio Gray", "Sky Blue", "Clean White"])
    win.combo_theme.currentTextChanged.connect(win.canvas.set_background_theme)
    vbox_env.addWidget(win.combo_theme)

    side_layout.addWidget(grp_env)

    # Group: Dataset Telemetry
    grp_info = QGroupBox("📊 3D Point Statistics")
    vbox_info = QVBoxLayout(grp_info)
    vbox_info.setSpacing(6)

    win.lbl_points = QLabel("Points Rendered: <b>Loading...</b>")
    vbox_info.addWidget(win.lbl_points)

    win.lbl_zrange = QLabel("Elevation Range: <b>──</b>")
    vbox_info.addWidget(win.lbl_zrange)

    win.lbl_fps = QLabel("GPU Render Rate: <b>60 FPS</b>")
    win.lbl_fps.setStyleSheet("color: #16a34a; font-weight: bold;")
    vbox_info.addWidget(win.lbl_fps)

    side_layout.addWidget(grp_info)
    side_layout.addStretch()

    # Instructions
    nav_box = QFrame()
    nav_box.setStyleSheet("background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px;")
    vbox_nav = QVBoxLayout(nav_box)
    vbox_nav.setContentsMargins(4, 4, 4, 4)
    vbox_nav.setSpacing(4)
    lbl_help_title = QLabel("🖱 <b>3D Navigation Controls</b>")
    lbl_help_title.setStyleSheet("color: #0284c7; font-size: 11px;")
    vbox_nav.addWidget(lbl_help_title)
    vbox_nav.addWidget(QLabel("• <b>Left Drag:</b> Orbit / Rotate Camera"))
    vbox_nav.addWidget(QLabel("• <b>Middle / Shift+Left:</b> Pan 3D View"))
    vbox_nav.addWidget(QLabel("• <b>Wheel / Right Drag:</b> Smooth Zoom"))
    side_layout.addWidget(nav_box)

    return side_panel
