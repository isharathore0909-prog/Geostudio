# -*- coding: utf-8 -*-
"""
GeoStudio - 📦 Data Management & Utilities Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

UTILITIES_CATALOG: Dict[str, Any] = {
            "category": "📦 Data Management & Utilities",
            "subcategories": [
                {
                    "name": "Import & Export",
                    "items": [
                        AlgorithmDefinition(
                            "Import Vector (SHP, GPKG, GeoJSON, KML)",
                            "native:import_vector",
                            "Data Management & Utilities",
                            "Import & Export",
                            "Loads Shapefile, GeoPackage, GeoJSON, KML, and DXF vector layers.",
                            "io_import_vector",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Import Raster (GeoTIFF, HDF, NetCDF)",
                            "native:import_raster",
                            "Data Management & Utilities",
                            "Import & Export",
                            "Loads GeoTIFF, DEM, HDF5, NetCDF, and JP2 rasters.",
                            "io_import_raster",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Import CSV / Delimited Coordinates",
                            "native:import_csv",
                            "Data Management & Utilities",
                            "Import & Export",
                            (
                                "Parses delimited text files with coordinates into point geometry"
                                "layers."
                            ),
                            "io_import_csv",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Export Layer to Format",
                            "native:export_layer",
                            "Data Management & Utilities",
                            "Import & Export",
                            "Converts active layer to Shapefile, GeoTIFF, GeoPackage, or DXF.",
                            "io_export",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Conversion & Projections",
                    "items": [
                        AlgorithmDefinition(
                            "Raster to Vector (Polygonize)",
                            "gdal:polygonize",
                            "Data Management & Utilities",
                            "Conversion & Projections",
                            (
                                "Converts classified raster pixel clusters into vector polygon"
                                "layers."
                            ),
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Vector to Raster (Rasterize)",
                            "gdal:rasterize",
                            "Data Management & Utilities",
                            "Conversion & Projections",
                            "Burns vector polygon or line geometries into a raster grid.",
                            "raster_calc",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Reproject Layer (Warp CRS)",
                            "native:reproject",
                            "Data Management & Utilities",
                            "Conversion & Projections",
                            "Transforms coordinates to a new Coordinate Reference System.",
                            "io_reproject",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Build Pyramid Overviews",
                            "tools:raster_util",
                            "Data Management & Utilities",
                            "Conversion & Projections",
                            (
                                "Builds multi-resolution pyramid overviews for high-speed map"
                                "zooming."
                            ),
                            "tools_raster",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Processing Settings & GPU Engine",
                            "tools:settings",
                            "Data Management & Utilities",
                            "Conversion & Projections",
                            (
                                "Configure GPU memory budgets, RAM thresholds, and CUDA device"
                                "priority."
                            ),
                            "processing_settings",
                            supports_gpu=False,
                        ),
                    ]
                }
            ]
        }
