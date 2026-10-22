# -*- coding: utf-8 -*-
"""
GeoStudio - Vector Digitizing & Geometry Editing Map Tool
Full-featured interactive tool supporting:
- Point, Line, and Polygon creation
- Vertex Tool / Node Editor (move, insert, and delete vertices)
- Move and Rotate features
- Split polygon/line features with cut lines
- Live vector snapping (vertex, segment, area)
- Multi-step Undo / Redo for vertex digitizing
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox

from qgis.core import QgsMapLayer, QgsGeometry, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand

from .digitize_operations import (
    snap_point, find_feature_at, find_vertex_at, find_segment_at,
    create_scratch_vector_layer, insert_point_feature, insert_line_feature,
    insert_polygon_feature, execute_split_feature, calculate_rotation_geom
)


class GeoDigitizeTool(QgsMapTool):
    """Vector digitizing tool supporting point/line/poly creation, vertex editing, move, rotate, and split."""

    feature_added = pyqtSignal(int)

    def __init__(self, canvas, main_window, tool_type="point"):
        super().__init__(canvas)
        self.canvas = canvas
        self.mw = main_window
        self.tool_type = tool_type
        self.setCursor(Qt.CrossCursor)

        self._pts = []
        self._undone_pts = []
        self._rubber_band = None
        self._hover_marker = None
        self._selected_feat = None
        self._drag_start = None
        self._vertex_index = None

        self._init_rubber_bands()

    def set_tool_type(self, tool_type: str):
        self.tool_type = tool_type
        self._reset()

    def _init_rubber_bands(self):
        if self._rubber_band:
            self._rubber_band.reset()
        if self._hover_marker:
            self._hover_marker.reset()

        geom_type = QgsWkbTypes.PolygonGeometry if self.tool_type in ("polygon", "rotate") else QgsWkbTypes.LineGeometry
        self._rubber_band = QgsRubberBand(self.canvas, geom_type)
        self._apply_style()

        self._hover_marker = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self._hover_marker.setColor(QColor(239, 68, 68, 220))
        self._hover_marker.setStrokeColor(QColor(185, 28, 28, 255))
        self._hover_marker.setWidth(8)

    def _apply_style(self):
        if not self._rubber_band:
            return
        if self.tool_type == "vertex":
            self._rubber_band.setColor(QColor(59, 130, 246, 60))
            self._rubber_band.setStrokeColor(QColor(37, 99, 235, 230))
        elif self.tool_type in ("move", "rotate"):
            self._rubber_band.setColor(QColor(16, 185, 129, 60))
            self._rubber_band.setStrokeColor(QColor(5, 150, 105, 230))
        elif self.tool_type == "split":
            self._rubber_band.setColor(QColor(239, 68, 68, 70))
            self._rubber_band.setStrokeColor(QColor(220, 38, 38, 240))
        else:
            self._rubber_band.setColor(QColor(245, 158, 11, 75))
            self._rubber_band.setStrokeColor(QColor(217, 119, 6, 230))
        self._rubber_band.setWidth(2)

    def _reset(self):
        self._pts = []
        self._undone_pts = []
        self._selected_feat = None
        self._drag_start = None
        self._vertex_index = None
        if self._rubber_band:
            self._rubber_band.reset()
        if self._hover_marker:
            self._hover_marker.reset()

    def _get_editable_layer(self):
        layer = self.mw.layer_panel.get_active_layer() if hasattr(self.mw, "layer_panel") else None
        if not layer or layer.type() != QgsMapLayer.VectorLayer:
            reply = QMessageBox.question(
                self.mw, "Create Vector Layer",
                f"Digitizing creates vector features (points, lines, polygons).\n\n"
                f"Would you like to create a new '{self.tool_type.capitalize()}' vector layer to draw on top of your current map/raster?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                new_layer = create_scratch_vector_layer(self.canvas, self.tool_type)
                if new_layer and hasattr(self.mw, "layer_panel"):
                    self.mw.layer_panel.refresh()
                return new_layer
            return None

        if not layer.isEditable():
            reply = QMessageBox.question(
                self.mw, "Start Editing",
                f"Layer '{layer.name()}' is not in edit mode.\nWould you like to start editing now?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                layer.startEditing()
                self.canvas.refresh()
                self.mw.geo_status.showMessage(f"Editing started for '{layer.name()}'.", 2500)
            else:
                return None
        return layer

    def canvasPressEvent(self, event):
        layer = self._get_editable_layer()
        if not layer:
            return

        raw_pt = self.toMapCoordinates(event.pos())
        pt = snap_point(self.canvas, raw_pt, layer)

        if event.button() == Qt.LeftButton:
            if self.tool_type == "point":
                fid = insert_point_feature(self.canvas, layer, pt)
                if fid is not None:
                    self.feature_added.emit(fid)
                    self.mw.geo_status.showMessage("Point feature added successfully.", 2500)

            elif self.tool_type in ("line", "polygon", "split"):
                self._pts.append(pt)
                self._undone_pts.clear()
                self._update_rubber_band()

            elif self.tool_type == "vertex":
                self._drag_start = pt
                feat, vidx, vpt = find_vertex_at(self.canvas, layer, pt)
                if feat and vidx >= 0:
                    self._selected_feat = feat
                    self._vertex_index = vidx
                    self._rubber_band.setToGeometry(feat.geometry(), None)
                    self._rubber_band.show()
                else:
                    feat, seg_pt, after_idx = find_segment_at(self.canvas, layer, pt)
                    if feat and after_idx >= 0:
                        layer.insertVertex(pt.x(), pt.y(), feat.id(), after_idx)
                        self.canvas.refresh()
                        self.mw.geo_status.showMessage(f"Inserted new vertex in feature #{feat.id()}.", 2500)

            elif self.tool_type in ("move", "rotate"):
                self._drag_start = pt
                self._selected_feat = find_feature_at(self.canvas, layer, pt)
                if self._selected_feat:
                    self._rubber_band.setToGeometry(self._selected_feat.geometry(), None)
                    self._rubber_band.show()
                else:
                    self.mw.geo_status.showMessage("Click directly on a feature to move/rotate.", 2000)

        elif event.button() == Qt.RightButton:
            if self.tool_type == "line" and len(self._pts) >= 2:
                fid = insert_line_feature(self.canvas, layer, self._pts)
                if fid is not None:
                    self.feature_added.emit(fid)
                    self.mw.geo_status.showMessage(f"Line feature added with {len(self._pts)} vertices.", 2500)
            elif self.tool_type == "polygon" and len(self._pts) >= 3:
                fid = insert_polygon_feature(self.canvas, layer, self._pts)
                if fid is not None:
                    self.feature_added.emit(fid)
                    self.mw.geo_status.showMessage(f"Polygon feature added with {len(self._pts)} vertices.", 2500)
            elif self.tool_type == "split" and len(self._pts) >= 2:
                count = execute_split_feature(self.canvas, layer, self._pts)
                if count > 0:
                    self.mw.geo_status.showMessage(f"Split feature into {count} parts.", 3000)
                else:
                    self.mw.geo_status.showMessage("Split line did not intersect any selected feature.", 2500)
            elif self.tool_type == "vertex" and self._selected_feat and self._vertex_index is not None:
                layer.deleteVertex(self._selected_feat.id(), self._vertex_index)
                self.canvas.refresh()
                self.mw.geo_status.showMessage(f"Deleted vertex #{self._vertex_index}.", 2500)
            self._reset()

    def canvasMoveEvent(self, event):
        raw_pt = self.toMapCoordinates(event.pos())
        layer = self.mw.layer_panel.get_active_layer() if hasattr(self.mw, "layer_panel") else None
        curr_pt = snap_point(self.canvas, raw_pt, layer)

        if self.tool_type in ("line", "polygon", "split") and self._pts:
            self._update_rubber_band(self._pts + [curr_pt])
        elif self.tool_type == "vertex":
            if self._drag_start and self._selected_feat and self._vertex_index is not None:
                geom = QgsGeometry(self._selected_feat.geometry())
                geom.moveVertex(curr_pt.x(), curr_pt.y(), self._vertex_index)
                self._rubber_band.setToGeometry(geom, None)
                self._rubber_band.show()
            elif layer:
                _, _, vpt = find_vertex_at(self.canvas, layer, curr_pt)
                if vpt and self._hover_marker:
                    self._hover_marker.setToGeometry(QgsGeometry.fromPointXY(vpt), None)
                    self._hover_marker.show()
                elif self._hover_marker:
                    self._hover_marker.reset(QgsWkbTypes.PointGeometry)
        elif self.tool_type == "move" and self._drag_start and self._selected_feat:
            dx, dy = curr_pt.x() - self._drag_start.x(), curr_pt.y() - self._drag_start.y()
            geom = QgsGeometry(self._selected_feat.geometry())
            geom.translate(dx, dy)
            self._rubber_band.setToGeometry(geom, None)
            self._rubber_band.show()
        elif self.tool_type == "rotate" and self._drag_start and self._selected_feat:
            geom, _ = calculate_rotation_geom(self._selected_feat.geometry(), self._drag_start, curr_pt)
            self._rubber_band.setToGeometry(geom, None)
            self._rubber_band.show()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        layer = self.mw.layer_panel.get_active_layer() if hasattr(self.mw, "layer_panel") else None
        if not layer or not layer.isEditable():
            return

        raw_pt = self.toMapCoordinates(event.pos())
        curr_pt = snap_point(self.canvas, raw_pt, layer)

        if self.tool_type == "vertex" and self._drag_start and self._selected_feat and self._vertex_index is not None:
            layer.moveVertex(curr_pt.x(), curr_pt.y(), self._selected_feat.id(), self._vertex_index)
            self.canvas.refresh()
            self.mw.geo_status.showMessage(f"Moved vertex #{self._vertex_index}.", 2500)
            self._reset()
        elif self.tool_type == "move" and self._drag_start and self._selected_feat:
            dx, dy = curr_pt.x() - self._drag_start.x(), curr_pt.y() - self._drag_start.y()
            layer.translateFeature(self._selected_feat.id(), dx, dy)
            self.canvas.refresh()
            self.mw.geo_status.showMessage(f"Moved feature #{self._selected_feat.id()}.", 2500)
            self._reset()
        elif self.tool_type == "rotate" and self._drag_start and self._selected_feat:
            geom, diff_deg = calculate_rotation_geom(self._selected_feat.geometry(), self._drag_start, curr_pt)
            layer.changeGeometry(self._selected_feat.id(), geom)
            self.canvas.refresh()
            self.mw.geo_status.showMessage(f"Rotated feature #{self._selected_feat.id()} by {diff_deg:.1f}°.", 2500)
            self._reset()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete) or (event.key() == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier)):
            self.undo_last_point()
        elif event.key() == Qt.Key_Y and (event.modifiers() & Qt.ControlModifier):
            self.redo_last_point()
        elif event.key() == Qt.Key_Escape:
            self._reset()
            self.mw.geo_status.showMessage("Digitizing buffer cleared.", 2000)
        else:
            super().keyPressEvent(event)

    def _update_rubber_band(self, points=None):
        pts_to_draw = points if points is not None else self._pts
        if not self._rubber_band or not pts_to_draw:
            if self._rubber_band:
                self._rubber_band.reset()
            return

        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry if self.tool_type == "polygon" else QgsWkbTypes.LineGeometry)
        for i, pt in enumerate(pts_to_draw):
            self._rubber_band.addPoint(pt, i == len(pts_to_draw) - 1)
        self._rubber_band.show()

    def undo_last_point(self):
        if self._pts:
            self._undone_pts.append(self._pts.pop())
            self._update_rubber_band()
            self.mw.geo_status.showMessage(f"Undo vertex ({len(self._pts)} remaining).", 1500)

    def redo_last_point(self):
        if self._undone_pts:
            self._pts.append(self._undone_pts.pop())
            self._update_rubber_band()
            self.mw.geo_status.showMessage(f"Redo vertex ({len(self._pts)} total).", 1500)
