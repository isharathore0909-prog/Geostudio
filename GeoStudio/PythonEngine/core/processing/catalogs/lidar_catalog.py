# -*- coding: utf-8 -*-
"""
GeoStudio - ☁️ LiDAR & Point Cloud Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

LIDAR_CATALOG: Dict[str, Any] = {
            "category": "☁️ LiDAR & Point Cloud",
            "subcategories": [
                {
                    "name": "Point Classification",
                    "items": [
                        AlgorithmDefinition(
                            "Classify Ground Points (CSF / TIN)",
                            "lidar:classify_ground",
                            "LiDAR & Point Cloud",
                            "Point Classification",
                            (
                                "Cloth Simulation / Progressive TIN ground filter separating bare-"
                                "earth from above-ground objects."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Classify Buildings & Roofs",
                            "lidar:classify_buildings",
                            "LiDAR & Point Cloud",
                            "Point Classification",
                            "Segments planar building roofs and structural footprints.",
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Classify Vegetation Canopy",
                            "lidar:classify_veg",
                            "LiDAR & Point Cloud",
                            "Point Classification",
                            "Separates low, medium, and high canopy vegetation returns.",
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Surface Extraction & DTM",
                    "items": [
                        AlgorithmDefinition(
                            "Generate Bare-Earth DTM",
                            "lidar:generate_dtm",
                            "LiDAR & Point Cloud",
                            "Surface Extraction & DTM",
                            (
                                "Interpolates bare-earth ground points into high-resolution"
                                "Digital Terrain Model raster."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Generate Surface DSM (First Returns)",
                            "lidar:generate_dsm",
                            "LiDAR & Point Cloud",
                            "Surface Extraction & DTM",
                            (
                                "Builds surface model including tree crowns and buildings from"
                                "first returns."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Canopy Height Model (CHM = DSM - DTM)",
                            "lidar:chm",
                            "LiDAR & Point Cloud",
                            "Surface Extraction & DTM",
                            (
                                "Calculates Normalized Canopy Height Model for forestry and tree"
                                "height measurements."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Point Cloud Filters & 3D Tools",
                    "items": [
                        AlgorithmDefinition(
                            "Statistical Outlier Noise Filter",
                            "lidar:outlier_filter",
                            "LiDAR & Point Cloud",
                            "Point Cloud Filters",
                            (
                                "Removes laser flight noise, birds, and high/low atmospheric point"
                                "anomalies."
                            ),
                            "raster_terrain",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Point Cloud Density Decimation",
                            "lidar:thinning",
                            "LiDAR & Point Cloud",
                            "Point Cloud Filters",
                            (
                                "Decimates point cloud volume while preserving morphological"
                                "surface edges."
                            ),
                            "raster_terrain",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Clip Point Cloud to Polygon",
                            "lidar:clip",
                            "LiDAR & Point Cloud",
                            "Point Cloud Filters",
                            "Clips point cloud coordinates to polygon or bounding box.",
                            "raster_terrain",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Interactive 3D Point Cloud Visualizer",
                            "lidar:3d_viewer",
                            "LiDAR & Point Cloud",
                            "Point Cloud Filters",
                            (
                                "Interactive GPU-accelerated 3D point visualizer colored by"
                                "elevation, intensity, or RGB."
                            ),
                            "dem_dialog",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Utility Corridor & Infrastructure LiDAR",
                    "items": [
                        AlgorithmDefinition(
                            "Classify Powerlines & Transmission Towers",
                            "lidar:classify_powerlines",
                            "LiDAR & Point Cloud",
                            "Utility Corridor & Infrastructure LiDAR",
                            "Classifies powerline conductor wires (ASPRS 14) and transmission towers (ASPRS 15) using 3D linearity tensor and structural clustering.",
                            "lidar_powerline",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Vegetation Clearance & Danger Tree Buffer",
                            "lidar:vegetation_clearance",
                            "LiDAR & Point Cloud",
                            "Utility Corridor & Infrastructure LiDAR",
                            "Calculates 3D radial clearance between powerlines and canopy, identifying fall-in danger trees and generating corridor safety buffers.",
                            "lidar_clearance",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Building & Urban 3D",
                    "items": [
                        AlgorithmDefinition(
                            "Extract Building Planar Roofs",
                            "lidar:extract_roofs",
                            "LiDAR & Point Cloud",
                            "Building & Urban 3D",
                            "Extracts planar roof facets from building LiDAR points using Multi-Plane RANSAC, calculating pitch (°), azimuth (°), 3D area, and solar PV suitability.",
                            "lidar_roofs",
                            supports_gpu=True,
                        ),
                    ]
                },
                {
                    "name": "Road & Transportation Corridor Engineering",
                    "items": [
                        AlgorithmDefinition(
                            "Classify Road Surface & Pavement (ASPRS 11)",
                            "lidar:classify_roads",
                            "LiDAR & Point Cloud",
                            "Road & Transportation Corridor Engineering",
                            "Segments asphalt, pavement, and road surface points (ASPRS Class 11) from LiDAR point clouds using 3D planarity tensor, roughness, and ground proximity.",
                            "lidar_road_surface",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Extract Road Centerlines & Curbs",
                            "lidar:road_centerline",
                            "LiDAR & Point Cloud",
                            "Road & Transportation Corridor Engineering",
                            "Traces 3D continuous road centerlines, left/right curb boundary lines, corridor footprint polygons, and equidistant station chainage markers (GPKG).",
                            "lidar_road_corridor",
                            supports_gpu=True,
                        ),
                        AlgorithmDefinition(
                            "Road Grade, Roughness & Vehicle Clearance",
                            "lidar:road_condition",
                            "LiDAR & Point Cloud",
                            "Road & Transportation Corridor Engineering",
                            "Analyzes longitudinal slope gradient (%), pavement surface roughness (IRI proxy), and scans 3D overhead vehicle clearance envelope (e.g. 4.8m) for encroaching tree branches, cables, and overpass hazards.",
                            "lidar_road_condition",
                            supports_gpu=True,
                        ),
                    ]
                }
            ]
        }

