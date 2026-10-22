# -*- coding: utf-8 -*-
"""
GeoStudio - Map Canvas Navigation & Extent Management
Zoom to layer, extent stack history (undo/redo pan/zoom), and coordinate CRS transforms.
"""

from qgis.core import QgsProject, QgsCoordinateTransform, QgsRectangle


class CanvasNavigationManager:
    """Manages extent history and layer zooming operations for QgsMapCanvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.extent_history = []
        self.history_index = -1
        self.ignore_extent_history = False

    def on_extents_changed(self):
        if self.ignore_extent_history or not self.canvas:
            return
        ext = self.canvas.extent()
        if not ext or ext.isEmpty() or ext.width() <= 0:
            return

        if 0 <= self.history_index < len(self.extent_history):
            curr = self.extent_history[self.history_index]
            if abs(curr.xMinimum() - ext.xMinimum()) < 1e-6 and abs(curr.width() - ext.width()) < 1e-6:
                return

        if self.history_index < len(self.extent_history) - 1:
            self.extent_history = self.extent_history[:self.history_index + 1]

        self.extent_history.append(QgsRectangle(ext))
        if len(self.extent_history) > 60:
            self.extent_history.pop(0)
        self.history_index = len(self.extent_history) - 1

    def zoom_last(self):
        """Navigate back to previous zoom extent."""
        if not self.canvas:
            return
        if self.history_index > 0:
            self.history_index -= 1
            ext = self.extent_history[self.history_index]
            self.ignore_extent_history = True
            try:
                self.canvas.setExtent(ext)
                self.canvas.refresh()
            finally:
                self.ignore_extent_history = False
        else:
            self.canvas.zoomToPreviousExtent()
            self.canvas.refresh()

    def zoom_next(self):
        """Navigate forward to next zoom extent."""
        if not self.canvas:
            return
        if 0 <= self.history_index < len(self.extent_history) - 1:
            self.history_index += 1
            ext = self.extent_history[self.history_index]
            self.ignore_extent_history = True
            try:
                self.canvas.setExtent(ext)
                self.canvas.refresh()
            finally:
                self.ignore_extent_history = False
        else:
            self.canvas.zoomToNextExtent()
            self.canvas.refresh()

    def zoom_to_layer(self, layer):
        """Zoom canvas to target layer bounding extent with padding."""
        if not layer or not self.canvas:
            return
        try:
            if not layer.isValid():
                return

            # Ensure layer has a valid CRS if coordinates are projected or unreferenced
            if not layer.crs().isValid() or not layer.crs().authid():
                from qgis.core import QgsCoordinateReferenceSystem
                ext = layer.extent()
                if ext.xMinimum() > 180.0 or ext.yMinimum() > 90.0 or ext.xMaximum() > 180.0 or ext.yMinimum() < -90.0:
                    layer.setCrs(QgsCoordinateReferenceSystem("EPSG:32643"))
                else:
                    layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

            if layer.crs().isValid():
                dest_crs = layer.crs()
                self.canvas.setDestinationCrs(dest_crs)
                QgsProject.instance().setCrs(dest_crs)
            else:
                dest_crs = self.canvas.mapSettings().destinationCrs()

            extent = layer.extent()
            if extent.isNull() or extent.isEmpty() or extent.width() <= 0 or extent.height() <= 0:
                if hasattr(layer, "dataProvider") and layer.dataProvider():
                    extent = layer.dataProvider().extent()

            if extent.isNull() or extent.width() <= 0 or extent.height() <= 0:
                return

            if dest_crs.isValid() and layer.crs().isValid() and dest_crs != layer.crs():
                try:
                    tr = QgsCoordinateTransform(layer.crs(), dest_crs, QgsProject.instance())
                    extent = tr.transformBoundingBox(extent)
                except Exception:
                    pass

            extent.scale(1.05)
            self.canvas.setExtent(extent)
            self.canvas.refresh()
            self.canvas.update()
        except Exception:
            pass


    def zoom_to_active_layer(self, layer=None):
        if layer and layer.isValid():
            self.zoom_to_layer(layer)
            return
        if self.canvas:
            try:
                layers = list(QgsProject.instance().mapLayers().values())
                if layers:
                    self.zoom_to_layer(layers[-1])
            except Exception:
                pass
