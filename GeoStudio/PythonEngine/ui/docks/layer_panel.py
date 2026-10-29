# -*- coding: utf-8 -*-
"""GeoStudio - Layer Panel (left sidebar, like QGIS / Global Mapper Layers panel)."""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush

from core.elevation_styler import ElevationStyler, ELEVATION_PRESETS
from ui.layers.layer_loader import LayerLoader
from ui.layers.layer_context_menu import LayerContextMenuHandler


LAYER_STYLE = """
    QWidget { background: #ffffff; color: #0f172a; font-family: "Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif; font-size: 12px; }
    QTreeWidget {
        background: #ffffff; color: #0f172a;
        border: 1px solid #e2e8f0; font-size: 12px; border-radius: 5px;
        outline: none;
        selection-background-color: #e2e8f0;
        selection-color: #0f172a;
    }
    QTreeWidget::branch {
        background: transparent;
    }
    QTreeWidget::branch:selected {
        background: #e2e8f0;
    }
    QTreeWidget::branch:hover:!selected {
        background: #f8fafc;
    }
    QTreeWidget::item { padding: 5px 6px; border-radius: 4px; }
    QTreeWidget::item:selected { background: #e2e8f0; color: #0f172a; font-weight: 600; }
    QTreeWidget::item:hover:!selected { background: #f8fafc; }
    QPushButton {
        background: #ffffff; color: #334155; border: 1px solid #cbd5e1;
        border-radius: 5px; padding: 5px 8px; font-size: 11px; font-weight: 600;
    }
    QPushButton:hover { background: #f1f5f9; color: #0f172a; border-color: #94a3b8; }
    QPushButton:pressed { background: #e2e8f0; }
    QLineEdit { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1;
                border-radius: 5px; padding: 5px 8px; font-size: 11px; }
    QLineEdit:focus { border: 1.5px solid #0f172a; }
    QLabel { color: #475569; font-size: 11px; }
"""


