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

import common
from common import report_progress, report_result

from tasks import (
    task_launch_3d,
    task_classify_ground,
    task_classify_buildings,
    task_classify_veg,
    task_thin_pointcloud,
    task_terrain_analysis,
    task_elevation_relief,
    task_cut_fill,
    task_watershed,
    task_satellite_index,
    task_clip_raster,
    task_raster_stats,
    task_viewshed,
    task_landsat_lst,
    task_lulc_intelligence,
    task_transpose_fields,
    task_vector_geoprocessing,
)

TASK_REGISTRY = {
    # 3D & LiDAR Tasks
    "launch_3d": task_launch_3d,
    "classify_ground": task_classify_ground,
    "classify_buildings": task_classify_buildings,
    "classify_veg": task_classify_veg,
    "thin": task_thin_pointcloud,

    # Terrain & Earthwork Tasks
    "terrain": task_terrain_analysis,
    "elevation_relief": task_elevation_relief,
    "cut_fill": task_cut_fill,
    "viewshed": task_viewshed,

    # Hydrological Modeling Tasks
    "watershed": task_watershed,
    "hydrology": task_watershed,

    # Raster & Satellite Remote Sensing Tasks
    "satellite": task_satellite_index,
    "clip_raster": task_clip_raster,
    "raster_stats": task_raster_stats,
    "landsat_lst": task_landsat_lst,
    "split_window_lst": task_landsat_lst,
    "lulc": task_lulc_intelligence,
    "lulc_intelligence": task_lulc_intelligence,

    # Vector & Attribute Geoprocessing Tasks
    "transpose_fields": task_transpose_fields,
    "vector_geoprocessing": task_vector_geoprocessing,
}


def main():
    parser = argparse.ArgumentParser(description="GeoStudio Python Pipeline Bridge")
    parser.add_argument("--task", required=True, help="Task identifier")
    parser.add_argument("--input", help="Primary input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--mode", default=None, help="Sub-mode identifier")
    parser.add_argument("--param1", help="Generic parameter 1")
    parser.add_argument("--param2", help="Generic parameter 2")

    args = parser.parse_args()

    runner = TASK_REGISTRY.get(args.task)
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
