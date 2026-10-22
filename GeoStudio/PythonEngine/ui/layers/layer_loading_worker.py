# -*- coding: utf-8 -*-
"""
GeoStudio - Layer Loading Worker Routines
Implements loading operations for LiDAR Point Clouds, Raster/DEMs, Vectors, and CSVs.
"""

import os
from core.elevation_styler import ElevationStyler


def load_point_cloud_layer(file_path: str, progress_cb=None):
    """Loads a LAS/LAZ point cloud dataset into QgsPointCloudLayer."""
    from qgis.core import QgsPointCloudLayer, QgsCoordinateReferenceSystem
    from core.lidar_styler import LidarStyler
    from core.point_cloud_indexer import PointCloudIndexer

    name = os.path.splitext(os.path.basename(file_path))[0]
    clean_name = name.replace(".copc", "")

    copc_path = None
    if file_path.lower().endswith(".copc.laz"):
        copc_path = file_path
    else:
        target_copc = PointCloudIndexer.get_target_copc_path(file_path)
        if os.path.exists(target_copc) and os.path.getsize(target_copc) > 1024:
            copc_path = target_copc
        else:
            if progress_cb:
                progress_cb(15, "Generating Cloud-Optimized Point Cloud (.copc.laz) for discrete 3D point sprites...")
            copc_path = PointCloudIndexer.ensure_copc_index(file_path, progress_callback=progress_cb)

    source_path = copc_path if (copc_path and os.path.exists(copc_path)) else file_path
    provider = "copc" if (copc_path and os.path.exists(copc_path)) else "pdal"

    if progress_cb:
        progress_cb(75, f"Mounting discrete 3D point cloud layer ({provider.upper()})...")
    layer = QgsPointCloudLayer(source_path, f"{clean_name} [LiDAR]", provider)

    if not layer or not layer.isValid():
        alt_provider = "pdal" if provider == "copc" else "copc"
        layer = QgsPointCloudLayer(source_path, f"{clean_name} [LiDAR]", alt_provider)

    if not layer or not layer.isValid():
        raise RuntimeError(f"Could not initialize discrete 3D point cloud layer for:\n{file_path}")

    if progress_cb:
        progress_cb(85, "Configuring spatial reference system...")
    if not layer.crs().isValid() or not layer.crs().authid():
        ext = layer.extent()
        if abs(ext.xMinimum()) <= 180.0 and abs(ext.yMaximum()) <= 90.0:
            layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        else:
            layer.setCrs(QgsCoordinateReferenceSystem("EPSG:32643"))

    layer.setCustomProperty("original_las_path", file_path)
    layer.setCustomProperty("is_lidar_layer", True)
    if copc_path:
        layer.setCustomProperty("copc_path", copc_path)

    try:
        if hasattr(layer, "setMaximumScreenError"):
            layer.setMaximumScreenError(1.0)
        if hasattr(layer, "setPointBudget"):
            layer.setPointBudget(20000000)
    except Exception:
        pass

    if progress_cb:
        progress_cb(92, "Styling discrete 3D point cloud sprites (True Color & Elevation)...")
    LidarStyler.auto_style(layer, point_size=3.5)

    return layer


def load_raster_layer(file_path: str, progress_cb=None):
    """Loads a GeoTIFF or DEM raster layer into QgsRasterLayer."""
    from qgis.core import QgsRasterLayer, QgsCoordinateReferenceSystem

    name = os.path.splitext(os.path.basename(file_path))[0]
    if progress_cb:
        progress_cb(35, "Reading raster dataset bands & extent...")

    layer = QgsRasterLayer(file_path, name)
    if not layer or not layer.isValid():
        raise RuntimeError(f"Invalid raster file: {file_path}")

    orig_crs = layer.crs()
    if not orig_crs.isValid() or not orig_crs.authid():
        ext = layer.extent()
        if ext.xMinimum() > 180.0 or ext.yMinimum() > 90.0:
            orig_crs = QgsCoordinateReferenceSystem("EPSG:32643")
        else:
            orig_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        layer.setCrs(orig_crs)

    if progress_cb:
        progress_cb(75, "Analyzing elevation statistics & terrain structure...")
    if ElevationStyler.is_dem_or_elevation(layer):
        if progress_cb:
            progress_cb(85, "Generating Global Mapper 3D Shaded Relief...")
        relief_path = ElevationStyler.generate_3d_shaded_relief_file(file_path, preset_key="GLOBAL_MAPPER_ATLAS")
        if relief_path and os.path.isfile(relief_path):
            relief_layer = QgsRasterLayer(relief_path, f"{name} [DEM]")
            if relief_layer and relief_layer.isValid():
                layer = relief_layer
                abs_file = os.path.abspath(file_path)
                layer.setCustomProperty("raw_dem_source", abs_file)
                layer.setCustomProperty("is_3d_relief", True)
                layer._raw_dem_source = abs_file
                layer._is_3d_relief = True
                if orig_crs.isValid():
                    layer.setCrs(orig_crs)
                ElevationStyler.apply_resampling(layer, mode="smooth")
            else:
                ElevationStyler.apply_elevation_colormap(layer, preset_key="GLOBAL_MAPPER_ATLAS")
                ElevationStyler.apply_resampling(layer, mode="smooth")
        else:
            ElevationStyler.apply_elevation_colormap(layer, preset_key="GLOBAL_MAPPER_ATLAS")
            ElevationStyler.apply_resampling(layer, mode="smooth")
    else:
        if progress_cb:
            progress_cb(90, "Configuring crisp imagery resampling...")
        ElevationStyler.apply_resampling(layer, mode="sharp")

    return layer


def load_vector_layer(file_path: str, progress_cb=None):
    """Loads a shapefile, GeoPackage, or GeoJSON vector layer into QgsVectorLayer."""
    from qgis.core import QgsVectorLayer
    name = os.path.splitext(os.path.basename(file_path))[0]
    if progress_cb:
        progress_cb(40, "Reading vector geometry features & table...")

    layer = QgsVectorLayer(file_path, name, "ogr")
    if layer and layer.isValid():
        feat_count = layer.featureCount()
        if progress_cb:
            progress_cb(85, f"Loaded {feat_count:,} features. Finalizing...")
        return layer
    raise RuntimeError(f"Invalid vector layer: {file_path}")


def load_csv_layer(file_path: str, x_field: str = "longitude", y_field: str = "latitude", progress_cb=None):
    """Loads a CSV point table into QgsVectorLayer delimited text."""
    from qgis.core import QgsVectorLayer
    name = os.path.splitext(os.path.basename(file_path))[0]
    if progress_cb:
        progress_cb(40, "Parsing CSV points & coordinates...")

    uri = f"file:///{file_path.replace(os.sep, '/')}?delimiter=,&xField={x_field}&yField={y_field}&crs=epsg:4326&useHeader=yes"
    layer = QgsVectorLayer(uri, name, "delimitedtext")
    if layer and layer.isValid():
        return layer
    raise RuntimeError("Could not parse CSV. Verify X/Y coordinate column names.")
