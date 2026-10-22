# -*- coding: utf-8 -*-
"""
GeoStudio - Measurement Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class MeasurementToolBar(QToolBar):
    """Measurement toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Measurement", parent or main_window)
        self.setObjectName("tb_measure")
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
            ("measure_dist", "Measure Distance", self.mw.set_measure_distance, "Measure Distance (Line)"),
            ("measure_area", "Measure Area", self.mw.set_measure_area, "Measure Area (Polygon)"),
            ("measure_angle", "Measure Angle", self.mw.set_measure_angle, "Measure Bearing & Angle"),
            ("coord_capture", "Coordinate Capture", self.mw.set_coord_capture, "Coordinate Capture (X, Y, Elevation)"),
        ]
        for icon_key, text, slot, tip in items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        lbl = QLabel("MEASUREMENT", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
