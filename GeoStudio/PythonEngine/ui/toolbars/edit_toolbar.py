# -*- coding: utf-8 -*-
"""
GeoStudio - Edit & History Toolbar (Grouped with Title)
Dedicated Undo and Redo controls positioned next to Measurement.
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class EditToolBar(QToolBar):
    """Edit history toolbar with Undo / Redo group."""

    def __init__(self, main_window, parent=None):
        super().__init__("Edit", parent or main_window)
        self.setObjectName("tb_edit")
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
            ("undo", "Undo", self.mw.undo_action, "Undo Edit / Last Point (Ctrl+Z)", "Ctrl+Z"),
            ("redo", "Redo", self.mw.redo_action, "Redo Edit (Ctrl+Y)", "Ctrl+Y"),
        ]
        for icon_key, text, slot, tip, shortcut in items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            if shortcut:
                btn.setShortcut(shortcut)
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        lbl = QLabel("EDIT", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
