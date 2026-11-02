# -*- coding: utf-8 -*-
"""
GeoStudio - High-Performance Python Processing Pipeline Bridge
CLI entry point and task dispatcher for LiDAR, Terrain, Hydrology, Remote Sensing, and Vector processing.
Communicates progress and JSON results back to the .NET host process.
"""

import os

for qgis_bin in [r"C:\Program Files\QGIS 3.40.14\bin", r"C:\Program Files\QGIS 3.40.14\apps\qgis-ltr\bin"]:
    if os.path.exists(qgis_bin):
        try:
            os.add_dll_directory(qgis_bin)
        except Exception:
            pass
        os.environ["PATH"] = qgis_bin + os.pathsep + os.environ.get("PATH", "")

# Ensure QGIS PROJ definitions take priority over any system or PostgreSQL installations
for proj_dir in [
    r"C:\Program Files\QGIS 3.40.14\share\proj",
    r"C:\Program Files\QGIS 3.40.14\apps\proj\share\proj"
]:
    if os.path.exists(proj_dir):
        os.environ["PROJ_LIB"] = proj_dir
        os.environ["PROJ_DATA"] = proj_dir
        break

import sys
import argparse
import traceback
import importlib

# Ensure PythonEngine is on sys.path for UI modules (MapLayout, etc.)
_script_dir = os.path.dirname(os.path.abspath(__file__))
for _cand in [
    os.path.abspath(os.path.join(_script_dir, "..", "..", "PythonEngine")),
    os.path.abspath(os.path.join(_script_dir, "..", "PythonEngine")),
    os.path.abspath(os.path.join(_script_dir, "PythonEngine")),
    r"D:\GEO MAP\GeoStudio\PythonEngine"
]:
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)

import common
from common import report_progress, report_result

# Task mapping for lazy dynamic importing (avoids loading unneeded heavy ML/3D modules)
TASK_MODULE_MAP = {
    # Layout & Cartography Tasks
    "launch_map_layout": ("layout_tasks", "task_launch_map_layout"),

    # 3D & LiDAR Tasks
    "launch_3d": ("lidar_tasks", "task_launch_3d"),
    "classify_ground": ("lidar_tasks", "task_classify_ground"),
    "classify_buildings": ("lidar_tasks", "task_classify_buildings"),
    "classify_veg": ("lidar_tasks", "task_classify_veg"),
    "thin": ("lidar_tasks", "task_thin_pointcloud"),

    # Terrain & Earthwork Tasks
    "terrain": ("terrain_tasks", "task_terrain_analysis"),
    "elevation_relief": ("terrain_tasks", "task_elevation_relief"),
    "cut_fill": ("terrain_tasks", "task_cut_fill"),
    "viewshed": ("raster_tasks", "task_viewshed"),

    # Hydrological Modeling Tasks
    "watershed": ("hydrology_tasks", "task_watershed"),
    "hydrology": ("hydrology_tasks", "task_watershed"),

    # Raster & Satellite Remote Sensing Tasks
    "satellite": ("raster_tasks", "task_satellite_index"),
    "clip_raster": ("raster_tasks", "task_clip_raster"),
    "raster_stats": ("raster_tasks", "task_raster_stats"),
    "landsat_lst": ("landsat_tasks", "task_landsat_lst"),
    "split_window_lst": ("landsat_tasks", "task_landsat_lst"),
    "lulc": ("lulc_tasks", "task_lulc_intelligence"),
    "lulc_intelligence": ("lulc_tasks", "task_lulc_intelligence"),

    # Vector & Attribute Geoprocessing Tasks
    "transpose_fields": ("vector_tasks", "task_transpose_fields"),
    "vector_geoprocessing": ("vector_tasks", "task_vector_geoprocessing"),
}


def _get_task_runner(task_name):
    if task_name not in TASK_MODULE_MAP:
        return None
    mod_name, func_name = TASK_MODULE_MAP[task_name]
    mod = importlib.import_module(f"tasks.{mod_name}")
    return getattr(mod, func_name)


def main():
    parser = argparse.ArgumentParser(description="GeoStudio Python Pipeline Bridge")
    parser.add_argument("--task", required=True, help="Task identifier")
    parser.add_argument("--input", help="Primary input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--mode", default=None, help="Sub-mode identifier")
    parser.add_argument("--param1", help="Generic parameter 1")
    parser.add_argument("--param2", help="Generic parameter 2")

    args = parser.parse_args()

    runner = _get_task_runner(args.task)
    if not runner:
        report_result(False, {}, f"Unknown task: {args.task}")
        sys.exit(1)

    try:
        runner(args)
    except Exception as ex:
        traceback.print_exc(file=sys.stderr)
        report_result(False, {}, str(ex))
        sys.exit(1)


if __name__ == "__main__":
    main()
