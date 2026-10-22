# -*- coding: utf-8 -*-
"""
GeoStudio - Central Algorithm Registry & QGIS Hierarchy Schema
Coordinator that loads modular catalogs and exposes the central registry API.
"""

from typing import List, Dict, Any, Optional

from .algorithm_definition import AlgorithmDefinition
from .catalogs import ALL_CATALOGS


class AlgorithmRegistry:
    """Central catalog of all processing algorithms organized into hierarchical categories."""

    HIERARCHY: List[Dict[str, Any]] = ALL_CATALOGS

    @classmethod
    def get_all_algorithms(cls) -> List[AlgorithmDefinition]:
        """Flatten and return all algorithm definitions across all categories."""
        all_algos = []
        for cat in cls.HIERARCHY:
            for sub in cat.get("subcategories", []):
                all_algos.extend(sub.get("items", []))
        return all_algos

    @classmethod
    def find_algorithm(cls, algo_id: str) -> Optional[AlgorithmDefinition]:
        """Find algorithm definition by ID, alias, or dialog type."""
        aliases = {
            "satellite:rastercalc": "satellite:bandmath",
            "satellite:composite": "landsat:composites",
            "native:rasterstats": "native:zonalstats",
            "native:mergevectorlayers": "native:merge",
            "forestry:detect": "forestry:detect_trees",
            "forestry:height": "forestry:tree_heights",
            "forestry:crown": "forestry:crown_diameter",
            "forestry:dbh": "forestry:calculate_dbh",
            "lidar:tree_count": "forestry:detect_trees",
            "lidar:tree_inventory": "forestry:detect_trees",
            "forestry:carbon": "forestry:carbon_stock",
            "forestry:agb": "forestry:carbon_stock",
            "lidar:powerlines": "lidar:classify_powerlines",
            "lidar:powerline": "lidar:classify_powerlines",
            "lidar:clearance": "lidar:vegetation_clearance",
            "lidar:danger_tree": "lidar:vegetation_clearance",
            "lidar:roofs": "lidar:extract_roofs",
            "lidar:building_roofs": "lidar:extract_roofs",
            "lidar:roads": "lidar:classify_roads",
            "lidar:road": "lidar:classify_roads",
            "lidar:road_surface": "lidar:classify_roads",
            "lidar:pavement": "lidar:classify_roads",
            "lidar:curbs": "lidar:road_centerline",
            "lidar:road_curbs": "lidar:road_centerline",
            "lidar:road_corridor": "lidar:road_centerline",
            "lidar:road_grade": "lidar:road_condition",
            "lidar:road_clearance": "lidar:road_condition",
            "lidar:road_roughness": "lidar:road_condition",
        }
        target_id = aliases.get(algo_id, algo_id)
        for algo in cls.get_all_algorithms():
            if (algo.algo_id == target_id
                    or algo.dialog_type == target_id
                    or algo.algo_id == algo_id):
                return algo
        return None


__all__ = ["AlgorithmDefinition", "AlgorithmRegistry"]
