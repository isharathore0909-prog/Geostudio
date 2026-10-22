# -*- coding: utf-8 -*-
"""
GeoStudio - 🗺 Cartography & Interactive Tools Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

CARTOGRAPHY_CATALOG: Dict[str, Any] = {
            "category": "🗺 Cartography & Interactive Tools",
            "subcategories": [
                {
                    "name": "Interactive Canvas Tools",
                    "items": [
                        AlgorithmDefinition(
                            "Interactive Swipe / Curtain Comparison",
                            "carto:swipe_tool",
                            "Cartography & Interactive Tools",
                            "Interactive Canvas Tools",
                            (
                                "Split-screen before/after curtain slider to visually compare"
                                "stacked raster or vector layers."
                            ),
                            "carto_swipe",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Cloud & XYZ Basemap Integrator",
                            "carto:cloud_basemaps",
                            "Cartography & Interactive Tools",
                            "Interactive Canvas Tools",
                            (
                                "One-click addition of OpenStreetMap, Google Satellite, Mapbox,"
                                "and ESRI World Imagery basemaps."
                            ),
                            "carto_basemap",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Measure Distance & Bearing",
                            "native:measure_dist",
                            "Cartography & Interactive Tools",
                            "Interactive Canvas Tools",
                            (
                                "Interactive on-canvas polyline distance and compass bearing"
                                "measurement tool."
                            ),
                            "tools_measure",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Measure Area & Perimeter",
                            "native:measure_area",
                            "Cartography & Interactive Tools",
                            "Interactive Canvas Tools",
                            "Interactive on-canvas polygon area and perimeter measuring tool.",
                            "tools_measure",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Coordinate Capture & DMS Inspector",
                            "native:coord",
                            "Cartography & Interactive Tools",
                            "Interactive Canvas Tools",
                            (
                                "Captures clicked coordinates with real-time DMS, MGRS, and CRS"
                                "readouts."
                            ),
                            "tools_coord",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Print Layout & Atlas",
                    "items": [
                        AlgorithmDefinition(
                            "Print Layout & Map Composer",
                            "carto:layout_composer",
                            "Cartography & Interactive Tools",
                            "Print Layout & Atlas",
                            (
                                "Professional cartographic layout designer with scale bar, north"
                                "arrow, legend, and grid frame."
                            ),
                            "carto_layout",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Generate Vector Grid / Mesh",
                            "native:grid",
                            "Cartography & Interactive Tools",
                            "Print Layout & Atlas",
                            "Creates rectangular, hexagonal, or diamond index grids.",
                            "tools_grid",
                            supports_gpu=False,
                        ),
                    ]
                }
            ]
        }
