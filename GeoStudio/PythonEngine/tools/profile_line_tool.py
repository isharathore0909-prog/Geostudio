# -*- coding: utf-8 -*-
"""
GeoStudio - Profile Transect Line Map Tool
Draws on-canvas transect lines for terrain elevation profile extraction.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from qgis.core import QgsGeometry, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand


class GeoProfileLineTool(QgsMapTool):
    """Draws a transect line across the terrain for elevation profiling."""

    profile_line_drawn = pyqtSignal(list)

    def __init__(self, canvas, main_window):
        super().__init__(canvas)
        self.canvas = canvas
        self.mw = main_window
        self.setCursor(Qt.CrossCursor)

        self._pts = []
        self._is_dragging = False
        self._press_pos = None
        self._rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self._rubber_band.setColor(QColor(14, 165, 233, 120))       # Sky blue highlight
        self._rubber_band.setStrokeColor(QColor(2, 132, 199, 255))  # Royal blue solid
        self._rubber_band.setWidth(3)

    def _reset(self):
        self._pts = []
        self._is_dragging = False
        self._press_pos = None
        if self._rubber_band:
            self._rubber_band.reset()

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            self._press_pos = event.pos()
            self._is_dragging = True
            self._pts.append(pt)
            self._rubber_band.addPoint(pt, True)
            self._rubber_band.show()
            self.mw.geo_status.showMessage(
                f"Profile Transect: Point {len(self._pts)} added. [Drag & release, double-click, or right-click to finish]", 4000
            )

        elif event.button() == Qt.RightButton:
            self._finish_drawing()

    def canvasMoveEvent(self, event):
        if not self._pts:
            return
        curr_pt = self.toMapCoordinates(event.pos())
        preview_pts = self._pts + [curr_pt]
        self._rubber_band.setToGeometry(QgsGeometry.fromPolylineXY(preview_pts), None)
        self._rubber_band.show()

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_dragging:
            self._is_dragging = False
            if self._press_pos is not None:
                # If dragged across a significant distance, auto-add end point and finish
                delta = event.pos() - self._press_pos
                if abs(delta.x()) > 15 or abs(delta.y()) > 15:
                    curr_pt = self.toMapCoordinates(event.pos())
                    self._pts.append(curr_pt)
                    self._finish_drawing()

    def canvasDoubleClickEvent(self, event):
        self._finish_drawing()

    def _finish_drawing(self):
        if len(self._pts) >= 2:
            pts_copy = list(self._pts)
            self._reset()
            self.profile_line_drawn.emit(pts_copy)
        else:
            self._reset()

    def deactivate(self):
        self._reset()
        super().deactivate()
