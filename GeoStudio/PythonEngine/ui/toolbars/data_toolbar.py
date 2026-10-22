# -*- coding: utf-8 -*-
"""
GeoStudio - Data Sources Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class DataSourcesToolBar(QToolBar):
    """Data source loading toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Data Sources", parent or main_window)
        self.setObjectName("tb_data")
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

        items = [
            ("add_vector", "Add Vector", self.mw.add_vector, "Add Vector Layer (Ctrl+Shift+V)", "Ctrl+Shift+V"),
            ("add_raster", "Add Raster", self.mw.add_raster, "Add Raster Layer (Ctrl+Shift+R)", "Ctrl+Shift+R"),
            ("add_csv", "Add CSV", self.mw.add_csv, "Add Delimited Text (CSV as Points)", None),
            ("add_wms", "Add WMS", self.mw.add_wms, "Add WMS / WMTS Basemap Layer", None),
            ("add_xyz", "Add XYZ", self.mw.add_xyz_basemap, "Add XYZ OpenStreetMap Basemap", None),
            ("browser_panel", "Browser Panel", self.mw.toggle_layer_dock, "Toggle Layers & Browser Panel", None),
        ]
        for icon_key, text, slot, tip, shortcut in items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        lbl = QLabel("DATA SOURCES", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
