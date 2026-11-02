# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Manager Dialog
Exact match to professional GIS layout manager:
- Searchable list of project layouts
- Action buttons: Show, Duplicate, Remove, Rename
- New from Template:
    * Preset dropdown (Empty, A4-A0, Current Map View, Survey, Thematic, Report)
    * Template file selector with browse [...]
    * Open template directory: [User] [Default]
- Close and Help buttons
"""

import os
import subprocess
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QComboBox,
    QMessageBox, QInputDialog, QFileDialog, QWidget, QFrame
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices

from qgis.core import QgsProject, QgsPrintLayout
from resources.icons.icon_provider import get_icon
from ..services.template_service import create_layout_from_template


class LayoutManagerDialog(QDialog):
    """Professional Layout Manager dialog for GeoStudio."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.mw = main_window
        self.setWindowTitle("Layout Manager")
        self.resize(520, 480)
        self.setMinimumSize(480, 420)
        self.setWindowModality(Qt.ApplicationModal)

        self._user_template_dir = os.path.join(os.path.expanduser("~"), ".geostudio", "templates")
        os.makedirs(self._user_template_dir, exist_ok=True)
        self._default_template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        os.makedirs(self._default_template_dir, exist_ok=True)

        self._init_ui()
        self._refresh_layout_list()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # 1. Search Box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_list)
        root.addWidget(self.search_edit)

        # 2. Existing Layouts List
        self.list_layouts = QListWidget()
        self.list_layouts.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 3px;
                font-size: 12px;
            }
            QListWidget::item { padding: 6px 10px; }
            QListWidget::item:selected { background: #e2e8f0; color: #0f172a; font-weight: 600; }
        """)
        self.list_layouts.itemDoubleClicked.connect(self._on_show_layout)
        root.addWidget(self.list_layouts, 1)

        # 3. Action Buttons underneath list: [ Show ] [ Duplicate... ] [ Remove... ] [ Rename... ]
        h_actions = QHBoxLayout()
        h_actions.setSpacing(6)

        self.btn_show = QPushButton("Show")
        self.btn_show.clicked.connect(self._on_show_layout)
        h_actions.addWidget(self.btn_show)

        self.btn_duplicate = QPushButton("Duplicate...")
        self.btn_duplicate.clicked.connect(self._on_duplicate_layout)
        h_actions.addWidget(self.btn_duplicate)

        self.btn_remove = QPushButton("Remove...")
        self.btn_remove.clicked.connect(self._on_remove_layout)
        h_actions.addWidget(self.btn_remove)

        self.btn_rename = QPushButton("Rename...")
        self.btn_rename.clicked.connect(self._on_rename_layout)
        h_actions.addWidget(self.btn_rename)

        root.addLayout(h_actions)

        # 4. Section Header: New from Template
        lbl_template_header = QLabel("▼  <b>New from Template</b>")
        lbl_template_header.setStyleSheet("color: #0f172a; margin-top: 6px;")
        root.addWidget(lbl_template_header)

        # Template Selection Row
        h_tpl_row1 = QHBoxLayout()
        h_tpl_row1.setSpacing(6)

        self.combo_templates = QComboBox()
        self.combo_templates.addItems([
            "Empty Layout",
            "A4 Portrait",
            "A4 Landscape",
            "A3 Portrait",
            "A3 Landscape",
            "A2 Portrait",
            "A2 Landscape",
            "A1 Portrait",
            "A1 Landscape",
            "A0 Portrait",
            "A0 Landscape",
            "Current Map View",
            "Map Report",
            "Survey Map",
            "Thematic Map",
            "Custom User Template..."
        ])
        h_tpl_row1.addWidget(self.combo_templates, 1)

        self.btn_create = QPushButton("Create...")
        self.btn_create.setStyleSheet("font-weight: 600;")
        self.btn_create.clicked.connect(self._on_create_from_template)
        h_tpl_row1.addWidget(self.btn_create)
        root.addLayout(h_tpl_row1)

        # Template File Path Row
        h_tpl_row2 = QHBoxLayout()
        h_tpl_row2.setSpacing(6)

        self.txt_template_path = QLineEdit()
        self.txt_template_path.setPlaceholderText("Template file (.qpt)...")
        h_tpl_row2.addWidget(self.txt_template_path, 1)

        self.btn_browse = QPushButton("...")
        self.btn_browse.setMaximumWidth(36)
        self.btn_browse.clicked.connect(self._on_browse_template)
        h_tpl_row2.addWidget(self.btn_browse)
        root.addLayout(h_tpl_row2)

        # Open template directory row
        h_tpl_row3 = QHBoxLayout()
        h_tpl_row3.setSpacing(8)

        lbl_open_dir = QLabel("Open template directory")
        lbl_open_dir.setStyleSheet("color: #475569;")
        h_tpl_row3.addWidget(lbl_open_dir)

        self.btn_user_dir = QPushButton("User")
        self.btn_user_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._user_template_dir)))
        h_tpl_row3.addWidget(self.btn_user_dir)

        self.btn_default_dir = QPushButton("Default")
        self.btn_default_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._default_template_dir)))
        h_tpl_row3.addWidget(self.btn_default_dir)

        h_tpl_row3.addStretch()
        root.addLayout(h_tpl_row3)

        # Bottom Separator & Buttons
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e2e8f0; margin-top: 6px;")
        root.addWidget(line)

        h_bottom = QHBoxLayout()
        h_bottom.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        h_bottom.addWidget(self.btn_close)

        self.btn_help = QPushButton("Help")
        self.btn_help.clicked.connect(self._on_help)
        h_bottom.addWidget(self.btn_help)

        root.addLayout(h_bottom)

    def _refresh_layout_list(self):
        self.list_layouts.clear()
        mgr = QgsProject.instance().layoutManager()
        layouts = mgr.printLayouts()

        for l in layouts:
            name = l.name() or "Untitled Layout"
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, l)
            self.list_layouts.addItem(item)

        if self.list_layouts.count() > 0:
            self.list_layouts.setCurrentRow(0)

    def _filter_list(self, text: str):
        query = text.strip().lower()
        for i in range(self.list_layouts.count()):
            it = self.list_layouts.item(i)
            it.setHidden(query not in it.text().lower() if query else False)

    def _get_selected_layout(self):
        it = self.list_layouts.currentItem()
        if it:
            return it.data(Qt.UserRole)
        return None

    def _on_show_layout(self):
        layout = self._get_selected_layout()
        if not layout:
            QMessageBox.information(self, "Show Layout", "Please select a layout from the list.")
            return

        if hasattr(self.mw, "open_layout_designer"):
            self.designer = self.mw.open_layout_designer(layout)
        else:
            from ..components.designer_window import GeoStudioLayoutDesignerWindow
            self.designer = GeoStudioLayoutDesignerWindow(layout, main_window=self.mw, parent=self.mw)
            self.designer.show()
        self.accept()

    def _on_duplicate_layout(self):
        layout = self._get_selected_layout()
        if not layout:
            QMessageBox.information(self, "Duplicate", "Please select a layout to duplicate.")
            return

        default_name = f"{layout.name()} Copy"
        new_name, ok = QInputDialog.getText(self, "Duplicate Layout", "Enter new layout name:", text=default_name)
        if ok and new_name.strip():
            mgr = QgsProject.instance().layoutManager()
            dup = mgr.duplicateLayout(layout, new_name.strip())
            if dup:
                self._refresh_layout_list()
                QMessageBox.information(self, "Duplicate", f"Layout '{new_name.strip()}' created successfully.")
            else:
                QMessageBox.warning(self, "Duplicate", f"A layout named '{new_name.strip()}' already exists.")

    def _on_remove_layout(self):
        layout = self._get_selected_layout()
        if not layout:
            QMessageBox.information(self, "Remove", "Please select a layout to remove.")
            return

        confirm = QMessageBox.question(
            self, "Remove Layout",
            f"Are you sure you want to remove the layout '{layout.name()}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            mgr = QgsProject.instance().layoutManager()
            mgr.removeLayout(layout)
            self._refresh_layout_list()

    def _on_rename_layout(self):
        layout = self._get_selected_layout()
        if not layout:
            QMessageBox.information(self, "Rename", "Please select a layout to rename.")
            return

        new_name, ok = QInputDialog.getText(self, "Rename Layout", "Enter new layout name:", text=layout.name())
        if ok and new_name.strip() and new_name.strip() != layout.name():
            layout.setName(new_name.strip())
            self._refresh_layout_list()

    def _on_browse_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Print Layout Template",
            self._user_template_dir,
            "QGIS / GeoStudio Templates (*.qpt *.json);;All Files (*.*)"
        )
        if path:
            self.txt_template_path.setText(path)
            self.combo_templates.setCurrentText("Custom User Template...")

    def _on_create_from_template(self):
        tpl_name = self.combo_templates.currentText()
        default_name = tpl_name.replace("...", "").strip()
        if default_name == "Empty Layout":
            default_name = "Layout 1"

        new_name, ok = QInputDialog.getText(self, "New Layout", "Enter layout name:", text=default_name)
        if not ok or not new_name.strip():
            return

        name = new_name.strip()
        mgr = QgsProject.instance().layoutManager()

        # Check existing
        for existing in mgr.printLayouts():
            if existing.name().lower() == name.lower():
                QMessageBox.warning(self, "Duplicate Name", f"A layout named '{name}' already exists.")
                return

        custom_path = self.txt_template_path.text().strip()
        if tpl_name == "Custom User Template..." and custom_path and os.path.exists(custom_path):
            layout = QgsPrintLayout(QgsProject.instance())
            layout.setName(name)
            if custom_path.endswith(".qpt"):
                from qgis.PyQt.QtXml import QDomDocument
                doc = QDomDocument()
                with open(custom_path, "r", encoding="utf-8") as f:
                    doc.setContent(f.read())
                layout.loadFromTemplate(doc, QgsProject.instance())
            mgr.addLayout(layout)
        else:
            map_canvas = getattr(self.mw, "map_canvas", None)
            layout = create_layout_from_template(QgsProject.instance(), name, tpl_name, map_canvas=map_canvas)
            mgr.addLayout(layout)

        self._refresh_layout_list()

        # Launch designer
        if hasattr(self.mw, "open_layout_designer"):
            self.designer = self.mw.open_layout_designer(layout)
        else:
            from ..components.designer_window import GeoStudioLayoutDesignerWindow
            self.designer = GeoStudioLayoutDesignerWindow(layout, main_window=self.mw, parent=self.mw)
            self.designer.show()
        self.accept()

    def _on_help(self):
        QMessageBox.information(
            self, "GeoStudio Layout Manager",
            "<b>GeoStudio Layout Manager</b><br><br>"
            "• Select a layout and click <b>Show</b> to open it in the Layout Designer.<br>"
            "• Use <b>Duplicate...</b>, <b>Rename...</b>, or <b>Remove...</b> to manage existing layouts.<br>"
            "• Choose a template preset from the dropdown and click <b>Create...</b> to start a new publication map.<br>"
            "• All layouts are automatically saved inside your GeoStudio project."
        )


__all__ = ["LayoutManagerDialog"]
