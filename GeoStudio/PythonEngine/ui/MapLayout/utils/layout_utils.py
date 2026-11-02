# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Utility Helpers
Provides unit conversions, geometric helpers, paper size lookups, and memory guards.
"""

from typing import Tuple, Optional, Any
from ..constants.presets import PAGE_PRESETS, PAGE_SIZES


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / 25.4


def inches_to_mm(inches: float) -> float:
    """Convert inches to millimeters."""
    return inches * 25.4


def mm_to_pixels(mm: float, dpi: int = 300) -> int:
    """Calculate pixel count from millimeters at given DPI."""
    return int(round((mm / 25.4) * dpi))


def pixels_to_mm(pixels: int, dpi: int = 300) -> float:
    """Calculate millimeters from pixel count at given DPI."""
    return round((pixels * 25.4) / dpi, 2)


def calculate_page_dimensions(preset_name: str, orientation: str = "Landscape") -> Tuple[float, float]:
    """
    Returns (width_mm, height_mm) for a named paper preset and orientation.
    """
    if preset_name in PAGE_PRESETS:
        return PAGE_PRESETS[preset_name]

    # Check base sizes
    base_key = preset_name.split()[0] if preset_name else "A4"
    w, h = PAGE_SIZES.get(base_key, (297.0, 210.0))
    if orientation.lower() == "landscape" and w < h:
        return (h, w)
    elif orientation.lower() == "portrait" and w > h:
        return (h, w)
    return (w, h)


def estimate_image_memory_mb(width_px: int, height_px: int, bytes_per_pixel: int = 4) -> float:
    """Calculates uncompressed raster memory requirement in megabytes."""
    return round((width_px * height_px * bytes_per_pixel) / (1024.0 * 1024.0), 2)


def is_memory_critical(width_px: int, height_px: int, threshold_mp: float = 100.0) -> bool:
    """Returns True if the rendered pixel dimensions exceed safety threshold."""
    megapixels = (width_px * height_px) / 1_000_000.0
    return megapixels > threshold_mp


def get_layout_item_by_id(layout: Any, item_id: str) -> Optional[Any]:
    """Finds an item in layout by its user-defined ID."""
    if not layout or not hasattr(layout, "items"):
        return None
    for it in layout.items():
        if hasattr(it, "id") and it.id() == item_id:
            return it
    return None


__all__ = [
    "mm_to_inches",
    "inches_to_mm",
    "mm_to_pixels",
    "pixels_to_mm",
    "calculate_page_dimensions",
    "estimate_image_memory_mb",
    "is_memory_critical",
    "get_layout_item_by_id",
]
