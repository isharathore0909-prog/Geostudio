# -*- coding: utf-8 -*-
"""
GeoStudio - 📐 Vector Geoprocessing Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

VECTOR_CATALOG: Dict[str, Any] = {
            "category": "📐 Vector Geoprocessing",
            "subcategories": [
                {
                    "name": "Geometry Tools",
                    "items": [
                        AlgorithmDefinition(
                            "Buffer",
                            "native:buffer",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            (
                                "Generates fixed or attribute-driven buffer zones around vector"
                                "features."
                            ),
                            "vector_buffer",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Centroids",
                            "native:centroids",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            "Calculates geometric center points of polygons and multipoints.",
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Convex Hull",
                            "native:convexhull",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            (
                                "Calculates the smallest enclosing convex polygon enclosing"
                                "feature geometries."
                            ),
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Dissolve",
                            "native:dissolve",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            (
                                "Merges adjacent polygons sharing boundaries or matching attribute"
                                "values."
                            ),
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Voronoi / Thiessen Polygons",
                            "native:voronoi",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            (
                                "Constructs Dirichlet/Voronoi tessellation polygons from point"
                                "datasets."
                            ),
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Delaunay Triangulation",
                            "native:delaunay",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            (
                                "Generates Delaunay triangular irregular network from point"
                                "coordinates."
                            ),
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Simplify Geometries (Douglas-Peucker)",
                            "native:simplify",
                            "Vector Geoprocessing",
                            "Geometry Tools",
                            (
                                "Generalizes and decimates vertices while preserving shape"
                                "topology."
                            ),
                            "vector_geometry",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Overlay & Geoprocessing",
                    "items": [
                        AlgorithmDefinition(
                            "Clip Vector",
                            "native:clip",
                            "Vector Geoprocessing",
                            "Overlay & Geoprocessing",
                            (
                                "Clips input features using the boundary polygon of an overlay"
                                "layer."
                            ),
                            "vector_overlay",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Intersection",
                            "native:intersection",
                            "Vector Geoprocessing",
                            "Overlay & Geoprocessing",
                            "Extracts spatial overlap portions of features across two layers.",
                            "vector_overlay",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Union",
                            "native:union",
                            "Vector Geoprocessing",
                            "Overlay & Geoprocessing",
                            (
                                "Combines layers while preserving all geometry boundaries and"
                                "attributes."
                            ),
                            "vector_overlay",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Difference",
                            "native:difference",
                            "Vector Geoprocessing",
                            "Overlay & Geoprocessing",
                            (
                                "Extracts features from input layer that do not overlap the"
                                "overlay layer."
                            ),
                            "vector_overlay",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Merge Vector Layers",
                            "native:merge",
                            "Vector Geoprocessing",
                            "Overlay & Geoprocessing",
                            "Combines multiple vector layers into a single unified layer.",
                            "vector_overlay",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Spatial Analysis & Join",
                    "items": [
                        AlgorithmDefinition(
                            "Spatial Join",
                            "native:spatialjoin",
                            "Vector Geoprocessing",
                            "Spatial Analysis & Join",
                            (
                                "Transfers attributes between layers based on spatial"
                                "relationships (intersects, contains, within)."
                            ),
                            "vector_analysis",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Distance Matrix",
                            "native:distancematrix",
                            "Vector Geoprocessing",
                            "Spatial Analysis & Join",
                            "Calculates pairwise distances between points in two layers.",
                            "vector_analysis",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Nearest Neighbor Analysis",
                            "native:nearestneighbor",
                            "Vector Geoprocessing",
                            "Spatial Analysis & Join",
                            (
                                "Computes spatial clustering index and expected nearest neighbor"
                                "distance."
                            ),
                            "vector_analysis",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Count Points in Polygons",
                            "native:pointsinpoly",
                            "Vector Geoprocessing",
                            "Spatial Analysis & Join",
                            "Aggregates point count within each bounding polygon feature.",
                            "vector_analysis",
                            supports_gpu=False,
                        ),
                    ]
                },
                {
                    "name": "Topology & Data Cleaning",
                    "items": [
                        AlgorithmDefinition(
                            "Topology & Geometry Validation",
                            "vector:topology_checker",
                            "Vector Geoprocessing",
                            "Topology & Data Cleaning",
                            (
                                "Detects self-intersections, duplicate nodes, slivers, gaps, and"
                                "invalid geometries."
                            ),
                            "tools_geom",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Fix Geometries & Remove Slivers",
                            "native:fixgeoms",
                            "Vector Geoprocessing",
                            "Topology & Data Cleaning",
                            "Repairs invalid geometries and removes micro-sliver polygons.",
                            "tools_geom",
                            supports_gpu=False,
                        ),
                        AlgorithmDefinition(
                            "Field Calculator & Expressions",
                            "native:fieldcalc",
                            "Vector Geoprocessing",
                            "Topology & Data Cleaning",
                            (
                                "Computes and creates new attribute columns using spatial &"
                                "arithmetic expressions."
                            ),
                            "field_calculator",
                            supports_gpu=False,
                        ),
                    ]
                }
            ]
        }
