# -*- coding: utf-8 -*-
"""
GeoStudio - 🌲 Forestry & Tree Metrics Algorithm Catalog
"""

from typing import Dict, Any
from ..algorithm_definition import AlgorithmDefinition

FORESTRY_CATALOG: Dict[str, Any] = {
    "category": "🌲 Forestry & Tree Metrics",
    "subcategories": [
        {
            "name": "Precision Forestry & Tree Inventory",
            "items": [
                AlgorithmDefinition(
                    "1. Detect Individual Trees (ITD)",
                    "forestry:detect_trees",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Detects individual tree apexes using Height-Adaptive Variable Window Filtering (VWF), crown prominence, and optional watershed delineation.",
                    "forestry_detect",
                    supports_gpu=True,
                ),
                AlgorithmDefinition(
                    "2. Extract Individual Tree Heights",
                    "forestry:tree_heights",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Extracts and samples exact individual tree apex heights from CHM or normalized LiDAR point cloud.",
                    "forestry_heights",
                    supports_gpu=True,
                ),
                AlgorithmDefinition(
                    "3. Delineate Individual Tree Crowns",
                    "forestry:crown_diameter",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Delineates individual tree crown polygons via Marker-Controlled Watershed, measuring crown area and diameter.",
                    "forestry_crown",
                    supports_gpu=True,
                ),
                AlgorithmDefinition(
                    "4. Estimate DBH, Basal Area & Biomass",
                    "forestry:calculate_dbh",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Estimates individual tree DBH (cm), Basal Area (m²), and Biomass (kg) using calibrated forestry allometric equations.",
                    "forestry_dbh",
                    supports_gpu=False,
                ),
                AlgorithmDefinition(
                    "5. Validate Tree Detection Accuracy",
                    "forestry:validate_accuracy",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Benchmarks detected tree points/crowns against ground truth field inventory, calculating TP, FP, FN, Precision, Recall, F1, and sensitivity curves.",
                    "forestry_validate",
                    supports_gpu=False,
                ),
                AlgorithmDefinition(
                    "6. Generate Forestry Inventory Report",
                    "forestry:inventory_report",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Compiles a comprehensive machine-readable JSON and 300-DPI publication report with stand metrics, height histograms, and crown statistics.",
                    "forestry_report",
                    supports_gpu=False,
                ),
                AlgorithmDefinition(
                    "7. Aboveground Biomass (AGB) & Carbon Stock Engine",
                    "forestry:carbon_stock",
                    "Forestry & Tree Metrics",
                    "Precision Forestry & Tree Inventory",
                    "Estimates continuous Aboveground Biomass (Mg/ha), Total Carbon Stock (t C/ha), and CO2 Equivalent (t CO2e/ha) from CHM raster or tree inventory vector with carbon credit valuation.",
                    "forestry_carbon",
                    supports_gpu=False,
                ),
            ]
        }
    ]
}
