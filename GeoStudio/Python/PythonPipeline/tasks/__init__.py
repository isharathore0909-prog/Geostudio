# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline Tasks Package
Aggregates and exposes domain-specific pipeline tasks across LiDAR, Terrain, Hydrology, Raster, and Vector domains.
"""

from .lidar_tasks import (
    task_launch_3d,
    run_pdal_smrf_classification,
    task_classify_ground,
    task_classify_buildings,
    task_classify_veg,
    task_thin_pointcloud,
)

from .terrain_tasks import (
    task_terrain_analysis,
    task_elevation_relief,
    task_cut_fill,
)

from .hydrology_tasks import (
    task_watershed,
    HEX_PALETTE,
)

from .raster_tasks import (
    task_satellite_index,
    task_clip_raster,
    task_raster_stats,
    task_viewshed,
)

from .landsat_tasks import (
    task_landsat_lst,
)

from .lulc_tasks import (
    task_lulc_intelligence,
    LULC_CLASSES,
)

from .vector_tasks import (
    task_transpose_fields,
    task_vector_geoprocessing,
)

__all__ = [
    "task_launch_3d",
    "run_pdal_smrf_classification",
    "task_classify_ground",
    "task_classify_buildings",
    "task_classify_veg",
    "task_thin_pointcloud",
    "task_terrain_analysis",
    "task_elevation_relief",
    "task_cut_fill",
    "task_watershed",
    "HEX_PALETTE",
    "task_satellite_index",
    "task_clip_raster",
    "task_raster_stats",
    "task_landsat_lst",
    "task_lulc_intelligence",
    "LULC_CLASSES",
    "task_transpose_fields",
    "task_vector_geoprocessing",
]
