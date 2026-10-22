# -*- coding: utf-8 -*-
"""
GeoStudio - Crown Segmentation & Canopy Spread Module
Segments individual tree crowns and extracts crown diameter (m), crown area (m²),
and crown perimeter polygon boundaries.
"""

import math
from typing import Dict, Any, Callable, Optional
import numpy as np
from osgeo import gdal, ogr

from .forestry_io import write_crown_polygons_vector


def delineate_crown_polygons(
    trees_vector_path: str,
    chm_path: str,
    output_vector_path: str,
    method: str = "watershed",
    max_crown_radius_m: float = 12.0,
    crown_base_ratio: float = 0.35,
    min_canopy_height: float = 1.5,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Segments individual tree crowns and extracts crown diameter (m), crown area (m²),
    and crown perimeter polygon boundaries using Marker-Controlled Watershed segmentation.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    progress(10, "Opening canopy height model and tree points layer...")
    from .point_cloud_chm import is_point_cloud_file, derive_chm_from_point_cloud

    if is_point_cloud_file(chm_path):
        chm, gt, _, _ = derive_chm_from_point_cloud(
            point_cloud_path=chm_path,
            resolution=0.5,
            progress_callback=progress_callback,
            log_callback=log_callback
        )
    else:
        ds_r = gdal.Open(chm_path, gdal.GA_ReadOnly)
        if not ds_r:
            raise RuntimeError(f"Could not open input CHM or point cloud: {chm_path}")
        band = ds_r.GetRasterBand(1)
        chm = band.ReadAsArray().astype(np.float32)
        gt = ds_r.GetGeoTransform()

    x_res = abs(gt[1])
    y_res = abs(gt[5])
    is_geo = (abs(gt[0]) <= 180 and abs(gt[3]) <= 90)
    if is_geo:
        mean_lat = gt[3] - (chm.shape[0] * y_res) / 2.0
        m_per_deg_lat = max(1000.0, 111132.954 - 559.822 * math.cos(2 * math.radians(mean_lat)))
        m_per_deg_lon = max(1000.0, 111412.84 * math.cos(math.radians(mean_lat)))
        m_per_px_x = x_res * m_per_deg_lon
        m_per_px_y = y_res * m_per_deg_lat
    else:
        m_per_px_x = x_res
        m_per_px_y = y_res

    cell_area_m2 = m_per_px_x * m_per_px_y
    max_pix_radius = int(math.ceil(max_crown_radius_m / max(m_per_px_x, m_per_px_y)))

    ds_v = ogr.Open(trees_vector_path, 0)
    if not ds_v:
        raise RuntimeError(f"Could not open trees layer: {trees_vector_path}")
    lyr = ds_v.GetLayer(0)
    srs = lyr.GetSpatialRef()
    wkt = srs.ExportToWkt() if srs else ""

    tree_count = lyr.GetFeatureCount()
    log(f"Segmenting individual tree crowns for <b>{tree_count:,}</b> trees (Method: <b>{method.capitalize()}</b>)...")

    # Extract tree apex positions
    trees = []
    markers = np.zeros(chm.shape, dtype=np.int32)

    for i, feat in enumerate(lyr):
        geom = feat.GetGeometryRef()
        if not geom:
            continue
        gx = geom.GetX() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetX()
        gy = geom.GetY() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetY()
        c = int((gx - gt[0]) / gt[1])
        r = int((gy - gt[3]) / gt[5])

        if 0 <= r < chm.shape[0] and 0 <= c < chm.shape[1]:
            h = float(feat.GetField("Height_m")) if feat.GetFieldIndex("Height_m") >= 0 else float(chm[r, c])
            t_id = feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else (i + 1)
            trees.append({"id": t_id, "x": gx, "y": gy, "row": r, "col": c, "height": h, "internal_idx": len(trees) + 1})
            markers[r, c] = len(trees)

    # 1. Marker-Controlled Watershed Flooding
    progress(30, "Computing inverted canopy topography and executing watershed flooding...")
    import scipy.ndimage as ndi
    smoothed = ndi.gaussian_filter(chm, sigma=0.8)
    max_h = float(smoothed.max())
    inv_topography = np.clip((max_h - smoothed) * (65535.0 / (max_h + 1e-5)), 0, 65535).astype(np.uint16)

    # Execute watershed
    ws_labels = ndi.watershed_ift(inv_topography, markers)
    # Mask out pixels below canopy cutoff
    ws_labels[chm < min_canopy_height] = 0

    progress(55, "Tracing individual crown perimeter boundary polygons...")
    crown_polygons = []
    crown_diameters = []
    crown_areas = []

    angles = np.linspace(0, 2 * np.pi, 24, endpoint=False)

    for idx, t in enumerate(trees):
        tr = t["row"]
        tc = t["col"]
        th = t["height"]
        t_marker = t["internal_idx"]

        poly_pts = []
        radii_m = []

        for ang in angles:
            cos_a = math.cos(ang)
            sin_a = math.sin(ang)
            last_r = 1

            for rad in range(1, max_pix_radius + 1):
                rr = int(round(tr + rad * sin_a))
                cc = int(round(tc + rad * cos_a))

                if rr < 0 or rr >= chm.shape[0] or cc < 0 or cc >= chm.shape[1]:
                    break
                if ws_labels[rr, cc] != t_marker:
                    break
                last_r = rad

            dist_x_m = last_r * m_per_px_x * cos_a
            dist_y_m = last_r * m_per_px_y * sin_a
            r_dist = math.sqrt(dist_x_m**2 + dist_y_m**2)
            radii_m.append(r_dist)

            # Geographical/Projected coordinates of polygon boundary vertex
            if is_geo:
                vx = t["x"] + (last_r * x_res * cos_a)
                vy = t["y"] + (last_r * y_res * sin_a)
            else:
                vx = t["x"] + dist_x_m
                vy = t["y"] + dist_y_m
            poly_pts.append((vx, vy))

        if poly_pts:
            poly_pts.append(poly_pts[0])

        # True pixel area within this tree's watershed segment
        pixel_count = int(np.sum(ws_labels == t_marker))
        if pixel_count > 0:
            c_area = round(pixel_count * cell_area_m2, 2)
            c_diam = round(2.0 * math.sqrt(c_area / math.pi), 2)
        else:
            mean_r = float(np.mean(radii_m)) if radii_m else (m_per_px_x * 2)
            c_diam = round(mean_r * 2.0, 2)
            c_area = round(math.pi * (mean_r ** 2), 2)

        crown_diameters.append(c_diam)
        crown_areas.append(c_area)
        crown_polygons.append({
            "id": t["id"],
            "height": t["height"],
            "crown_diam": c_diam,
            "crown_area": c_area,
            "pts": poly_pts
        })

        if idx % 250 == 0:
            progress(55 + int((idx / max(1, len(trees))) * 35), f"Segmented {idx:,} / {len(trees):,} crowns...")

    progress(92, "Writing crown polygons to vector dataset...")
    write_crown_polygons_vector(output_vector_path, crown_polygons, wkt)
    progress(100, f"Saved {len(crown_polygons):,} crown boundary polygons!")

    return {
        "total_crowns": len(crown_polygons),
        "mean_crown_diam": float(np.mean(crown_diameters)),
        "max_crown_diam": float(np.max(crown_diameters)),
        "min_crown_diam": float(np.min(crown_diameters)),
        "mean_crown_area": float(np.mean(crown_areas)),
        "output_vector": output_vector_path
    }
