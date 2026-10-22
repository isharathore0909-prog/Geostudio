# -*- coding: utf-8 -*-
"""
GeoStudio - Earthwork Cut & Fill Data Models
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CutFillResult:
    """Analytical results of a Cut & Fill computation."""
    base_name: str
    comp_name: str
    is_datum_mode: bool
    datum_elevation: Optional[float]

    # Area breakdown
    total_analyzed_area_m2: float
    total_analyzed_area_ha: float
    cut_area_m2: float
    fill_area_m2: float
    daylight_area_m2: float

    # Raw / Gross Volumes
    gross_cut_volume_m3: float
    gross_fill_volume_m3: float

    # Material Factors
    swell_factor: float       # Excavation bulking factor (e.g. 1.15)
    shrinkage_factor: float   # Embankment compaction factor (e.g. 0.90)

    # Factored Volumes
    factored_cut_volume_m3: float
    factored_fill_volume_m3: float
    net_earthwork_volume_m3: float  # + = Excavation surplus (Export), - = Embankment deficit (Import)
    cut_fill_ratio: float           # Cut / Fill ratio

    # Depths & Thicknesses
    max_cut_depth_m: float
    mean_cut_depth_m: float
    max_fill_depth_m: float
    mean_fill_depth_m: float

    # File outputs
    diff_raster_path: Optional[str] = None
    daylight_vector_path: Optional[str] = None
    balance_plane_elevation_m: Optional[float] = None
