# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Configuration & Presets
Standard ISO and ANSI page dimension definitions, units, and layout presets.
"""

# Standard paper presets in mm (width, height)
PAGE_PRESETS = {
    "A4 Portrait": (210.0, 297.0),
    "A4 Landscape": (297.0, 210.0),
    "A3 Portrait": (297.0, 420.0),
    "A3 Landscape": (420.0, 297.0),
    "A2 Portrait": (420.0, 594.0),
    "A2 Landscape": (594.0, 420.0),
    "A1 Portrait": (594.0, 841.0),
    "A1 Landscape": (841.0, 594.0),
    "A0 Portrait": (841.0, 1189.0),
    "A0 Landscape": (1189.0, 841.0),
    "Letter Landscape": (279.4, 215.9),
    "Letter Portrait": (215.9, 279.4),
}

# Base ISO paper sizes
PAGE_SIZES = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
    "A5": (148.0, 210.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}

# Standard resolution options
DPI_PRESETS = {
    "Screen (72 DPI)": 72,
    "Web / Preview (96 DPI)": 96,
    "Draft Print (150 DPI)": 150,
    "Medium (200 DPI)": 200,
    "High-Res Production (300 DPI)": 300,
    "Ultra-Fine (600 DPI)": 600,
    "Maximum Quality (1200 DPI)": 1200,
}

__all__ = [
    "PAGE_PRESETS",
    "PAGE_SIZES",
    "DPI_PRESETS",
]
