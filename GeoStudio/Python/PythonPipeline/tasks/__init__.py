# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline Tasks Package
Aggregates and exposes domain-specific pipeline tasks on demand with lazy loading.
"""

import importlib

_EXPORTS = {
    "task_launch_map_layout": (".layout_tasks", "task_launch_map_layout"),
    "task_launch_3d": (".lidar_tasks", "task_launch_3d"),
    "run_pdal_smrf_classification": (".lidar_tasks", "run_pdal_smrf_classification"),
    "task_classify_ground": (".lidar_tasks", "task_classify_ground"),
    "task_classify_buildings": (".lidar_tasks", "task_classify_buildings"),
    "task_classify_veg": (".lidar_tasks", "task_classify_veg"),
    "task_thin_pointcloud": (".lidar_tasks", "task_thin_pointcloud"),
    "task_terrain_analysis": (".terrain_tasks", "task_terrain_analysis"),
    "task_elevation_relief": (".terrain_tasks", "task_elevation_relief"),
    "task_cut_fill": (".terrain_tasks", "task_cut_fill"),
    "task_watershed": (".hydrology_tasks", "task_watershed"),
    "HEX_PALETTE": (".hydrology_tasks", "HEX_PALETTE"),
    "task_satellite_index": (".raster_tasks", "task_satellite_index"),
    "task_clip_raster": (".raster_tasks", "task_clip_raster"),
    "task_raster_stats": (".raster_tasks", "task_raster_stats"),
    "task_viewshed": (".raster_tasks", "task_viewshed"),
    "task_landsat_lst": (".landsat_tasks", "task_landsat_lst"),
    "task_lulc_intelligence": (".lulc_tasks", "task_lulc_intelligence"),
    "LULC_CLASSES": (".lulc_tasks", "LULC_CLASSES"),
    "task_transpose_fields": (".vector_tasks", "task_transpose_fields"),
    "task_vector_geoprocessing": (".vector_tasks", "task_vector_geoprocessing"),
}


def __getattr__(name):
    if name in _EXPORTS:
        mod_rel, func_name = _EXPORTS[name]
        mod = importlib.import_module(mod_rel, package=__name__)
        val = getattr(mod, func_name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_EXPORTS.keys())
