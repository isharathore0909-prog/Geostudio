# -*- coding: utf-8 -*-
"""
GeoStudio - Elevation & DEM Styling Package
Provides color palettes, relief shading engines, and DEM renderers.
"""

from .elevation_palettes import ELEVATION_PRESETS
from .relief_shading import generate_3d_shaded_relief_file
from .elevation_styler import ElevationStyler

__all__ = [
    "ElevationStyler",
    "ELEVATION_PRESETS",
    "generate_3d_shaded_relief_file",
]
