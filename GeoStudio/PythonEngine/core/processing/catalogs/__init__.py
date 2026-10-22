# -*- coding: utf-8 -*-
"""
GeoStudio - Processing Catalogs Package
"""

from .remote_sensing_catalog import REMOTE_SENSING_CATALOG
from .terrain_catalog import TERRAIN_CATALOG
from .spatial_hydrology_catalog import SPATIAL_HYDROLOGY_CATALOG
from .vector_catalog import VECTOR_CATALOG
from .lidar_catalog import LIDAR_CATALOG
from .cartography_catalog import CARTOGRAPHY_CATALOG
from .forestry_catalog import FORESTRY_CATALOG
from .utilities_catalog import UTILITIES_CATALOG




ALL_CATALOGS = [
    REMOTE_SENSING_CATALOG,
    TERRAIN_CATALOG,
    SPATIAL_HYDROLOGY_CATALOG,
    VECTOR_CATALOG,
    LIDAR_CATALOG,
    FORESTRY_CATALOG,
    CARTOGRAPHY_CATALOG,
    UTILITIES_CATALOG,
]

__all__ = [
    "REMOTE_SENSING_CATALOG",
    "TERRAIN_CATALOG",
    "SPATIAL_HYDROLOGY_CATALOG",
    "VECTOR_CATALOG",
    "LIDAR_CATALOG",
    "FORESTRY_CATALOG",
    "CARTOGRAPHY_CATALOG",
    "UTILITIES_CATALOG",
    "ALL_CATALOGS",
]

