# -*- coding: utf-8 -*-
"""
GeoStudio - Selection Map Tool
Provides single-click, rectangle marquee, polygon, and circular radius selection
on vector layers with Shift (add) and Ctrl (toggle) modifiers.
"""

import math
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsProject, QgsMapLayer, QgsGeometry, QgsPointXY,
    QgsRectangle, QgsWkbTypes, QgsCoordinateTransform
)
from qgis.gui import QgsMapTool, QgsRubberBand


class GeoSelectTool(QgsMapTool):
    """Interactive selection tool supporting single-click, rectangle, polygon, and radius modes."""

    selection_completed = pyqtSignal(int)

    def __init__(self, canvas, main_window, mode="single"):
        super().__init__(canvas)
        self.canvas = canvas
        self.mw = main_window
        self.mode = mode
        self.setCursor(Qt.CrossCursor)

        self._start_pt = None
        self._pts = []
        self._rubber_band = None
        self._init_rubber_band()

    def set_mode(self, mode: str):
        self.mode = mode
        self._reset()

    def _init_rubber_band(self):
        if self._rubber_band:
            self._rubber_band.reset()
        geom_type = QgsWkbTypes.PolygonGeometry if self.mode in ("rectangle", "polygon", "radius") else QgsWkbTypes.PointGeometry
        self._rubber_band = QgsRubberBand(self.canvas, geom_type)
        self._rubber_band.setColor(QColor(37, 99, 235, 60))        # Translucent blue
        self._rubber_band.setStrokeColor(QColor(37, 99, 235, 220)) # Solid blue border
        self._rubber_band.setWidth(2)

    def _reset(self):
        self._start_pt = None
        self._pts = []
        if self._rubber_band:
            self._rubber_band.reset()

    def _get_active_vector_layer(self):
        layer = self.mw.layer_panel.get_active_layer() if hasattr(self.mw, "layer_panel") else None
        if not layer or layer.type() != QgsMapLayer.VectorLayer:
            for l in QgsProject.instance().mapLayers().values():
                if l.type() == QgsMapLayer.VectorLayer and l.isValid():
                    return l
            return None
        return layer

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            if self.mode in ("single", "rectangle", "radius"):
                self._start_pt = pt
                self._pts = [pt]
                self._init_rubber_band()
                if self.mode == "rectangle":
                    self._rubber_band.setToCanvasRectangle(event.pos(), event.pos())
            elif self.mode == "polygon":
                self._pts.append(pt)
                self._rubber_band.addPoint(pt, True)
                self._rubber_band.show()

        elif event.button() == Qt.RightButton:
            if self.mode == "polygon" and len(self._pts) >= 3:
                self._apply_polygon_selection()
            self._reset()

    def canvasMoveEvent(self, event):
        if not self._start_pt and self.mode != "polygon":
            return
        curr_pt = self.toMapCoordinates(event.pos())

        if self.mode == "rectangle" and self._start_pt:
            rect = QgsRectangle(self._start_pt, curr_pt)
            self._rubber_band.setToGeometry(QgsGeometry.fromRect(rect), None)
            self._rubber_band.show()

        elif self.mode == "radius" and self._start_pt:
            dist = math.hypot(curr_pt.x() - self._start_pt.x(), curr_pt.y() - self._start_pt.y())
            circle_pts = [
                QgsPointXY(self._start_pt.x() + dist * math.cos(math.radians(i * 10)),
                           self._start_pt.y() + dist * math.sin(math.radians(i * 10)))
                for i in range(37)
            ]
            self._rubber_band.setToGeometry(QgsGeometry.fromPolygonXY([circle_pts]), None)
            self._rubber_band.show()

        elif self.mode == "polygon" and len(self._pts) > 0:
            preview_pts = self._pts + [curr_pt]
            self._rubber_band.setToGeometry(QgsGeometry.fromPolygonXY([preview_pts]), None)
            self._rubber_band.show()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        end_pt = self.toMapCoordinates(event.pos())
        layer = self._get_active_vector_layer()
        if not layer:
            self.mw.geo_status.showMessage("⚠ Please select a vector layer to perform selection.", 3000)
            self._reset()
            return

        ctrl_held = bool(event.modifiers() & Qt.ControlModifier)
        shift_held = bool(event.modifiers() & Qt.ShiftModifier)

        if self.mode == "single":
            search_radius = self.canvas.mapUnitsPerPixel() * 8
            rect = QgsRectangle(end_pt.x() - search_radius, end_pt.y() - search_radius,
                                end_pt.x() + search_radius, end_pt.y() + search_radius)
            self._do_select(layer, QgsGeometry.fromRect(rect), ctrl_held, shift_held)
            self._reset()

        elif self.mode == "rectangle" and self._start_pt:
            if math.hypot(end_pt.x() - self._start_pt.x(), end_pt.y() - self._start_pt.y()) < self.canvas.mapUnitsPerPixel() * 3:
                search_radius = self.canvas.mapUnitsPerPixel() * 8
                geom = QgsGeometry.fromRect(QgsRectangle(end_pt.x() - search_radius, end_pt.y() - search_radius,
                                                         end_pt.x() + search_radius, end_pt.y() + search_radius))
            else:
                geom = QgsGeometry.fromRect(QgsRectangle(self._start_pt, end_pt))
            self._do_select(layer, geom, ctrl_held, shift_held)
            self._reset()

        elif self.mode == "radius" and self._start_pt:
            dist = math.hypot(end_pt.x() - self._start_pt.x(), end_pt.y() - self._start_pt.y())
            if dist > 0:
                circle_pts = [
                    QgsPointXY(self._start_pt.x() + dist * math.cos(math.radians(i * 10)),
                               self._start_pt.y() + dist * math.sin(math.radians(i * 10)))
                    for i in range(37)
                ]
                self._do_select(layer, QgsGeometry.fromPolygonXY([circle_pts]), ctrl_held, shift_held)
            self._reset()

    def _apply_polygon_selection(self):
        layer = self._get_active_vector_layer()
        if layer and len(self._pts) >= 3:
            geom = QgsGeometry.fromPolygonXY([self._pts])
            self._do_select(layer, geom, False, False)
        self._reset()

    def _do_select(self, layer, geom, ctrl, shift):
        if not layer or not geom:
            return
        dest_crs = self.canvas.mapSettings().destinationCrs()
        if dest_crs.isValid() and layer.crs().isValid() and dest_crs != layer.crs():
            tr = QgsCoordinateTransform(dest_crs, layer.crs(), QgsProject.instance())
            geom.transform(tr)

        select_box = geom.boundingBox()
        req = layer.getFeatures(select_box)
        selected_ids = [feat.id() for feat in req if feat.geometry().intersects(geom)]

        if shift:
            current = set(layer.selectedFeatureIds())
            layer.selectByIds(list(current.union(selected_ids)))
        elif ctrl:
            current = set(layer.selectedFeatureIds())
            for fid in selected_ids:
                if fid in current:
                    current.remove(fid)
                else:
                    current.add(fid)
            layer.selectByIds(list(current))
        else:
            layer.selectByIds(selected_ids)

        count = layer.selectedFeatureCount()
        self.canvas.refresh()
        self.mw.geo_status.showMessage(f"Selected {count} feature(s) in '{layer.name()}'.", 3000)
        self.selection_completed.emit(count)

    def deactivate(self):
        self._reset()
        super().deactivate()
