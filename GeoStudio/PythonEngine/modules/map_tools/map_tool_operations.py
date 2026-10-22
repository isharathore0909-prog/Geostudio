# -*- coding: utf-8 -*-
"""
GeoAnalytica / GeoStudio - Map Tools Operations
Measurement algorithms, coordinate formatting, click tool, and grid generation.
"""

from qgis.core import (
    QgsProject, QgsDistanceArea, QgsPointXY, QgsGeometry
)
from qgis.gui import QgsMapToolEmitPoint
import processing


class CoordClickTool(QgsMapToolEmitPoint):
    """Simple click tool that emits point coordinates."""
    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.callback = callback

    def canvasReleaseEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        self.callback(point)


def format_coordinate_text(point: QgsPointXY, crs) -> tuple:
    """Returns (multiline_detail_string, short_label_string)."""
    x, y = point.x(), point.y()
    authid = crs.authid() if crs and crs.isValid() else "Unknown"
    text = (
        f"CRS: {authid}\n"
        f"X / Lon: {x:.6f}\n"
        f"Y / Lat: {y:.6f}\n"
    )
    if crs and crs.isGeographic():
        def to_dms(deg):
            d = int(abs(deg))
            m = int((abs(deg) - d) * 60)
            s = (abs(deg) - d - m / 60) * 3600
            sign = "+" if deg >= 0 else "-"
            return f"{sign}{d}°{m}'{s:.2f}\""
        text += f"DMS: {to_dms(y)}, {to_dms(x)}\n"

    short_label = f"📍  {x:.6f}, {y:.6f}  [{authid}]"
    return text, short_label


def calculate_measurement(points: list, is_distance: bool, unit_idx: int, canvas) -> str:
    """Calculate measured distance or area string."""
    if not points:
        return "Result: --"
    da = QgsDistanceArea()
    da.setSourceCrs(
        canvas.mapSettings().destinationCrs(),
        QgsProject.instance().transformContext()
    )
    da.setEllipsoid(QgsProject.instance().ellipsoid())

    if is_distance:
        total = 0.0
        for i in range(1, len(points)):
            total += da.measureLine(points[i-1], points[i])
        units = [
            (1.0, "m"), (1/1000, "km"), (1/1609.344, "mi"),
            (3.28084, "ft"), (1.0, "°")
        ]
        if 0 <= unit_idx < len(units):
            factor, unit_label = units[unit_idx]
        else:
            factor, unit_label = 1.0, "m"
        return f"Distance: {total * factor:.4f} {unit_label}"
    else:
        if len(points) >= 3:
            pts = points + [points[0]]
            poly = QgsGeometry.fromPolygonXY([pts])
            area = da.measureArea(poly)
            return f"Area: {area:.4f} m²  ({area/10000:.4f} ha)"
        return "Result: --"


def generate_grid_layer(canvas, grid_type_name: str, width: float, height: float):
    """Generates a polygon grid covering the current canvas extent."""
    extent = canvas.extent()
    type_map = {
        "Rectangle": 0,
        "Diamond": 1,
        "Hexagon (Flat-top)": 4,
        "Hexagon (Pointy-top)": 5,
    }
    grid_type = type_map.get(grid_type_name, 0)
    params = {
        "TYPE": grid_type,
        "EXTENT": f"{extent.xMinimum()},{extent.xMaximum()},{extent.yMinimum()},{extent.yMaximum()}"
                  f" [{canvas.mapSettings().destinationCrs().authid()}]",
        "HSPACING": width,
        "VSPACING": height,
        "HOVERLAY": 0,
        "VOVERLAY": 0,
        "CRS": canvas.mapSettings().destinationCrs(),
        "OUTPUT": "memory:",
    }
    result = processing.run("native:creategrid", params)
    out = result.get("OUTPUT")
    if out:
        out.setName(f"grid_{grid_type_name.replace(' ', '_')}")
    return out
