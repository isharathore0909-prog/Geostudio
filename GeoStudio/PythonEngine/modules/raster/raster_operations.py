# -*- coding: utf-8 -*-
"""
GeoStudio - Raster Operations & Algorithm Invocation
Invokes native QGIS processing algorithms for slope, aspect, hillshade, roughness, contours, and reprojection.
"""

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
import processing
from core.elevation_styler import ElevationStyler


def run_raster_processing_algo(algo: str, params: dict, name: str, progress_bar=None, iface=None, parent_widget=None):
    """Generic execution wrapper with progress updates and layer styling."""
    if progress_bar:
        progress_bar.setFormat(f"Running {name}...")
        progress_bar.setValue(20)
    try:
        result = processing.run(algo, params)
        output = result.get("OUTPUT") or result.get("output")
        if output:
            if isinstance(output, str):
                if output.endswith(".shp") or "memory:" in output or "??" in output:
                    l = QgsVectorLayer(output, name, "ogr")
                else:
                    l = QgsRasterLayer(output, name)
                if l.isValid():
                    if name.endswith("_aspect"):
                        ElevationStyler.apply_aspect_colormap(l)
                    elif name.endswith("_slope"):
                        ElevationStyler.apply_slope_colormap(l)
                    QgsProject.instance().addMapLayer(l)
            elif hasattr(output, "isValid"):
                output.setName(name)
                if name.endswith("_aspect"):
                    ElevationStyler.apply_aspect_colormap(output)
                elif name.endswith("_slope"):
                    ElevationStyler.apply_slope_colormap(output)
                QgsProject.instance().addMapLayer(output)
        if progress_bar:
            progress_bar.setValue(100)
            progress_bar.setFormat(f"✓ {name} done")
        if iface and hasattr(iface, "messageBar") and iface.messageBar():
            iface.messageBar().pushSuccess("GeoStudio", f"{name} completed!")
    except Exception as e:
        if progress_bar:
            progress_bar.setFormat("Error")
        QMessageBox.critical(parent_widget, "Error", str(e))


def get_raster_stats_text(layer: QgsRasterLayer) -> str:
    """Formats human-readable summary of raster dimensions, resolution, and elevation range."""
    stats_lines = [
        f"Raster: {layer.name()}", f"CRS: {layer.crs().authid()}",
        f"Bands: {layer.bandCount()}", f"Dimensions: {layer.width()} x {layer.height()} px",
        f"Pixel size: {layer.rasterUnitsPerPixelX():.6f} x {layer.rasterUnitsPerPixelY():.6f}",
        ""
    ]
    stats = ElevationStyler.get_valid_elevation_stats(layer, 1)
    if stats:
        stats_lines.append(
            f"🏔 Valid Elevation Data:\n"
            f"  Min: {stats['min']:.4f} m   Max: {stats['max']:.4f} m\n"
            f"  Mean: {stats['mean']:.4f} m  StdDev: {stats['std_dev']:.4f}\n"
            f"  2%-98% Stretch: {stats['p2']:.2f} m – {stats['p98']:.2f} m\n"
            f"  NoData Defined: {'Yes (' + str(stats['nodata_val']) + ')' if stats['has_nodata'] else 'None'}"
        )
    return "\n".join(stats_lines)
