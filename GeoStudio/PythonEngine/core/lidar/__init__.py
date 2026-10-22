# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR & 3D Point Cloud Processing Package
Includes styling, COPC indexing, octree optimization, and rasterization.
"""

try:
    from .lidar_styler import LidarStyler
except ImportError:
    LidarStyler = None

from .point_cloud_indexer import PointCloudIndexer
from .point_cloud_optimizer import PointCloudOptimizer

try:
    from .point_cloud_rasterizer import PointCloudRasterizer
except ImportError:
    PointCloudRasterizer = None

from .powerline_classifier import PowerlineClassifier
from .vegetation_clearance_engine import VegetationClearanceEngine
from .building_roof_engine import BuildingRoofEngine

try:
    from ..roads import (
        RoadExtractionEngine,
        RoadSurfaceEngine,
        RoadCorridorEngine,
        RoadConditionEngine,
    )
except ImportError:
    RoadExtractionEngine = None
    RoadSurfaceEngine = None
    RoadCorridorEngine = None
    RoadConditionEngine = None

__all__ = [
    "LidarStyler",
    "PointCloudIndexer",
    "PointCloudOptimizer",
    "PointCloudRasterizer",
    "PowerlineClassifier",
    "VegetationClearanceEngine",
    "BuildingRoofEngine",
    "RoadExtractionEngine",
    "RoadSurfaceEngine",
    "RoadCorridorEngine",
    "RoadConditionEngine",
]
