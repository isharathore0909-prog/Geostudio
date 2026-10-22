# -*- coding: utf-8 -*-
"""
GeoStudio - Project / File Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class ProjectToolBar(QToolBar):
    """File and Project management toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Project", parent or main_window)
        self.setObjectName("tb_file")
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
            ("new_project", "New Project", self.mw.new_project, "New Project (Ctrl+N)", "Ctrl+N"),
            ("open_project", "Open Project", self.mw.open_project, "Open Project (Ctrl+O)", "Ctrl+O"),
            ("save_project", "Save Project", self.mw.save_project, "Save Project (Ctrl+S)", "Ctrl+S"),
            ("save_project_as", "Save As", self.mw.save_project_as, "Save Project As (Ctrl+Shift+S)", "Ctrl+Shift+S"),
            ("print_map", "Print / Export", self.mw.print_map, "Print / Export Map Layout (Ctrl+P)", "Ctrl+P"),
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

        lbl = QLabel("PROJECT", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
