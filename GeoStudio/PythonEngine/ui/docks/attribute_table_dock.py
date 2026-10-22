# -*- coding: utf-8 -*-
"""GeoStudio - Attribute Table Dock (bottom panel)."""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QLabel, QPushButton,
    QLineEdit, QComboBox, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


class AttributeTableDock(QDockWidget):
    """Bottom dock showing the attribute table of the active vector layer."""

    def __init__(self, parent=None):
        super().__init__("📊 Attribute Table", parent)
        self.setObjectName("attr_table_dock")
        self.setMinimumHeight(200)
        self.setMaximumHeight(400)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self._current_layer = None
        self._build_ui()

    def _build_ui(self):
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget { background: #ffffff; color: #0f172a; font-family: "Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif; }
            QTableWidget { background: #ffffff; color: #0f172a; gridline-color: #e2e8f0;
                           border: 1px solid #e2e8f0; font-size: 11px; border-radius: 5px; }
            QTableWidget::item { padding: 4px 6px; }
            QTableWidget::item:selected { background: #e2e8f0; color: #0f172a; font-weight: 600; }
            QHeaderView::section { background: #f8fafc; color: #475569; border: none;
                                   border-bottom: 1px solid #cbd5e1; border-right: 1px solid #e2e8f0;
                                   padding: 5px 8px; font-weight: 600; font-size: 11px; }
            QPushButton { background: #ffffff; color: #334155; border: 1px solid #cbd5e1;
                          border-radius: 5px; padding: 4px 10px; font-size: 11px; font-weight: 600; }
            QPushButton:hover { background: #f1f5f9; color: #0f172a; border-color: #94a3b8; }
            QLineEdit { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                        border-radius: 5px; padding: 4px 8px; font-size: 11px; }
            QLineEdit:focus { border: 1.5px solid #0f172a; }
            QLabel { color: #475569; font-size: 11px; }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Toolbar row
        toolbar = QHBoxLayout()
        self.layer_label = QLabel("No layer selected")
        self.layer_label.setStyleSheet("color: #0f172a; font-weight: bold; font-size: 11px; padding: 2px 4px;")
        toolbar.addWidget(self.layer_label)
        toolbar.addStretch()

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("🔍 Filter rows...")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setMaximumWidth(220)
        self.filter_edit.textChanged.connect(self._filter_rows)
        toolbar.addWidget(self.filter_edit)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._refresh_table)
        toolbar.addWidget(btn_refresh)

        btn_export = QPushButton("📋 Copy Table")
        btn_export.clicked.connect(self._copy_selection)
        toolbar.addWidget(btn_export)

        self.feature_count_label = QLabel("0 features")
        self.feature_count_label.setStyleSheet("background: #f1f5f9; color: #0f172a; font-weight: 700; font-size: 10px; border-radius: 4px; padding: 3px 8px; border: 1px solid #cbd5e1;")
        toolbar.addWidget(self.feature_count_label)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.setStyleSheet("alternate-background-color: #f8fafc;")
        layout.addWidget(self.table)

        widget.setLayout(layout)
        self.setWidget(widget)

    def load_active_layer(self, layer=None):
        self._current_layer = layer
        self._refresh_table()

    def _refresh_table(self):
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        layer = self._current_layer
        if not layer:
            self.layer_label.setText("No layer selected")
            return

        try:
            from qgis.core import QgsMapLayer
            if layer.type() != QgsMapLayer.VectorLayer:
                self.layer_label.setText(f"⚠ '{layer.name()}' is a raster layer")
                return

            self.layer_label.setText(f"🗂  {layer.name()}")
            fields = layer.fields()
            field_names = [f.name() for f in fields]
            features = list(layer.getFeatures())

            self.table.setColumnCount(len(field_names))
            self.table.setHorizontalHeaderLabels(field_names)
            self.table.setRowCount(len(features))
            self.feature_count_label.setText(f"{len(features):,} features")

            for row, feat in enumerate(features):
                for col, fname in enumerate(field_names):
                    val = feat[fname]
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    self.table.setItem(row, col, item)

            self.table.resizeColumnsToContents()
        except Exception as e:
            self.layer_label.setText(f"Error: {e}")

    def _filter_rows(self, text):
        for row in range(self.table.rowCount()):
            row_visible = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    row_visible = True
                    break
            self.table.setRowHidden(row, not row_visible)

    def _copy_selection(self):
        from PyQt5.QtWidgets import QApplication
        rows = sorted(set(i.row() for i in self.table.selectedItems()))
        cols = list(range(self.table.columnCount()))
        lines = []
        headers = [self.table.horizontalHeaderItem(c).text() for c in cols]
        lines.append("\t".join(headers))
        for row in rows:
            line = []
            for col in cols:
                item = self.table.item(row, col)
                line.append(item.text() if item else "")
            lines.append("\t".join(line))
        QApplication.clipboard().setText("\n".join(lines))
