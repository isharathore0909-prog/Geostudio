# -*- coding: utf-8 -*-
"""
GeoStudio - Coordinate & Elevation Capture Tool
Samples Native CRS, WGS84 Lat/Lon, and DEM raster elevation on click.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from qgis.core import (
    QgsProject, QgsMapLayer, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsGeometry, QgsWkbTypes
)
from qgis.gui import QgsMapTool, QgsRubberBand


class GeoCoordCaptureTool(QgsMapTool):
    """Click anywhere on the map to sample coordinates and DEM elevation."""

    def __init__(self, canvas, main_window):
        super().__init__(canvas)
        self.canvas = canvas
        self.mw = main_window
        self.setCursor(Qt.CrossCursor)
        self._history = []
        self._redo_history = []
        self._marker = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self._marker.setColor(QColor(239, 68, 68, 220))
        self._marker.setStrokeColor(QColor(185, 28, 28, 255))
        self._marker.setWidth(7)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            self._capture_point(pt)
            self._redo_history.clear()
        elif event.button() == Qt.RightButton:
            self._reset()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.undo_last_point()
        elif event.key() == Qt.Key_Z and (event.modifiers() & Qt.ControlModifier):
            self.undo_last_point()
        elif event.key() == Qt.Key_Y and (event.modifiers() & Qt.ControlModifier):
            self.redo_last_point()
        elif event.key() == Qt.Key_Escape:
            self._reset()
            self.mw.geo_status.showMessage("Coordinate capture cleared.", 2000)
        else:
            super().keyPressEvent(event)

    def _capture_point(self, pt):
        crs = self.canvas.mapSettings().destinationCrs()
        wgs84 = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
        try:
            pt_wgs84 = wgs84.transform(pt)
            lon, lat = pt_wgs84.x(), pt_wgs84.y()
        except Exception:
            lon, lat = pt.x(), pt.y()

        elev = self._sample_elevation(pt)
        elev_str = f"{elev:.2f} m" if elev is not None else "N/A"

        coord_text = f"X: {pt.x():.4f}, Y: {pt.y():.4f} | Lat: {lat:.6f}°, Lon: {lon:.6f}° | Elev: {elev_str}"
        self._history.append((pt, coord_text))
        self._update_marker(pt)

        QApplication.clipboard().setText(coord_text)
        self.mw.geo_status.showMessage(f"📍 {coord_text} (Copied to Clipboard)", 5000)

    def _update_marker(self, pt):
        if not self._marker:
            return
        if pt is None:
            self._marker.reset(QgsWkbTypes.PointGeometry)
        else:
            self._marker.reset(QgsWkbTypes.PointGeometry)
            self._marker.setColor(QColor(239, 68, 68, 220))
            self._marker.setStrokeColor(QColor(185, 28, 28, 255))
            self._marker.setWidth(7)
            self._marker.setToGeometry(QgsGeometry.fromPointXY(pt), None)
            self._marker.show()

    def _sample_elevation(self, pt):
        try:
            from core.elevation_styler import ElevationStyler
            for layer in QgsProject.instance().mapLayers().values():
                if layer.type() == QgsMapLayer.RasterLayer and layer.isValid():
                    val, _ = ElevationStyler.sample_elevation_at_point(
                        layer, pt, map_crs=self.canvas.mapSettings().destinationCrs(), band=1
                    )
                    if val is not None:
                        return val
        except Exception:
            pass
        return None

    def undo_last_point(self):
        """Removes the last captured coordinate point."""
        if self._history:
            item = self._history.pop()
            self._redo_history.append(item)
            if self._history:
                last_pt, last_text = self._history[-1]
                self._update_marker(last_pt)
                self.mw.geo_status.showMessage(f"📍 {last_text}", 4000)
            else:
                self._update_marker(None)
                self.mw.geo_status.showMessage("Coordinate capture buffer cleared (Undo).", 2000)
            return True
        return False

    def redo_last_point(self):
        """Restores the last undone coordinate point."""
        if self._redo_history:
            item = self._redo_history.pop()
            self._history.append(item)
            pt, coord_text = item
            self._update_marker(pt)
            self.mw.geo_status.showMessage(f"📍 {coord_text} (Redo)", 4000)
            return True
        return False

    def _reset(self):
        self._history.clear()
        self._redo_history.clear()
        if self._marker:
            self._marker.reset(QgsWkbTypes.PointGeometry)

    def deactivate(self):
        self._reset()
        super().deactivate()
