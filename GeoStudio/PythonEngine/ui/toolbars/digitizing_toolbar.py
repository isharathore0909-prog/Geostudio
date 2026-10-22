# -*- coding: utf-8 -*-
"""
GeoStudio - Digitizing Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QMenu
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class DigitizingToolBar(QToolBar):
    """Digitizing Toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Digitizing", parent or main_window)
        self.setObjectName("tb_digitizing")
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
            ("digitizer", "Toggle Editing", self.mw.toggle_editing, "Toggle Vector Editing (Ctrl+E)", "Ctrl+E"),
            ("add_point", "Add Point", lambda: self.mw.set_digitize_tool("point"), "Add Point Feature", None),
            ("add_line", "Add Line", lambda: self.mw.set_digitize_tool("line"), "Add Line Feature", None),
            ("add_poly", "Add Polygon", lambda: self.mw.set_digitize_tool("polygon"), "Add Polygon Feature", None),
            ("vertex_tool", "Vertex Tool", lambda: self.mw.set_digitize_tool("vertex"), "Vertex Node Editor Tool", None),
            ("split", "Split", self.mw.split_feature, "Split Selected Feature", None),
            ("merge", "Merge", self.mw.merge_features, "Merge Selected Features", None),
            ("delete", "Delete", self.mw.delete_selected, "Delete Selected Features (Delete)", "Delete"),
            ("move", "Move", lambda: self.mw.set_digitize_tool("move"), "Move Selected Feature", None),
            ("rotate", "Rotate", lambda: self.mw.set_digitize_tool("rotate"), "Rotate Selected Feature", None),
        ]
        for icon_key, text, slot, tip, shortcut in items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        # ── 2. Snapping Dropdown Button ────────────────────
        btn_snapping = QToolButton(container)
        btn_snapping.setIcon(get_icon("snapping"))
        btn_snapping.setText(" Snapping ▾")
        btn_snapping.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn_snapping.setPopupMode(QToolButton.InstantPopup)
        btn_snapping.setToolTip("Vector Snapping Configuration")

        snapping_menu = QMenu(btn_snapping)
        snapping_menu.addAction("☑ Enable Snapping", self.mw.toggle_snapping)
        snapping_menu.addAction("• Snap to Vertices", lambda: self.mw.set_snapping_mode("vertex"))
        snapping_menu.addAction("• Snap to Segments", lambda: self.mw.set_snapping_mode("segment"))
        snapping_menu.addAction("• Snap to Area", lambda: self.mw.set_snapping_mode("area"))
        btn_snapping.setMenu(snapping_menu)
        btn_row.addWidget(btn_snapping)

        layout.addLayout(btn_row)

        lbl = QLabel("DIGITIZING", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
