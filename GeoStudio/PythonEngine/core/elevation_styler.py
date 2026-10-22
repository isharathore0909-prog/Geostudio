# -*- coding: utf-8 -*-
"""
Backward-compatible wrapper importing from modular core.elevation package.
"""
from .elevation import ElevationStyler, ELEVATION_PRESETS, generate_3d_shaded_relief_file

__all__ = ["ElevationStyler", "ELEVATION_PRESETS", "generate_3d_shaded_relief_file"]
