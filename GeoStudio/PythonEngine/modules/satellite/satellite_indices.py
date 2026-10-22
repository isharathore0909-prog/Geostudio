# -*- coding: utf-8 -*-
"""
GeoStudio / GeoAnalytica - Satellite Indices & Hyperspectral Processing Core
Raster calculation, pseudocolor styling, composite generation, and PCA routines.
"""

import tempfile
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsContrastEnhancement,
    QgsRasterBandStats, QgsMultiBandColorRenderer,
    QgsSingleBandPseudoColorRenderer, QgsColorRampShader
)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
import processing


def apply_pseudocolor_ramp(layer):
    """Apply a blue-green-yellow-red pseudocolor ramp to a single-band raster."""
    provider = layer.dataProvider()
    stats = provider.bandStatistics(1)
    min_val = stats.minimumValue
    max_val = stats.maximumValue

    color_ramp = QgsColorRampShader()
    color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
    items = [
        QgsColorRampShader.ColorRampItem(min_val, Qt.blue, "Low"),
        QgsColorRampShader.ColorRampItem((min_val + max_val) / 2, Qt.yellow, "Mid"),
        QgsColorRampShader.ColorRampItem(max_val, Qt.red, "High"),
    ]
    color_ramp.setColorRampItemList(items)

    renderer = QgsSingleBandPseudoColorRenderer(provider, 1)
    renderer.setClassificationMin(min_val)
    renderer.setClassificationMax(max_val)
    renderer.setShader(color_ramp)
    layer.setRenderer(renderer)


def run_raster_calculation(formula: str, layer: QgsRasterLayer, output_name: str):
    """Run QGIS Raster Calculator with given formula and apply pseudocolor ramp."""
    if not layer:
        return None, "Select a raster layer."

    entries = []
    for b in range(1, layer.bandCount() + 1):
        entry = QgsRasterCalculatorEntry()
        entry.ref = f"{layer.name()}@{b}"
        entry.raster = layer
        entry.bandNumber = b
        entries.append(entry)

    extent = layer.extent()
    crs = layer.crs()
    cols = layer.width()
    rows = layer.height()

    tmp = tempfile.mktemp(suffix=".tif")
    calc = QgsRasterCalculator(formula, tmp, "GTiff", extent, crs, cols, rows, entries)
    result_code = calc.processCalculation()

    if result_code == QgsRasterCalculator.Success:
        result_layer = QgsRasterLayer(tmp, output_name)
        if result_layer.isValid():
            apply_pseudocolor_ramp(result_layer)
            QgsProject.instance().addMapLayer(result_layer)
            return result_layer, None
    return None, f"Raster Calculator failed (code {result_code}). Check formula: {formula}"


def apply_false_color_composite(layer: QgsRasterLayer, r_band: int, g_band: int, b_band: int):
    """Applies multi-band color composite with auto contrast stretch."""
    if not layer:
        return False, "Select a raster layer."

    n_bands = layer.bandCount()
    if max(r_band, g_band, b_band) > n_bands:
        return False, f"Layer only has {n_bands} bands. Adjust band numbers."

    renderer = QgsMultiBandColorRenderer(layer.dataProvider(), r_band, g_band, b_band)

    def stretch_band(band_no):
        stats = layer.dataProvider().bandStatistics(band_no, QgsRasterBandStats.Min | QgsRasterBandStats.Max)
        ce = QgsContrastEnhancement(layer.dataProvider().dataType(band_no))
        ce.setMinimumValue(stats.minimumValue)
        ce.setMaximumValue(stats.maximumValue)
        ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
        return ce

    renderer.setRedContrastEnhancement(stretch_band(r_band))
    renderer.setGreenContrastEnhancement(stretch_band(g_band))
    renderer.setBlueContrastEnhancement(stretch_band(b_band))

    layer.setRenderer(renderer)
    layer.triggerRepaint()
    return True, f"False color composite applied: R={r_band} G={g_band} B={b_band}"


def run_pca(layer: QgsRasterLayer, max_components: int = 10):
    """Executes GDAL PCA on raster layer."""
    if not layer:
        return None, "Select a raster layer."
    try:
        params = {
            "INPUT": layer,
            "COMPONENTS": min(layer.bandCount(), max_components),
            "OUTPUT": "TEMPORARY_OUTPUT"
        }
        result = processing.run("gdal:pcaanalysis", params)
        out = result.get("OUTPUT")
        if out:
            pca_layer = QgsRasterLayer(out, f"{layer.name()}_PCA")
            if pca_layer.isValid():
                QgsProject.instance().addMapLayer(pca_layer)
                return pca_layer, f"✓ PCA completed: {layer.bandCount()} → {params['COMPONENTS']} components"
    except Exception as e:
        return None, f"⚠ GDAL PCA error: {e}"
    return None, "PCA execution yielded no output."
