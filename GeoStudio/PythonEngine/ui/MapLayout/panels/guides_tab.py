# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Guides Tab
Controls layout guide markers, adding/removing horizontal & vertical guide lines,
guide visibility and snapping.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from qgis.core import (
    QgsLayoutGuide, QgsLayoutMeasurement, QgsUnitTypes
)


class GuidesTab(QWidget):
    """Guides manager tab for adding and configuring horizontal & vertical guides."""

    def __init__(self, designer, parent=None):
        super().__init__(parent)
        self.designer = designer
        self._build_ui()
        self._refresh_guides_table()

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(6)

        lbl = QLabel("Layout Guides (mm)")
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        vbox.addWidget(lbl)

        # Checkboxes for guides visibility & snapping
        h_chk = QHBoxLayout()
        self.chk_show_guides = QCheckBox("Show Guides")
        self.chk_show_guides.setChecked(True)
        self.chk_show_guides.toggled.connect(self._on_toggle_show_guides)
        h_chk.addWidget(self.chk_show_guides)

        self.chk_snap_guides = QCheckBox("Snap to Guides")
        self.chk_snap_guides.setChecked(True)
        self.chk_snap_guides.toggled.connect(self._on_toggle_snap_guides)
        h_chk.addWidget(self.chk_snap_guides)
        vbox.addLayout(h_chk)

        self.table_guides = QTableWidget(0, 2)
        self.table_guides.setHorizontalHeaderLabels(["Orientation", "Position (mm)"])
        self.table_guides.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_guides.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_guides.setStyleSheet("background: white; border: 1px solid #cbd5e1;")
        self.table_guides.itemChanged.connect(self._on_guide_cell_changed)
        vbox.addWidget(self.table_guides, 1)

        h_ctrl = QHBoxLayout()
        self.btn_add_h = QPushButton("+ Horizontal")
        self.btn_add_h.clicked.connect(self._add_horizontal_guide)
        h_ctrl.addWidget(self.btn_add_h)

        self.btn_add_v = QPushButton("+ Vertical")
        self.btn_add_v.clicked.connect(self._add_vertical_guide)
        h_ctrl.addWidget(self.btn_add_v)

        self.btn_del = QPushButton("Delete")
        self.btn_del.clicked.connect(self._delete_selected_guide)
        h_ctrl.addWidget(self.btn_del)

        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self._clear_guides)
        h_ctrl.addWidget(self.btn_clear)

        vbox.addLayout(h_ctrl)

    def _on_toggle_show_guides(self, checked):
        if self.designer.layout and hasattr(self.designer.layout, "guides"):
            self.designer.layout.guides().setVisible(checked)
            self.designer.view.update()

    def _on_toggle_snap_guides(self, checked):
        if self.designer.layout and hasattr(self.designer.layout, "snapper"):
            self.designer.layout.snapper().setSnapToGuides(checked)

    def _refresh_guides_table(self):
        if not self.designer.layout or not hasattr(self.designer.layout, "guides"):
            return
        self.table_guides.blockSignals(True)
        self.table_guides.setRowCount(0)
        guides = self.designer.layout.guides().guides()
        for g in guides:
            row = self.table_guides.rowCount()
            self.table_guides.insertRow(row)
            orient_str = "Horizontal" if g.orientation() == Qt.Horizontal else "Vertical"
            self.table_guides.setItem(row, 0, QTableWidgetItem(orient_str))
            pos_val = round(g.layoutPosition(), 2)
            self.table_guides.setItem(row, 1, QTableWidgetItem(str(pos_val)))
        self.table_guides.blockSignals(False)

    def _add_horizontal_guide(self):
        if not self.designer.layout:
            return
        pages = self.designer.layout.pageCollection().pages()
        if not pages:
            return
        page = pages[0]
        pos = round(page.pageSize().height() / 2.0, 1)
        guide = QgsLayoutGuide(Qt.Horizontal, QgsLayoutMeasurement(pos, QgsUnitTypes.LayoutMillimeters), page)
        self.designer.layout.guides().addGuide(guide)
        self.designer.view.update()
        self._refresh_guides_table()

    def _add_vertical_guide(self):
        if not self.designer.layout:
            return
        pages = self.designer.layout.pageCollection().pages()
        if not pages:
            return
        page = pages[0]
        pos = round(page.pageSize().width() / 2.0, 1)
        guide = QgsLayoutGuide(Qt.Vertical, QgsLayoutMeasurement(pos, QgsUnitTypes.LayoutMillimeters), page)
        self.designer.layout.guides().addGuide(guide)
        self.designer.view.update()
        self._refresh_guides_table()

    def _delete_selected_guide(self):
        row = self.table_guides.currentRow()
        if row < 0 or not self.designer.layout:
            return
        guides = list(self.designer.layout.guides().guides())
        if row < len(guides):
            self.designer.layout.guides().removeGuide(guides[row])
            self.designer.view.update()
            self._refresh_guides_table()

    def _clear_guides(self):
        if self.designer.layout and hasattr(self.designer.layout, "guides"):
            self.designer.layout.guides().clear()
            self.designer.view.update()
            self._refresh_guides_table()

    def _on_guide_cell_changed(self, item):
        row = item.row()
        if row < 0 or not self.designer.layout:
            return
        try:
            val = float(self.table_guides.item(row, 1).text())
            guides = list(self.designer.layout.guides().guides())
            if row < len(guides):
                self.designer.layout.guides().setGuideLayoutPosition(guides[row], val)
                self.designer.view.update()
        except ValueError:
            pass


__all__ = ["GuidesTab"]