class LayerPanelWidget(QWidget):
    """
    Left-side layer panel — shows all project layers with:
    - Visibility toggle (checkbox)
    - Layer icons (vector / raster / DEM elevation)
    - Right-click context menu with Global Mapper & ArcGIS style DEM/Raster tools
    - Search filtering
    """

    active_layer_changed = pyqtSignal(object)

    def __init__(self, map_canvas, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self.setStyleSheet(LAYER_STYLE)
        self._init_ui()
        self._connect_project_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header
        header_box = QHBoxLayout()
        header = QLabel("🗂  LAYERS")
        header.setStyleSheet("color: #0f172a; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; padding: 2px 2px;")
        self.count_badge = QLabel("0")
        self.count_badge.setStyleSheet("background: #f1f5f9; color: #0f172a; font-weight: 700; font-size: 10px; border-radius: 8px; padding: 1px 7px; border: 1px solid #cbd5e1;")
        header_box.addWidget(header)
        header_box.addStretch()
        header_box.addWidget(self.count_badge)
        layout.addLayout(header_box)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Search layers...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter_layers)
        layout.addWidget(self.search)

        # Layer tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)

        # Quick-add buttons
        btn_row = QHBoxLayout()
        btn_v = QPushButton("📂 Vector")
        btn_v.clicked.connect(self._quick_add_vector)
        btn_r = QPushButton("🏔 Raster / DEM")
        btn_r.clicked.connect(self._quick_add_raster)
        btn_row.addWidget(btn_v)
        btn_row.addWidget(btn_r)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _connect_project_signals(self):
        try:
            from qgis.core import QgsProject
            QgsProject.instance().layersAdded.connect(self.refresh)
            QgsProject.instance().layersRemoved.connect(self.refresh)
        except ImportError:
            pass

    def refresh(self, *args):
        self.tree.blockSignals(True)
        self.tree.clear()
        try:
            from qgis.core import QgsProject, QgsVectorLayer
            layers = list(QgsProject.instance().mapLayers().values())
            for layer in reversed(layers):
                if getattr(layer, '_is_sub_relief_layer', False) or "[3D Hillshade]" in layer.name():
                    continue

                is_vector = isinstance(layer, QgsVectorLayer)
                is_point_cloud = "PointCloud" in type(layer).__name__
                is_lidar_raster = bool(layer.customProperty("is_lidar_layer", False))
                is_dem = (not is_vector) and (not is_point_cloud) and (not is_lidar_raster) and ElevationStyler.is_dem_or_elevation(layer)

                clean_name = layer.name().replace(" [DEM]", "").replace(" [3D Relief]", "").replace(" [3D Hillshade]", "").replace(" [LiDAR]", "").strip()
                if is_vector:
                    icon = "🗂"
                    label_text = f"  {icon}  {clean_name}"
                elif is_point_cloud or is_lidar_raster:
                    icon = "☁"
                    label_text = f"  {icon}  {clean_name} [LiDAR]"
                elif is_dem:
                    icon = "🏔"
                    label_text = f"  {icon}  {clean_name} [DEM]"
                else:
                    icon = "🗺"
                    label_text = f"  {icon}  {clean_name}"

                item = QTreeWidgetItem([label_text])
                item.setData(0, Qt.UserRole, layer.id())
                item.setCheckState(0, Qt.Checked if layer.isValid() else Qt.Unchecked)

                if is_vector:
                    item.setForeground(0, QBrush(QColor("#15803d")))
                elif is_point_cloud or is_lidar_raster:
                    item.setForeground(0, QBrush(QColor("#0284c7")))
                elif is_dem:
                    item.setForeground(0, QBrush(QColor("#b45309")))
                else:
                    item.setForeground(0, QBrush(QColor("#0369a1")))

                self.tree.addTopLevelItem(item)

            if self.tree.topLevelItemCount() > 0:
                self.tree.setCurrentItem(self.tree.topLevelItem(0))
            if hasattr(self, 'count_badge'):
                self.count_badge.setText(str(self.tree.topLevelItemCount()))
        except ImportError:
            pass
        self.tree.blockSignals(False)

    def _filter_layers(self, text):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setHidden(text.lower() not in item.text(0).lower())

    def get_active_layer(self):
        item = self.tree.currentItem()
        if item:
            return self._layer_from_item(item)
        return None

    def _on_item_clicked(self, item, col):
        layer = self._layer_from_item(item)
        if layer:
            self.active_layer_changed.emit(layer)
            if self.map_canvas and hasattr(self.map_canvas, "update_elevation_legend"):
                self.map_canvas.update_elevation_legend(layer)

    def _on_item_double_clicked(self, item, col):
        layer = self._layer_from_item(item)
        if layer:
            self.active_layer_changed.emit(layer)
            self.map_canvas.zoom_to_layer(layer)

    def _on_item_changed(self, item, col):
        """Toggle layer visibility when checkbox is toggled."""
        layer = self._layer_from_item(item)
        if layer:
            try:
                from qgis.core import QgsProject
                root = QgsProject.instance().layerTreeRoot()
                node = root.findLayer(layer.id())
                if node:
                    node.setItemVisibilityChecked(item.checkState(0) == Qt.Checked)
                linked_id = getattr(layer, "_linked_hs_layer_id", None)
                if linked_id:
                    hs_node = root.findLayer(linked_id)
                    if hs_node:
                        hs_node.setItemVisibilityChecked(item.checkState(0) == Qt.Checked)
                self.map_canvas.refresh_canvas()
            except Exception:
                pass

    def _show_context_menu(self, pos):
        LayerContextMenuHandler.show_context_menu(self, pos)

    def _quick_add_vector(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Vector Layer", "", "Shapefile (*.shp);;GeoPackage (*.gpkg);;GeoJSON (*.geojson);;All Files (*.*)")
        if path:
            self.load_vector(path)

    def _quick_add_raster(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Elevation DEM / Raster / Point Cloud", "", "All Supported (*.tif *.tiff *.dem *.dtm *.dsm *.las *.laz *.copc.laz *.asc *.xyz);;GeoTIFF (*.tif *.tiff);;Point Cloud (*.las *.laz *.copc.laz);;All Files (*.*)")
        if path:
            self.load_raster(path)

    def load_vector(self, path):
        LayerLoader.load_vector(self, path)

    def load_raster(self, path):
        LayerLoader.load_raster(self, path)

    def load_point_cloud(self, path):
        LayerLoader.load_point_cloud(self, path)

    def load_osm_basemap(self):
        pass

    def load_csv(self, path, x_field="longitude", y_field="latitude"):
        LayerLoader.load_csv(self, path, x_field, y_field)

    def _layer_from_item(self, item):
        if not item:
            return None
        layer_id = item.data(0, Qt.UserRole)
        if layer_id:
            try:
                from qgis.core import QgsProject
                return QgsProject.instance().mapLayer(layer_id)
            except ImportError:
                pass
        return None

    def remove_active_layer(self):
        layer = self.get_active_layer()
        if layer:
            LayerContextMenuHandler.remove_layer(self, layer)

    def show_layer_properties(self):
        layer = self.get_active_layer()
        if layer:
            LayerContextMenuHandler.show_props(self, layer)

    def apply_elevation_preset(self, layer, preset_key):
        LayerContextMenuHandler.apply_elevation_preset(self, layer, preset_key)

    def _apply_elevation_preset(self, layer, preset_key):
        LayerContextMenuHandler.apply_elevation_preset(self, layer, preset_key)

    def open_dem_dialog(self, layer=None):
        LayerContextMenuHandler.open_dem_dialog(self, layer)
