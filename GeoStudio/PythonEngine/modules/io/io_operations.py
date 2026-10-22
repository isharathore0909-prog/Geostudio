# -*- coding: utf-8 -*-
"""
GeoStudio / GeoAnalytica - Import/Export & Reprojection Engine
Contains vector writing, layer reprojection, and merging routines.
"""

from qgis.core import (
    QgsVectorFileWriter, QgsCoordinateTransformContext, QgsCoordinateReferenceSystem,
    QgsProject
)
import processing


def export_vector_layer(layer, path: str, driver_name: str, dest_crs_str: str, selected_only: bool = False):
    """Exports a vector layer to file with specified format and CRS."""
    dest_crs = QgsCoordinateReferenceSystem(dest_crs_str)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = driver_name
    options.fileEncoding = "UTF-8"
    options.ct = None
    if selected_only:
        options.onlySelectedFeatures = True

    error, err_msg, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, QgsCoordinateTransformContext(), options
    )
    return error == QgsVectorFileWriter.NoError, err_msg


def reproject_vector_layer(layer, target_crs_str: str):
    """Reprojects a vector layer into memory using native:reprojectlayer."""
    params = {"INPUT": layer, "TARGET_CRS": target_crs_str, "OUTPUT": "memory:"}
    result = processing.run("native:reprojectlayer", params)
    out = result.get("OUTPUT")
    if out:
        out.setName(f"{layer.name()}_{target_crs_str.replace(':', '_')}")
        QgsProject.instance().addMapLayer(out)
        return out
    return None


def merge_vector_layers(layer1, layer2):
    """Merges two vector layers into memory using native:mergevectorlayers."""
    params = {"LAYERS": [layer1, layer2], "CRS": None, "OUTPUT": "memory:"}
    result = processing.run("native:mergevectorlayers", params)
    out = result.get("OUTPUT")
    if out:
        out.setName(f"{layer1.name()}_{layer2.name()}_merged")
        QgsProject.instance().addMapLayer(out)
        return out
    return None
