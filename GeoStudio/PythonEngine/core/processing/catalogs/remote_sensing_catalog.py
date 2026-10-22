# -*- coding: utf-8 -*-
"""
GeoStudio - 🛰 Landsat & Remote Sensing Algorithm Catalog
"""

from typing import Dict, Any
from .remote_sensing_items import (
    LANDSAT_ITEMS,
    SPECTRAL_INDICES_ITEMS,
    ENHANCEMENT_ITEMS,
    HYPERSPECTRAL_ITEMS
)

REMOTE_SENSING_CATALOG: Dict[str, Any] = {
    "category": "🛰 Landsat & Remote Sensing",
    "subcategories": [
        {
            "name": "Landsat Workflows",
            "items": LANDSAT_ITEMS
        },
        {
            "name": "Spectral Indices Studio",
            "items": SPECTRAL_INDICES_ITEMS
        },
        {
            "name": "Image Enhancement & Radiometry",
            "items": ENHANCEMENT_ITEMS
        },
        {
            "name": "Hyperspectral & Dimensionality",
            "items": HYPERSPECTRAL_ITEMS
        }
    ]
}
