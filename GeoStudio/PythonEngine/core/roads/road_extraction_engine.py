# -*- coding: utf-8 -*-
"""
GeoStudio - Road & Transportation LiDAR Engineering Engine
Unified Facade coordinating modular transportation corridor engines:

Modular Components:
- road_models.py: Data classes (StationMarker, CorridorHazard, CorridorGeometryResult, ProcessingContext)
- road_io.py: Spatial reference handling and OGR vector writing
- road_surface_engine.py: RoadSurfaceEngine (ASPRS Class 11 pavement classification)
- road_corridor_engine.py: RoadCorridorEngine (3D centerline, curbs, station chainage)
- road_condition_engine.py: RoadConditionEngine (grade profiling, IRI roughness, vehicle clearance)
"""

from typing import Dict, Any, Callable, Optional, List, Tuple
import numpy as np
from osgeo import osr

from .road_models import (
    ProcessingContext,
    StationMarker,
    CorridorHazard,
    CorridorGeometryResult,
)
from .road_io import (
    RoadSpatialReference,
    RoadVectorWriter,
    RoadDataLoader,
)
from .road_surface_engine import (
    RoadGroundEstimator,
    RoadPavementClassifier,
    RoadSurfaceEngine,
)
from .road_corridor_engine import (
    RoadAlignmentTracer,
    RoadCorridorEngine,
)
from .road_condition_engine import (
    RoadCorridorAuditor,
    RoadConditionEngine,
)


class RoadExtractionEngine:
    """Unified facade coordinating road surface classification, alignment vectorization, and safety audits."""

    # 1. Road Surface & Pavement Classification (ASPRS Class 11)
    @classmethod
    def classify_road_surface(
        cls,
        input_las_path: str,
        output_las_path: Optional[str] = None,
        output_vector_path: Optional[str] = None,
        road_centerline_vector: Optional[str] = None,
        max_corridor_width_m: float = 12.0,
        max_hag_m: float = 0.35,
        min_planarity: float = 0.65,
        max_roughness_m: float = 0.08,
        min_verticality: float = 0.85,
        min_intensity: Optional[float] = None,
        max_intensity: Optional[float] = None,
        min_corridor_area_m2: float = 20.0,
        export_footprint_polygon: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Classifies asphalt and pavement points into ASPRS Class 11 (Road Surface)."""
        return RoadSurfaceEngine.classify_road_surface(
            input_las_path=input_las_path,
            output_las_path=output_las_path,
            output_vector_path=output_vector_path,
            road_centerline_vector=road_centerline_vector,
            max_corridor_width_m=max_corridor_width_m,
            max_hag_m=max_hag_m,
            min_planarity=min_planarity,
            max_roughness_m=max_roughness_m,
            min_verticality=min_verticality,
            min_intensity=min_intensity,
            max_intensity=max_intensity,
            min_corridor_area_m2=min_corridor_area_m2,
            export_footprint_polygon=export_footprint_polygon,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    # 2. Road Alignment, Curbs & Corridor Vectorization
    @classmethod
    def extract_road_corridor(
        cls,
        input_source: str,
        output_vector_path: str,
        station_interval_m: float = 25.0,
        corridor_search_step_m: float = 5.0,
        detect_curbs: bool = True,
        curb_step_height_m: float = 0.12,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Extracts 3D continuous road centerlines, curbs, and equidistant station chainage markers."""
        return RoadCorridorEngine.extract_road_corridor(
            input_source=input_source,
            output_vector_path=output_vector_path,
            station_interval_m=station_interval_m,
            corridor_search_step_m=corridor_search_step_m,
            detect_curbs=detect_curbs,
            curb_step_height_m=curb_step_height_m,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    # 3. Road Grade, Roughness & Overhead Vehicle Clearance Audit
    @classmethod
    def analyze_road_condition(
        cls,
        road_centerline_source: str,
        lidar_source: str,
        output_vector_path: str,
        max_design_grade_pct: float = 8.0,
        critical_grade_pct: float = 12.0,
        vehicle_clearance_height_m: float = 4.80,
        critical_clearance_height_m: float = 4.00,
        corridor_width_m: float = 8.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Audits longitudinal grades, pavement roughness, surface depressions, and overhead vehicle clearances."""
        return RoadConditionEngine.analyze_road_condition(
            road_centerline_source=road_centerline_source,
            lidar_source=lidar_source,
            output_vector_path=output_vector_path,
            max_design_grade_pct=max_design_grade_pct,
            critical_grade_pct=critical_grade_pct,
            vehicle_clearance_height_m=vehicle_clearance_height_m,
            critical_clearance_height_m=critical_clearance_height_m,
            corridor_width_m=corridor_width_m,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    # Compatibility Helpers
    @classmethod
    def _load_road_points(cls, source_path: str) -> np.ndarray:
        pts, _ = RoadDataLoader.load_road_points_with_srs(source_path)
        return pts

    @classmethod
    def _load_centerline_coords(cls, source_path: str) -> np.ndarray:
        pts, _ = RoadDataLoader.load_centerline_coords_with_srs(source_path)
        return pts

    @classmethod
    def _export_pavement_boundary(cls, points: np.ndarray, out_path: str):
        RoadVectorWriter.write_pavement_boundary(points, out_path)


__all__ = [
    "RoadExtractionEngine",
    "RoadSurfaceEngine",
    "RoadCorridorEngine",
    "RoadConditionEngine",
    "RoadGroundEstimator",
    "RoadPavementClassifier",
    "RoadAlignmentTracer",
    "RoadCorridorAuditor",
    "RoadSpatialReference",
    "RoadVectorWriter",
    "RoadDataLoader",
    "StationMarker",
    "CorridorHazard",
    "CorridorGeometryResult",
    "ProcessingContext",
]
