# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR / Point Cloud Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QMenu
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class LidarToolBar(QToolBar):
    """LiDAR / Point Cloud Toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("LiDAR", parent or main_window)
        self.setObjectName("tb_lidar")
        self.mw = main_window
        self._build_ui()

    def _build_ui(self):
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 1)
        layout.setSpacing(1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(2)

        # ── 1. Action Buttons ──────────────────────────────
        items = [
            ("load_las", "Load LAS/LAZ", self.mw.load_las_file, "Load LAS / LAZ Point Cloud File"),
            ("classify_ground", "Classify Ground", lambda: self.mw.run_lidar_auto_classification(), "Auto-Classify Ground & Vegetation (SMRF / HAG)"),
            ("classify_buildings", "Classify Buildings", lambda: self.mw.processing_dock.open_algorithm("lidar:classify_buildings"), "Classify Building Structures"),
            ("classify_veg", "Classify Vegetation", lambda: self.mw.processing_dock.open_algorithm("lidar:classify_veg"), "Classify Vegetation Canopy"),
            ("thin", "Thin", lambda: self.mw.processing_dock.open_algorithm("lidar:thinning"), "Point Density Decimation / Thinning"),
            ("clip", "Clip", lambda: self.mw.processing_dock.open_algorithm("lidar:clip"), "Clip Point Cloud to Polygon Extent"),
            ("view_3d", "Point Cloud 3D", self.mw.open_3d_viewer, "Interactive 3D Point Cloud View"),
        ]
        for icon_key, text, slot, tip in items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        # ── 2. Color By Dropdown Button ────────────────────
        btn_colorby = QToolButton(container)
        btn_colorby.setIcon(get_icon("control_center"))
        btn_colorby.setText(" Color By ▾")
        btn_colorby.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn_colorby.setPopupMode(QToolButton.InstantPopup)
        btn_colorby.setToolTip("Point Cloud Display Color Mode")

        colorby_menu = QMenu(btn_colorby)
        colorby_menu.addAction("Color Lidar by RGB/Elev", lambda: self.mw.set_lidar_color_mode("rgb_elev"))
        colorby_menu.addAction("Color Lidar by Elevation", lambda: self.mw.set_lidar_color_mode("elevation"))
        colorby_menu.addAction("Color Lidar by Intensity", lambda: self.mw.set_lidar_color_mode("intensity"))
        colorby_menu.addAction("Color Lidar by Classification", lambda: self.mw.set_lidar_color_mode("classification"))
        colorby_menu.addAction("Color Lidar by Return Number", lambda: self.mw.set_lidar_color_mode("return_num"))
        colorby_menu.addAction("Color Lidar by Height Above Ground", lambda: self.mw.set_lidar_color_mode("hag"))
        colorby_menu.addAction("Color Lidar by Scan Angle", lambda: self.mw.set_lidar_color_mode("scan_angle"))
        colorby_menu.addAction("Color Lidar by Point Source ID", lambda: self.mw.set_lidar_color_mode("point_source_id"))
        colorby_menu.addAction("Color Lidar by Source Layer", lambda: self.mw.set_lidar_color_mode("source_layer"))
        colorby_menu.addAction("Color Lidar by Segment", lambda: self.mw.set_lidar_color_mode("segment"))
        colorby_menu.addAction("Color Lidar by Point Index", lambda: self.mw.set_lidar_color_mode("point_index"))
        colorby_menu.addAction("Color Lidar as CIR (Color Infrared)", lambda: self.mw.set_lidar_color_mode("cir"))
        colorby_menu.addAction("Color Lidar using NDVI (Vegetation)", lambda: self.mw.set_lidar_color_mode("ndvi"))
        colorby_menu.addAction("Color Lidar using NDWI (Water)", lambda: self.mw.set_lidar_color_mode("ndwi"))
        colorby_menu.addAction("Color Lidar by Point Density", lambda: self.mw.set_lidar_color_mode("point_density"))
        colorby_menu.addAction("Color Lidar by Withheld Flag", lambda: self.mw.set_lidar_color_mode("withheld"))
        colorby_menu.addAction("Color Lidar by Key Point Flag", lambda: self.mw.set_lidar_color_mode("keypoint"))
        colorby_menu.addAction("Color Lidar by Overlap Flag", lambda: self.mw.set_lidar_color_mode("overlap"))
        colorby_menu.addAction("Color Lidar by Return Height Delta", lambda: self.mw.set_lidar_color_mode("return_delta"))
        colorby_menu.addSeparator()
        colorby_menu.addAction("⚡ Auto-Classify Ground & Canopy (SMRF)...", lambda: self.mw.run_lidar_auto_classification())
        btn_colorby.setMenu(colorby_menu)
        btn_row.addWidget(btn_colorby)

        layout.addLayout(btn_row)

        lbl = QLabel("LIDAR / POINT CLOUD", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
