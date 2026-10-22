# -*- coding: utf-8 -*-
"""
GeoStudio - Selection & Identify Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class SelectionToolBar(QToolBar):
    """Selection and identify toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Selection", parent or main_window)
        self.setObjectName("tb_selection")
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
            ("identify", "Identify", self.mw.set_identify_tool, "Identify Features (I)", "I"),
            ("select", "Select", self.mw.set_select_tool, "Select Features by Click", None),
            ("select_rect", "Select Rectangle", lambda: self.mw.set_select_mode("rectangle"), "Select Features by Rectangle", None),
            ("select_poly", "Select Polygon", lambda: self.mw.set_select_mode("polygon"), "Select Features by Polygon", None),
            ("select_radius", "Select Radius", lambda: self.mw.set_select_mode("radius"), "Select Features by Radius", None),
            ("clear_selection", "Clear Selection", self.mw.clear_selection, "Clear Selected Features", None),
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

        lbl = QLabel("SELECTION", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
