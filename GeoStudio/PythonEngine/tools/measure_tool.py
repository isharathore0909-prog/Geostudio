# -*- coding: utf-8 -*-
"""
GeoStudio - Measurement Map Tool
Interactive geodesic distance, polygon area, and 3-point angle/azimuth measurement.
Supports full Undo and Redo of vertices with real-time recalculation.
"""

import math
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsProject, QgsGeometry, QgsDistanceArea, QgsWkbTypes, QgsPointXY
)
from qgis.gui import QgsMapTool, QgsRubberBand


class GeoMeasureTool(QgsMapTool):
    """Real-time measurement tool for Distance, Area, and Angle / Azimuth."""

    def __init__(self, canvas, main_window, measure_type="distance"):
        super().__init__(canvas)
        self.canvas = canvas
        self.mw = main_window
        self.measure_type = measure_type
        self.setCursor(Qt.CrossCursor)

        self._pts = []
        self._undone_pts = []
        self._rubber_band = None
        self._init_rubber_band()

    def set_measure_type(self, mtype: str):
        self.measure_type = mtype
        self._reset()

    def _init_rubber_band(self):
        if self._rubber_band:
            self._rubber_band.reset()
        geom_type = QgsWkbTypes.PolygonGeometry if self.measure_type == "area" else QgsWkbTypes.LineGeometry
        self._rubber_band = QgsRubberBand(self.canvas, geom_type)
        self._apply_style()

    def _apply_style(self):
        if not self._rubber_band:
            return
        if self.measure_type == "angle":
            self._rubber_band.setColor(QColor(14, 165, 233, 75))       # Cyan fill
            self._rubber_band.setStrokeColor(QColor(2, 132, 199, 230))  # Cyan border
        else:
            self._rubber_band.setColor(QColor(245, 158, 11, 75))       # Amber translucent fill
            self._rubber_band.setStrokeColor(QColor(217, 119, 6, 230))  # Amber border
        self._rubber_band.setWidth(2)

    def _reset(self):
        self._pts = []
        self._undone_pts = []
        if self._rubber_band:
            self._rubber_band.reset()

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            self._pts.append(pt)
            self._undone_pts.clear()
            self._update_rubber_band()
            self._calculate_and_display()

        elif event.button() == Qt.RightButton:
            self._calculate_and_display(final=True)
            self._undone_pts.clear()

    def canvasMoveEvent(self, event):
        if not self._pts:
            return
        curr_pt = self.toMapCoordinates(event.pos())
        preview_pts = self._pts + [curr_pt]
        self._update_rubber_band(preview_pts)
        self._calculate_and_display(preview_pt=curr_pt)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.undo_last_point()
        elif event.key() == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier):
            self.undo_last_point()
        elif event.key() == Qt.Key_Y and (event.modifiers() & Qt.ControlModifier):
            self.redo_last_point()
        elif event.key() == Qt.Key_Escape:
            self._reset()
            self.mw.geo_status.showMessage("Measurement cleared.", 2000)
        else:
            super().keyPressEvent(event)

    def _update_rubber_band(self, pts=None):
        if not self._rubber_band:
            return
        target_pts = pts if pts is not None else self._pts
        if not target_pts:
            self._rubber_band.reset()
            return

        if self.measure_type == "area":
            if len(target_pts) >= 3:
                self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)
                self._apply_style()
                closed = list(target_pts) + [target_pts[0]]
                self._rubber_band.setToGeometry(QgsGeometry.fromPolygonXY([closed]), None)
            elif len(target_pts) == 2:
                self._rubber_band.reset(QgsWkbTypes.LineGeometry)
                self._apply_style()
                self._rubber_band.setToGeometry(QgsGeometry.fromPolylineXY(target_pts), None)
            elif len(target_pts) == 1:
                self._rubber_band.reset(QgsWkbTypes.PointGeometry)
                self._apply_style()
                self._rubber_band.setWidth(6)
                self._rubber_band.setToGeometry(QgsGeometry.fromPointXY(target_pts[0]), None)

        elif self.measure_type == "angle":
            if len(target_pts) >= 2:
                self._rubber_band.reset(QgsWkbTypes.LineGeometry)
                self._apply_style()
                self._rubber_band.setToGeometry(QgsGeometry.fromPolylineXY(target_pts), None)
            elif len(target_pts) == 1:
                self._rubber_band.reset(QgsWkbTypes.PointGeometry)
                self._apply_style()
                self._rubber_band.setWidth(6)
                self._rubber_band.setToGeometry(QgsGeometry.fromPointXY(target_pts[0]), None)

        else: # distance
            if len(target_pts) >= 2:
                self._rubber_band.reset(QgsWkbTypes.LineGeometry)
                self._apply_style()
                self._rubber_band.setToGeometry(QgsGeometry.fromPolylineXY(target_pts), None)
            elif len(target_pts) == 1:
                self._rubber_band.reset(QgsWkbTypes.PointGeometry)
                self._apply_style()
                self._rubber_band.setWidth(6)
                self._rubber_band.setToGeometry(QgsGeometry.fromPointXY(target_pts[0]), None)

        self._rubber_band.show()

    @staticmethod
    def _compute_segment_distance(da, p1, p2, is_geographic):
        if is_geographic:
            lat1, lon1 = math.radians(p1.y()), math.radians(p1.x())
            lat2, lon2 = math.radians(p2.y()), math.radians(p2.x())
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat / 2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0)**2
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
            return 6378137.0 * c
        else:
            return float(da.measureLine(p1, p2))

    @staticmethod
    def _compute_polygon_area(da, pts, is_geographic):
        if is_geographic and len(pts) >= 3:
            R = 6378137.0
            n = len(pts)
            rad_pts = [(math.radians(p.x()), math.radians(p.y())) for p in pts]
            total_sum = 0.0
            for i in range(n):
                prev_lon = rad_pts[(i - 1) % n][0]
                next_lon = rad_pts[(i + 1) % n][0]
                curr_lat = rad_pts[i][1]
                total_sum += (next_lon - prev_lon) * math.sin(curr_lat)
            return abs(total_sum * (R ** 2) / 2.0)
        else:
            poly = QgsGeometry.fromPolygonXY([pts + [pts[0]]])
            return float(da.measureArea(poly))

    @staticmethod
    def _compute_bearing(p1, p2, is_geographic):
        if is_geographic:
            lat1, lon1 = math.radians(p1.y()), math.radians(p1.x())
            lat2, lon2 = math.radians(p2.y()), math.radians(p2.x())
            dlon = lon2 - lon1
            y = math.sin(dlon) * math.cos(lat2)
            x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
            return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
        else:
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0

    def _calculate_and_display(self, preview_pt=None, final=False):
        pts = list(self._pts)
        if preview_pt:
            pts.append(preview_pt)
        if not pts:
            return

        dest_crs = self.canvas.mapSettings().destinationCrs()
        is_geographic = dest_crs.isGeographic() or (abs(pts[0].x()) <= 180.0 and abs(pts[0].y()) <= 90.0)

        da = QgsDistanceArea()
        da.setSourceCrs(dest_crs, QgsProject.instance().transformContext())
        da.setEllipsoid("WGS84")

        suffix = " [Right-click to finish]" if not final else " [Finished]"

        if self.measure_type == "distance":
            if len(pts) >= 2:
                total_dist = sum(self._compute_segment_distance(da, pts[i - 1], pts[i], is_geographic) for i in range(1, len(pts)))
                last_seg = self._compute_segment_distance(da, pts[-2], pts[-1], is_geographic)
                if total_dist >= 1000.0:
                    dist_str = f"Total: {total_dist/1000.0:.3f} km (Segment: {last_seg:.1f} m)"
                else:
                    dist_str = f"Total: {total_dist:.2f} m (Segment: {last_seg:.1f} m)"
                self.mw.geo_status.showMessage(f"📏 Distance: {dist_str} {suffix}", 4000)
            else:
                self.mw.geo_status.showMessage("📏 Distance: Click 2nd point to measure distance.", 3000)

        elif self.measure_type == "area":
            if len(pts) >= 3:
                area_m2 = self._compute_polygon_area(da, pts, is_geographic)
                if area_m2 >= 1_000_000.0:
                    area_str = f"{area_m2/1_000_000.0:.3f} km² ({area_m2/10_000.0:.2f} ha)"
                elif area_m2 >= 10_000.0:
                    area_str = f"{area_m2/10_000.0:.2f} ha ({area_m2:.1f} m²)"
                else:
                    area_str = f"{area_m2:.2f} m²"
                self.mw.geo_status.showMessage(f"📐 Area: {area_str} {suffix}", 4000)
            else:
                needed = 3 - len(pts)
                self.mw.geo_status.showMessage(f"📐 Area: Click {needed} more point(s) to form a polygon.", 3000)

        elif self.measure_type == "angle":
            if len(pts) == 1:
                self.mw.geo_status.showMessage("🧭 Angle/Bearing: Click 2nd point to establish base line.", 3000)
            elif len(pts) == 2:
                azimuth = self._compute_bearing(pts[0], pts[1], is_geographic)
                self.mw.geo_status.showMessage(f"🧭 Bearing: {azimuth:.2f}° (Azimuth)  [Click 3rd point for angle]", 4000)
            elif len(pts) >= 3:
                v, p1, p2 = pts[-2], pts[-3], pts[-1]
                b1 = self._compute_bearing(v, p1, is_geographic)
                b2 = self._compute_bearing(v, p2, is_geographic)
                deg = abs(b2 - b1)
                if deg > 180.0:
                    deg = 360.0 - deg
                self.mw.geo_status.showMessage(f"📐 Measured Angle: {deg:.2f}° (Interior) {suffix}", 4000)

    def undo_last_point(self):
        """Removes the last measured point and stores it in redo stack."""
        if self._pts:
            popped = self._pts.pop()
            self._undone_pts.append(popped)
            self._update_rubber_band()
            if self._pts:
                self._calculate_and_display()
            else:
                self.mw.geo_status.showMessage("Measurement buffer cleared (Undo).", 2000)
            return True
        return False

    def redo_last_point(self):
        """Restores the last undone point to the measurement buffer."""
        if self._undone_pts:
            restored = self._undone_pts.pop()
            self._pts.append(restored)
            self._update_rubber_band()
            self._calculate_and_display()
            return True
        return False

    def deactivate(self):
        self._reset()
        super().deactivate()
