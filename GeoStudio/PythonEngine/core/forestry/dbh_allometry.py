# -*- coding: utf-8 -*-
"""
GeoStudio - DBH Allometry & Forest Biomass Module
Estimates DBH (cm), Basal Area (m²), and Tree Biomass (kg) using forestry allometry models.
"""

import math
from typing import Dict, Any, Callable, Optional
import numpy as np
from osgeo import ogr

from .forestry_io import write_dbh_points_vector


def calculate_dbh_and_biomass(
    trees_vector_path: str,
    output_vector_path: str,
    method: str = "allometric",
    forest_preset: str = "conifer",
    custom_a: float = 0.85,
    custom_b: float = 0.72,
    custom_c: float = 0.38,
    wood_density: float = 0.55,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Estimates DBH (cm), Basal Area (m²), and Tree Biomass (kg) using forestry allometry
    or direct stem calculations.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    progress(10, "Opening input trees layer...")
    ds_v = ogr.Open(trees_vector_path, 0)
    if not ds_v:
        raise RuntimeError(f"Could not open trees layer: {trees_vector_path}")
    lyr = ds_v.GetLayer(0)
    srs = lyr.GetSpatialRef()
    wkt = srs.ExportToWkt() if srs else ""

    # Presets for DBH allometry: ln(DBH) = a + b*ln(H) + c*ln(CD)
    presets = {
        "conifer": (0.85, 0.72, 0.38),      # Pine / Spruce / Fir
        "hardwood": (1.02, 0.68, 0.42),     # Oak / Maple / Beech
        "tropical": (1.15, 0.75, 0.35),     # Tropical Broadleaf
        "eucalyptus": (0.92, 0.81, 0.28),   # Fast-growing plantation
        "custom": (custom_a, custom_b, custom_c)
    }
    coeff = presets.get(forest_preset.lower(), presets["conifer"])
    a, b, c = coeff

    dbh_source = "Allometric Model"
    dbh_model_name = f"ln(DBH) = {a:.2f} + {b:.2f}·ln(H) + {c:.2f}·ln(CD) [{forest_preset.capitalize()}]"
    dbh_confidence = "Estimated (Aerial CHM)"
    biomass_model_name = f"Chave et al. (2014) Allometric AGB (wood density={wood_density:.2f} g/cm³)"

    log(f"<b>Estimated DBH Allometry Model:</b> {dbh_model_name}")
    log(f"<b>DBH Source:</b> {dbh_source} | <b>Confidence:</b> {dbh_confidence}")
    log(f"<b>Biomass Model:</b> {biomass_model_name}")

    tree_count = lyr.GetFeatureCount()
    records = []
    dbhs = []
    biomasses = []
    basal_areas = []

    for i, feat in enumerate(lyr):
        geom = feat.GetGeometryRef()
        if not geom:
            continue

        h = float(feat.GetField("Height_m")) if feat.GetFieldIndex("Height_m") >= 0 else 15.0
        cd = float(feat.GetField("Crown_Diam_m")) if feat.GetFieldIndex("Crown_Diam_m") >= 0 else (h * 0.25)
        h = max(1.5, h)
        cd = max(0.5, cd)

        # Estimate DBH (cm) via Allometric Equation
        ln_dbh = a + b * math.log(h) + c * math.log(cd)
        dbh_cm = round(math.exp(ln_dbh), 1)

        # Basal area in m²: BA = pi * (DBH / 200)^2
        radius_m = (dbh_cm / 100.0) / 2.0
        ba_m2 = round(math.pi * (radius_m ** 2), 4)

        # Individual Aboveground Biomass (kg) using Chave et al. equation:
        # AGB_kg = 0.0673 * (rho * DBH^2 * H)^0.976
        biomass_kg = round(0.0673 * ((wood_density * (dbh_cm ** 2) * h) ** 0.976), 1)

        t_id = feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else (i + 1)
        if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D):
            gx = geom.GetX()
            gy = geom.GetY()
        else:
            centroid = geom.Centroid()
            gx = centroid.GetX()
            gy = centroid.GetY()

        records.append({
            "id": t_id,
            "x": gx,
            "y": gy,
            "height": h,
            "crown_diam": cd,
            "dbh_cm": dbh_cm,
            "basal_area": ba_m2,
            "biomass_kg": biomass_kg,
            "dbh_source": dbh_source,
            "dbh_model": dbh_model_name,
            "dbh_confidence": dbh_confidence,
            "biomass_model": biomass_model_name
        })
        dbhs.append(dbh_cm)
        biomasses.append(biomass_kg)
        basal_areas.append(ba_m2)

        if i % 500 == 0:
            progress(20 + int((i / max(1, tree_count)) * 60), f"Estimated DBH for {i:,} trees...")

    write_dbh_points_vector(output_vector_path, records, wkt)
    progress(100, f"Estimated DBH and biomass for {len(records):,} trees!")

    return {
        "total_trees": len(records),
        "mean_dbh_cm": float(np.mean(dbhs)),
        "max_dbh_cm": float(np.max(dbhs)),
        "min_dbh_cm": float(np.min(dbhs)),
        "total_basal_area_m2": float(np.sum(basal_areas)),
        "total_biomass_tons": float(np.sum(biomasses) / 1000.0),
        "dbh_source": dbh_source,
        "dbh_model": dbh_model_name,
        "dbh_confidence": dbh_confidence,
        "biomass_model": biomass_model_name,
        "output_vector": output_vector_path
    }
