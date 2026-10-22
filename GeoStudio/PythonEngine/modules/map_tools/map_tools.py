# -*- coding: utf-8 -*-
"""
GeoAnalytica - Map Tools Module
Measure area/distance, annotate/draw on canvas, coordinate picker,
feature info, bearing tool, and grid generation.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QComboBox, QGroupBox, QDoubleSpinBox, QSpinBox,
    QTextEdit, QMessageBox, QLineEdit, QRadioButton
)
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProject, QgsMapLayer, QgsPointXY, QgsWkbTypes
)
from qgis.gui import QgsRubberBand
from core.style import MODULE_STYLE
from .map_tool_operations import (
    CoordClickTool, format_coordinate_text, calculate_measurement, generate_grid_layer
)

STYLE = MODULE_STYLE


class MapToolsWidget(QWidget):
    """Map Tools: measure, coordinate picker, draw, grid, bearing, feature info."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.setStyleSheet(STYLE)
        self._current_tool = None
        self._rubber_band = None
        self._measure_points = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # --- Coordinate Picker ---
        coord_box = QGroupBox("Coordinate Picker")
        coord_layout = QVBoxLayout()
        self.coord_label = QLabel("Click the map to get coordinates")
        self.coord_label.setWordWrap(True)
        btn_pick = QPushButton("📍 Pick Coordinate from Map")
        btn_pick.setCheckable(True)
        btn_pick.clicked.connect(self._toggle_coord_tool)
        self.coord_pick_btn = btn_pick
        self.coord_output = QTextEdit()
        self.coord_output.setReadOnly(True)
        self.coord_output.setFixedHeight(80)
        coord_layout.addWidget(btn_pick)
        coord_layout.addWidget(self.coord_label)
        coord_layout.addWidget(self.coord_output)
        coord_box.setLayout(coord_layout)
        layout.addWidget(coord_box)

        # --- Measure Tool ---
        measure_box = QGroupBox("Measure Distance / Area")
        measure_layout = QVBoxLayout()

        mode_row = QHBoxLayout()
        self.measure_distance_rb = QRadioButton("Distance")
        self.measure_area_rb = QRadioButton("Area")
        self.measure_distance_rb.setChecked(True)
        mode_row.addWidget(self.measure_distance_rb)
        mode_row.addWidget(self.measure_area_rb)
        measure_layout.addLayout(mode_row)

        unit_form = QFormLayout()
        self.measure_unit = QComboBox()
        self.measure_unit.addItems(["Meters", "Kilometers", "Miles", "Feet", "Degrees"])
        unit_form.addRow("Units:", self.measure_unit)
        measure_layout.addLayout(unit_form)

        btn_start_measure = QPushButton("📏 Start Measuring (click points)")
        btn_start_measure.setCheckable(True)
        btn_start_measure.clicked.connect(self._toggle_measure)
        self.measure_btn = btn_start_measure

        btn_clear_measure = QPushButton("🗑 Clear Measurement")
        btn_clear_measure.clicked.connect(self._clear_measure)

        self.measure_result = QLabel("Result: --")
        self.measure_result.setStyleSheet("color: #16a34a; font-weight: bold; font-size: 11px;")

        measure_layout.addWidget(btn_start_measure)
        measure_layout.addWidget(btn_clear_measure)
        measure_layout.addWidget(self.measure_result)
        measure_box.setLayout(measure_layout)
        layout.addWidget(measure_box)

        # --- Quick Zoom ---
        zoom_box = QGroupBox("Navigate")
        zoom_layout = QVBoxLayout()
        btn_row1 = QHBoxLayout()
        btn_zoom_full = QPushButton("🌍 Zoom Full Extent")
        btn_zoom_full.setObjectName("grayBtn")
        btn_zoom_full.clicked.connect(lambda: self.canvas.zoomToFullExtent())
        btn_zoom_sel = QPushButton("🔍 Zoom to Selection")
        btn_zoom_sel.setObjectName("grayBtn")
        btn_zoom_sel.clicked.connect(self.zoom_to_selection)
        btn_row1.addWidget(btn_zoom_full)
        btn_row1.addWidget(btn_zoom_sel)
        zoom_layout.addLayout(btn_row1)

        # Zoom to coordinates
        coord_form = QFormLayout()
        self.goto_lon = QLineEdit(); self.goto_lon.setPlaceholderText("Longitude / X")
        self.goto_lat = QLineEdit(); self.goto_lat.setPlaceholderText("Latitude / Y")
        self.goto_scale = QSpinBox(); self.goto_scale.setRange(100, 10_000_000); self.goto_scale.setValue(50_000)
        coord_form.addRow("X / Lon:", self.goto_lon)
        coord_form.addRow("Y / Lat:", self.goto_lat)
        coord_form.addRow("Scale 1:", self.goto_scale)
        btn_goto = QPushButton("➡ Go to Coordinates")
        btn_goto.setObjectName("blueBtn")
        btn_goto.clicked.connect(self._go_to_coordinates)
        coord_form.addRow(btn_goto)
        zoom_layout.addLayout(coord_form)
        zoom_box.setLayout(zoom_layout)
        layout.addWidget(zoom_box)

        # --- Grid Generation ---
        grid_box = QGroupBox("Generate Grid")
        grid_form = QFormLayout()
        self.grid_type = QComboBox()
        self.grid_type.addItems(["Rectangle", "Diamond", "Hexagon (Flat-top)", "Hexagon (Pointy-top)"])
        self.grid_width = QDoubleSpinBox(); self.grid_width.setRange(0.001, 1_000_000); self.grid_width.setValue(1000); self.grid_width.setSuffix(" m")
        self.grid_height = QDoubleSpinBox(); self.grid_height.setRange(0.001, 1_000_000); self.grid_height.setValue(1000); self.grid_height.setSuffix(" m")
        grid_form.addRow("Type:", self.grid_type)
        grid_form.addRow("Width:", self.grid_width)
        grid_form.addRow("Height:", self.grid_height)
        btn_grid = QPushButton("🔲 Generate Grid from Canvas Extent")
        btn_grid.clicked.connect(self._generate_grid)
        grid_form.addRow(btn_grid)
        grid_box.setLayout(grid_form)
        layout.addWidget(grid_box)

        # --- Map Scale ---
        scale_box = QGroupBox("Map Scale")
        scale_layout = QHBoxLayout()
        self.scale_label = QLabel(f"1 : {int(self.canvas.scale()):,}")
        self.scale_label.setStyleSheet("color: #1e40af; font-weight: bold; font-size: 11px;")
        btn_refresh_scale = QPushButton("🔄 Refresh")
        btn_refresh_scale.clicked.connect(self._update_scale)
        self.canvas.scaleChanged.connect(self._update_scale)
        scale_layout.addWidget(QLabel("Current scale:"))
        scale_layout.addWidget(self.scale_label)
        scale_layout.addWidget(btn_refresh_scale)
        scale_box.setLayout(scale_layout)
        layout.addWidget(scale_box)

        layout.addStretch()
        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Coordinate Picker
    # ------------------------------------------------------------------
    def _toggle_coord_tool(self, checked):
        if checked:
            self._coord_tool = CoordClickTool(self.canvas, self._on_coord_clicked)
            self.canvas.setMapTool(self._coord_tool)
        else:
            self.canvas.unsetMapTool(getattr(self, "_coord_tool", None))

    def _on_coord_clicked(self, point):
        crs = self.canvas.mapSettings().destinationCrs()
        text, short_lbl = format_coordinate_text(point, crs)
        self.coord_output.setText(text)
        self.coord_label.setText(short_lbl)

    # ------------------------------------------------------------------
    # Measure Tool
    # ------------------------------------------------------------------
    def _toggle_measure(self, checked):
        if checked:
            self._measure_points = []
            self._rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
            self._rubber_band.setColor(QColor("#f44336"))
            self._rubber_band.setWidth(2)
            self._measure_tool = CoordClickTool(self.canvas, self._on_measure_click)
            self.canvas.setMapTool(self._measure_tool)
        else:
            self.canvas.unsetMapTool(getattr(self, "_measure_tool", None))

    def _on_measure_click(self, point):
        self._measure_points.append(point)
        if self._rubber_band:
            self._rubber_band.addPoint(point)
        self._update_measure_result()

    def _update_measure_result(self):
        res = calculate_measurement(
            self._measure_points,
            self.measure_distance_rb.isChecked(),
            self.measure_unit.currentIndex(),
            self.canvas
        )
        self.measure_result.setText(res)

    def _clear_measure(self):
        self._measure_points = []
        if self._rubber_band:
            self._rubber_band.reset()
        self.measure_result.setText("Result: --")
        self.measure_btn.setChecked(False)
        self.canvas.unsetMapTool(getattr(self, "_measure_tool", None))

    # ------------------------------------------------------------------
    # Navigate
    # ------------------------------------------------------------------
    def zoom_to_selection(self):
        layer = self.iface.activeLayer()
        if layer and layer.type() == QgsMapLayer.VectorLayer:
            self.iface.mapCanvas().zoomToSelected(layer)
        else:
            self.iface.messageBar().pushWarning("GeoAnalytica", "No active vector layer with selection.")

    def _go_to_coordinates(self):
        try:
            x = float(self.goto_lon.text())
            y = float(self.goto_lat.text())
            scale = self.goto_scale.value()
            center = QgsPointXY(x, y)
            self.canvas.setCenter(center)
            self.canvas.zoomScale(scale)
            self.canvas.refresh()
        except ValueError:
            QMessageBox.warning(self, "Invalid Coordinates",
                "Enter valid numeric X/Longitude and Y/Latitude values.")

    # ------------------------------------------------------------------
    # Grid
    # ------------------------------------------------------------------
    def _generate_grid(self):
        try:
            out = generate_grid_layer(
                self.canvas,
                self.grid_type.currentText(),
                self.grid_width.value(),
                self.grid_height.value()
            )
            if out:
                QgsProject.instance().addMapLayer(out)
                self.iface.messageBar().pushSuccess("GeoAnalytica", "Grid created!")
        except Exception as e:
            QMessageBox.critical(self, "Grid Error", str(e))

    # ------------------------------------------------------------------
    # Scale
    # ------------------------------------------------------------------
    def _update_scale(self):
        scale = int(self.canvas.scale())
        self.scale_label.setText(f"1 : {scale:,}")
