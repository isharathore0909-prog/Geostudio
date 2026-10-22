# -*- coding: utf-8 -*-
"""
GeoStudio - 🏔 Terrain & Global Mapper Suite Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

TERRAIN_CATALOG: Dict[str, Any] = {
            "category": "🏔 Terrain & Global Mapper Suite",
            "subcategories": [
                {
                    "name": "Elevation & Profiling",
                    "items": [
                        AlgorithmDefinition(
                            "Elevation Profile & Cross-Section",
                            "terrain:elevation_profile",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Interactive polyline terrain slicing with real-time elevation"
                                "profile, slope, and cross-section graphs."
                            ),
                            "terrain_profile",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Slope",
                            "native:slope",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Calculates terrain steepness (degrees/percent) using Horn's 3x3"
                                "algorithm."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "Aspect",
                            "native:aspect",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            "Calculates compass direction of terrain slopes (0-360 degrees).",
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "Hillshade",
                            "native:hillshade",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Generates shaded relief with multi-directional solar azimuth and"
                                "altitude."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "TRI (Terrain Ruggedness Index)",
                            "native:roughness",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            "Quantifies topographic roughness based on elevation variance.",
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "TPI (Topographic Position Index)",
                            "native:tpi",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Measures elevation relative to surrounding neighborhood (ridges"
                                "vs valleys)."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "TWI (Topographic Wetness Index)",
                            "native:twi",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Predicts soil moisture accumulation and drainage saturation"
                                "zones."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "Curvature (Profile & Planform)",
                            "native:curvature",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Calculates acceleration/deceleration and convergence of water"
                                "flow."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                            requires_halo=True,
                            halo_size=1,
                        ),
                        AlgorithmDefinition(
                            "DEM Symbology & 3D Relief",
                            "native:dem_symbology",
                            "Terrain & Global Mapper Suite",
                            "Elevation & Profiling",
                            (
                                "Global Mapper and ArcGIS style elevation color ramp styler with"
                                "hillshade blending."
                            ),
                            "dem_dialog",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Earthworks & Volumetrics",
                    "items": [
                        AlgorithmDefinition(
                            "Volumetric Analysis & Stage-Storage",
                            "terrain:volumetric_analysis",
                            "Terrain & Global Mapper Suite",
                            "Earthworks & Volumetrics",
                            (
                                "Single-surface hypsometric capacity curves, stockpile volumes,"
                                "pit voids, and datum plane volumetrics."
                            ),
                            "terrain_volumetrics",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Cut & Fill Earthwork Volume",
                            "terrain:cut_fill",
                            "Terrain & Global Mapper Suite",
                            "Earthworks & Volumetrics",
                            (
                                "Calculates net cut and fill volumes between a DEM and a"
                                "horizontal plane or between two temporal DEM surfaces with"
                                "expansion factors and balance plane solver."
                            ),
                            "terrain_cutfill",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Flood & Inundation Simulator",
                            "terrain:flood_sim",
                            "Terrain & Global Mapper Suite",
                            "Earthworks & Volumetrics",
                            (
                                "Simulates dynamic water level rise over DEMs with catchment area"
                                "and flooded volume estimation."
                            ),
                            "terrain_flood",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Contours & Isolines",
                            "gdal:contour",
                            "Terrain & Global Mapper Suite",
                            "Earthworks & Volumetrics",
                            (
                                "Extracts elevation contour isolines with customizable interval,"
                                "index lines, and smoothing."
                            ),
                            "raster_contours",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Georeferencing & Rectification",
                    "items": [
                        AlgorithmDefinition(
                            "Image Rectifier & GCP Georeferencer",
                            "terrain:georeference",
                            "Terrain & Global Mapper Suite",
                            "Georeferencing",
                            (
                                "Interactive Ground Control Point (GCP) alignment with Affine,"
                                "Polynomial, and Thin Plate Spline warping."
                            ),
                            "terrain_georef",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Clip Raster by Extent/Polygon",
                            "gdal:clipraster",
                            "Terrain & Global Mapper Suite",
                            "Georeferencing",
                            (
                                "Clips elevation rasters using bounding boxes or vector polygon"
                                "masks."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                    ]
                }
            ]
        }
