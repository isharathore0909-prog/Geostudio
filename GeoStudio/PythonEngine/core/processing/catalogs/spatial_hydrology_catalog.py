# -*- coding: utf-8 -*-
"""
GeoStudio - 📐 Spatial & Hydrology Analyst Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

SPATIAL_HYDROLOGY_CATALOG: Dict[str, Any] = {
            "category": "📐 Spatial & Hydrology Analyst",
            "subcategories": [
                {
                    "name": "Hydrological Modeling",
                    "items": [
                        AlgorithmDefinition(
                            "Fill Sinks (Depressions)",
                            "hydrology:fillsinks",
                            "Spatial & Hydrology Analyst",
                            "Hydrological Modeling",
                            (
                                "Fills digital elevation model depressions and sinks to establish"
                                "continuous flow paths."
                            ),
                            "raster_hydro",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Flow Direction (D8 / D-Infinity)",
                            "hydrology:flowdir",
                            "Spatial & Hydrology Analyst",
                            "Hydrological Modeling",
                            (
                                "Calculates steepest slope flow direction per cell towards"
                                "neighbor cells."
                            ),
                            "raster_hydro",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Flow Accumulation",
                            "hydrology:flowaccum",
                            "Spatial & Hydrology Analyst",
                            "Hydrological Modeling",
                            "Computes total upslope drainage area contributing to each cell.",
                            "raster_hydro",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Stream Network & Order (Strahler)",
                            "hydrology:stream_network",
                            "Spatial & Hydrology Analyst",
                            "Hydrological Modeling",
                            (
                                "Extracts hierarchical stream channels from flow accumulation"
                                "using Strahler and Shreve ordering."
                            ),
                            "raster_hydro",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Watershed & Basin Delineation",
                            "hydrology:watershed",
                            "Spatial & Hydrology Analyst",
                            "Hydrological Modeling",
                            (
                                "Delineates complete hydrological drainage basins and catchment areas."
                            ),
                            "raster_hydro",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Spatial Interpolation",
                    "items": [
                        AlgorithmDefinition(
                            "Ordinary & Universal Kriging",
                            "spatial:kriging",
                            "Spatial & Hydrology Analyst",
                            "Spatial Interpolation",
                            (
                                "Geostatistical point interpolation with semivariogram fitting and"
                                "prediction error variance."
                            ),
                            "spatial_interp",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Inverse Distance Weighting (IDW)",
                            "spatial:idw",
                            "Spatial & Hydrology Analyst",
                            "Spatial Interpolation",
                            (
                                "Calculates cell values using linearly weighted combination of"
                                "sample points."
                            ),
                            "spatial_interp",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Thin Plate Spline Interpolation",
                            "spatial:spline",
                            "Spatial & Hydrology Analyst",
                            "Spatial Interpolation",
                            (
                                "Fits minimum curvature surface passing exactly through sample"
                                "points."
                            ),
                            "spatial_interp",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Visibility & Multi-Criteria",
                    "items": [
                        AlgorithmDefinition(
                            "3D Viewshed & Line of Sight",
                            "spatial:viewshed",
                            "Spatial & Hydrology Analyst",
                            "Visibility & Multi-Criteria",
                            (
                                "Calculates visible terrain areas from observer points accounting"
                                "for target height, Earth curvature, and refraction."
                            ),
                            "raster_viewshed",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Multi-Criteria Decision Analysis (AHP)",
                            "spatial:weighted_overlay",
                            "Spatial & Hydrology Analyst",
                            "Visibility & Multi-Criteria",
                            (
                                "Weighted overlay suitability modeling combining reclassified"
                                "factor rasters with Analytic Hierarchy Process."
                            ),
                            "raster_calc",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Zonal Statistics",
                            "native:zonalstats",
                            "Spatial & Hydrology Analyst",
                            "Visibility & Multi-Criteria",
                            (
                                "Calculates summary statistics (mean, sum, min, max, std) of"
                                "raster values within polygon zones."
                            ),
                            "raster_stats",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Focal Statistics (Neighborhood)",
                            "native:focalmean",
                            "Spatial & Hydrology Analyst",
                            "Visibility & Multi-Criteria",
                            (
                                "Calculates neighborhood moving window statistics (mean, median,"
                                "majority)."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                    ]
                }
            ]
        }
