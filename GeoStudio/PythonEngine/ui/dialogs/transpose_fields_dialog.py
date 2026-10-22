# -*- coding: utf-8 -*-
"""
GeoStudio - Transpose / Pivot Fields Tool
Restructures wide attribute tables into long (normalized) format.

ArcGIS equivalent: Data Management → Fields → Transpose Fields

Wide table:
    CityID | Pop1990 | Pop2000 | Pop2010
     NYC   |  7.3M   |  8.0M   |  8.2M

→ Long table (after transpose):
    CityID | Year | Population
     NYC   | 1990 |    7.3M
     NYC   | 2000 |    8.0M
     NYC   | 2010 |    8.2M

Implementation uses pandas DataFrame.melt() internally, then writes the
result as a QGIS memory layer or GeoPackage.
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QGroupBox, QMessageBox, QFileDialog,
    QAbstractItemView, QSplitter, QWidget, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from resources.icons.icon_provider import get_icon

DIALOG_STYLE = """
QDialog {
    background: #ffffff;
    color: #0f172a;
    font-family: "Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 8px;
    font-weight: 600;
    padding: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    color: #334155;
}
QComboBox, QLineEdit {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 4px 8px;
}
QComboBox:focus, QLineEdit:focus { border-color: #2563eb; }
QListWidget {
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    background: #f8fafc;
}
QListWidget::item { padding: 4px 6px; border-radius: 3px; }
QListWidget::item:selected { background: #dbeafe; color: #1e40af; }
QListWidget::item:hover { background: #f1f5f9; }
QPushButton {
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover { background: #1d4ed8; }
QPushButton:pressed { background: #1e40af; }
QPushButton#secondaryBtn {
    background: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
}
QPushButton#secondaryBtn:hover { background: #e2e8f0; }
QPushButton#smallBtn {
    background: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
    padding: 4px 10px;
    font-size: 11px;
}
"""


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class TransposeWorker(QThread):
    """Background thread: reads QGIS layer → pandas melt → writes output."""

    finished = pyqtSignal(str)   # output path on success
    error    = pyqtSignal(str)   # error message on failure

    def __init__(self, layer, fields_to_transpose, attr_fields,
                 transposed_field_name, value_field_name, output_path):
        super().__init__()
        self.layer                = layer
        self.fields_to_transpose  = fields_to_transpose    # list of (field_name, alias)
        self.attr_fields          = attr_fields            # list of field names to keep
        self.transposed_field_name = transposed_field_name
        self.value_field_name      = value_field_name
        self.output_path           = output_path

    def run(self):
        try:
            import pandas as pd
            from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsProject
            from PyQt5.QtCore import QVariant

            layer = self.layer
            field_names   = [f[0] for f in self.fields_to_transpose]
            field_aliases = {f[0]: f[1] for f in self.fields_to_transpose}

            # --- Read layer into DataFrame ---
            rows = []
            for feat in layer.getFeatures():
                row = {}
                for attr_f in self.attr_fields:
                    row[attr_f] = feat[attr_f]
                for fn in field_names:
                    row[fn] = feat[fn]
                rows.append(row)

            if not rows:
                self.error.emit("Input layer has no features.")
                return

            df = pd.DataFrame(rows)

            # --- Melt (= Transpose Fields) ---
            df_long = df.melt(
                id_vars=self.attr_fields,
                value_vars=field_names,
                var_name=self.transposed_field_name,
                value_name=self.value_field_name
            )

            # Apply user-defined aliases to the transposed field column
            df_long[self.transposed_field_name] = df_long[self.transposed_field_name].map(
                lambda x: field_aliases.get(x, x)
            )

            # Ensure value column is string (matches ArcGIS behaviour)
            df_long[self.value_field_name] = df_long[self.value_field_name].astype(str)

            # --- Write output ---
            if self.output_path.endswith(".csv"):
                df_long.to_csv(self.output_path, index=False)
            else:
                # Write to GeoPackage via QGIS memory layer
                self._write_gpkg(df_long, layer)

            self.finished.emit(self.output_path)

        except ImportError:
            self.error.emit(
                "pandas is required for Transpose Fields.\n"
                "Install it via:  pip install pandas"
            )
        except Exception as e:
            self.error.emit(str(e))

    def _write_gpkg(self, df, source_layer):
        """Write DataFrame to GeoPackage using QGIS vector writer."""
        try:
            from qgis.core import (
                QgsVectorLayer, QgsField, QgsFeature, QgsVectorFileWriter,
                QgsProject, QgsWkbTypes
            )
            from PyQt5.QtCore import QVariant

            # Build memory layer schema
            fields_str = []
            for col in df.columns:
                fields_str.append(f"field={col}:string")
            uri = "NoGeometry?" + "&".join(fields_str)

            mem_layer = QgsVectorLayer(uri, "transposed_output", "memory")
            prov = mem_layer.dataProvider()

            # Add features
            feats = []
            for _, row in df.iterrows():
                feat = QgsFeature(mem_layer.fields())
                for col in df.columns:
                    val = row[col]
                    feat.setAttribute(col, str(val) if val is not None else None)
                feats.append(feat)
            prov.addFeatures(feats)

            # Save to GeoPackage
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.fileEncoding = "utf-8"
            error, msg = QgsVectorFileWriter.writeAsVectorFormatV3(
                mem_layer, self.output_path, QgsProject.instance().transformContext(), options
            )
            if error != QgsVectorFileWriter.NoError:
                raise RuntimeError(f"Write error {error}: {msg}")

        except Exception as e:
            raise RuntimeError(f"Could not write GeoPackage: {e}")


# ---------------------------------------------------------------------------
# Main Dialog
# ---------------------------------------------------------------------------

class TransposeFieldsDialog(QDialog):
    """
    ArcGIS-style Transpose Fields geoprocessing dialog.

    Parameters exposed:
    - Input Layer (any vector layer)
    - Fields to Transpose (multi-select list)
    - Attribute Fields to keep (multi-select list)
    - Transposed Field name  (name of the 'column header' column in output)
    - Value Field name       (name of the 'data value' column in output)
    - Output path            (GeoPackage or CSV)
    """

    def __init__(self, map_canvas=None, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self._worker    = None

        self.setWindowTitle("Transpose / Pivot Fields")
        self.setWindowIcon(get_icon("transpose"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(540)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()
        self._populate_layers()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # --- Info banner ---
        info = QLabel(
            "Switches data stored in columns into rows (wide → long / normalized format).\n"
            "Equivalent to ArcGIS Pro: Data Management → Fields → Transpose Fields"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 5px;"
            "color: #1e40af; padding: 8px; font-size: 11px;"
        )
        layout.addWidget(info)

        # --- Input layer ---
        in_group = QGroupBox("Input Layer")
        in_form  = QFormLayout(in_group)
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
        in_form.addRow("Input Vector Layer:", self.layer_combo)
        layout.addWidget(in_group)

        # --- Field lists ---
        fields_group = QGroupBox("Field Selection")
        fields_layout = QHBoxLayout(fields_group)

        # Left: Available fields
        left = QVBoxLayout()
        left.addWidget(QLabel("Available Fields:"))
        self.avail_list = QListWidget()
        self.avail_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        left.addWidget(self.avail_list)
        fields_layout.addLayout(left)

        # Center: arrow buttons
        center = QVBoxLayout()
        center.setAlignment(Qt.AlignVCenter)
        center.addStretch()
        self.btn_add_transpose = QPushButton("⇒\nTranspose")
        self.btn_add_transpose.setObjectName("smallBtn")
        self.btn_add_transpose.setFixedWidth(80)
        self.btn_add_transpose.setToolTip("Add to 'Fields to Transpose'")
        self.btn_add_transpose.clicked.connect(self._add_to_transpose)

        self.btn_add_attr = QPushButton("⇒\nKeep")
        self.btn_add_attr.setObjectName("smallBtn")
        self.btn_add_attr.setFixedWidth(80)
        self.btn_add_attr.setToolTip("Add to 'Attribute Fields to keep'")
        self.btn_add_attr.clicked.connect(self._add_to_attr)

        self.btn_remove = QPushButton("⇐\nRemove")
        self.btn_remove.setObjectName("smallBtn")
        self.btn_remove.setFixedWidth(80)
        self.btn_remove.clicked.connect(self._remove_selected)

        center.addWidget(self.btn_add_transpose)
        center.addSpacing(4)
        center.addWidget(self.btn_add_attr)
        center.addSpacing(4)
        center.addWidget(self.btn_remove)
        center.addStretch()
        fields_layout.addLayout(center)

        # Right: two target lists stacked
        right = QVBoxLayout()
        right.addWidget(QLabel("Fields to Transpose (pivot):"))
        self.transpose_list = QListWidget()
        self.transpose_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.transpose_list.setToolTip("These field names become row values in the output")
        right.addWidget(self.transpose_list)

        right.addWidget(QLabel("Attribute Fields to Keep (id vars):"))
        self.attr_list = QListWidget()
        self.attr_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.attr_list.setToolTip("These fields are preserved as-is in every output row")
        right.addWidget(self.attr_list)
        fields_layout.addLayout(right)

        layout.addWidget(fields_group)

        # --- Output column names ---
        names_group = QGroupBox("Output Column Names")
        names_form  = QFormLayout(names_group)

        self.transposed_field_name = QLineEdit("Attribute")
        self.transposed_field_name.setToolTip(
            "Name for the new column that holds the original field names"
        )
        names_form.addRow("Transposed Field Name:", self.transposed_field_name)

        self.value_field_name = QLineEdit("Value")
        self.value_field_name.setToolTip(
            "Name for the new column that holds the corresponding data values"
        )
        names_form.addRow("Value Field Name:", self.value_field_name)
        layout.addWidget(names_group)

        # --- Output path ---
        out_group = QGroupBox("Output")
        out_form  = QFormLayout(out_group)
        path_row  = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Click Browse… to choose output path")
        btn_browse = QPushButton("Browse…")
        btn_browse.setObjectName("smallBtn")
        btn_browse.clicked.connect(self._browse_output)
        path_row.addWidget(self.output_path_edit, 1)
        path_row.addWidget(btn_browse)
        out_form.addRow("Output File:", path_row)
        layout.addWidget(out_group)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # --- Status ---
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #16a34a; font-size: 11px;")
        layout.addWidget(self.status_label)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_run = QPushButton("▶ Run Transpose Fields")
        btn_run.clicked.connect(self._run)
        btn_close = QPushButton("Close")
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(btn_run)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _populate_layers(self):
        self.layer_combo.clear()
        try:
            from qgis.core import QgsProject, QgsVectorLayer
            layers = [
                l for l in QgsProject.instance().mapLayers().values()
                if isinstance(l, QgsVectorLayer)
            ]
            for layer in layers:
                self.layer_combo.addItem(f"🗂  {layer.name()}", layer.id())
        except ImportError:
            self.layer_combo.addItem("(QGIS not available)", None)

    def _get_layer(self):
        try:
            from qgis.core import QgsProject
            lid = self.layer_combo.currentData()
            return QgsProject.instance().mapLayer(lid) if lid else None
        except ImportError:
            return None

    def _on_layer_changed(self):
        """Populate the available fields list when the input layer changes."""
        self.avail_list.clear()
        self.transpose_list.clear()
        self.attr_list.clear()
        layer = self._get_layer()
        if not layer:
            return
        for field in layer.fields():
            name = field.name()
            if name.lower() in ("fid", "ogc_fid"):
                continue
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            self.avail_list.addItem(item)

    def _add_to_transpose(self):
        for item in self.avail_list.selectedItems():
            name = item.data(Qt.UserRole)
            if not self._in_list(self.transpose_list, name) and \
               not self._in_list(self.attr_list, name):
                new = QListWidgetItem(f"📊 {name}")
                new.setData(Qt.UserRole, name)
                self.transpose_list.addItem(new)

    def _add_to_attr(self):
        for item in self.avail_list.selectedItems():
            name = item.data(Qt.UserRole)
            if not self._in_list(self.transpose_list, name) and \
               not self._in_list(self.attr_list, name):
                new = QListWidgetItem(f"🔑 {name}")
                new.setData(Qt.UserRole, name)
                self.attr_list.addItem(new)

    def _remove_selected(self):
        for lst in (self.transpose_list, self.attr_list):
            for item in lst.selectedItems():
                lst.takeItem(lst.row(item))

    @staticmethod
    def _in_list(listwidget, name: str) -> bool:
        for i in range(listwidget.count()):
            if listwidget.item(i).data(Qt.UserRole) == name:
                return True
        return False

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Transposed Table",
            os.path.expanduser("~/transposed_output.gpkg"),
            "GeoPackage (*.gpkg);;CSV (*.csv);;All Files (*)"
        )
        if path:
            self.output_path_edit.setText(path)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _run(self):
        # Validate
        layer = self._get_layer()
        if not layer:
            QMessageBox.warning(self, "Transpose Fields", "Please select a valid vector layer.")
            return

        fields_to_transpose = [
            (self.transpose_list.item(i).data(Qt.UserRole),
             self.transpose_list.item(i).data(Qt.UserRole))  # (field, alias=same)
            for i in range(self.transpose_list.count())
        ]
        if not fields_to_transpose:
            QMessageBox.warning(self, "Transpose Fields",
                                "Please add at least one field to the 'Fields to Transpose' list.")
            return

        attr_fields = [
            self.attr_list.item(i).data(Qt.UserRole)
            for i in range(self.attr_list.count())
        ]

        transposed_name = self.transposed_field_name.text().strip() or "Attribute"
        value_name      = self.value_field_name.text().strip() or "Value"

        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Transpose Fields",
                                "Please specify an output file path.")
            return

        # Show progress
        self.progress.setVisible(True)
        self.status_label.setText("Running…")
        self.status_label.setStyleSheet("color: #1d4ed8; font-size: 11px;")

        self._worker = TransposeWorker(
            layer=layer,
            fields_to_transpose=fields_to_transpose,
            attr_fields=attr_fields,
            transposed_field_name=transposed_name,
            value_field_name=value_name,
            output_path=output_path
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, path: str):
        self.progress.setVisible(False)
        self.status_label.setText(f"✓ Output saved to: {path}")
        self.status_label.setStyleSheet("color: #16a34a; font-size: 11px;")

        # Offer to load the result as a QGIS layer
        reply = QMessageBox.question(
            self, "Transpose Fields — Complete",
            f"Transposed table written to:\n{path}\n\nLoad it into the map?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._load_result(path)

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.status_label.setText(f"✗ Error: {msg}")
        self.status_label.setStyleSheet("color: #dc2626; font-size: 11px;")
        QMessageBox.critical(self, "Transpose Fields — Error", msg)

    def _load_result(self, path: str):
        try:
            from qgis.core import QgsVectorLayer, QgsProject
            name = os.path.splitext(os.path.basename(path))[0]
            layer = QgsVectorLayer(path, name, "ogr")
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                if self.map_canvas:
                    self.map_canvas.refresh_canvas()
        except Exception as e:
            QMessageBox.warning(self, "Load Result", f"Could not load layer: {e}")
