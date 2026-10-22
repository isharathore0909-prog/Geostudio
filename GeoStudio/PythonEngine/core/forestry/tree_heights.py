# -*- coding: utf-8 -*-
"""
GeoStudio - Individual Tree Height Extraction Module
Samples or updates exact individual tree apex heights from a CHM raster onto point vectors.
"""

import os
from typing import Optional, Dict, Any, Callable
import numpy as np
from osgeo import gdal, ogr

from .forestry_io import write_tree_points_vector


def extract_heights_from_chm(
    trees_vector_path: str,
    chm_path: str,
    output_vector_path: Optional[str] = None,
    search_radius_m: float = 1.0,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Samples or updates exact individual tree apex heights from a CHM raster
    for every point feature in the input vector layer.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    progress(10, "Opening canopy model and trees vector...")
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
    pix_rad = max(0, int(round(search_radius_m / max(x_res, y_res))))


    ds_v = ogr.Open(trees_vector_path, 0)
    if not ds_v:
        raise RuntimeError(f"Could not open trees layer: {trees_vector_path}")
    lyr = ds_v.GetLayer(0)
    srs = lyr.GetSpatialRef()
    wkt = srs.ExportToWkt() if srs else ""

    if not output_vector_path:
        base, ext = os.path.splitext(trees_vector_path)
        output_vector_path = f"{base}_with_heights{ext}"

    tree_count = lyr.GetFeatureCount()
    log(f"Sampling heights for <b>{tree_count:,}</b> tree points (Neighborhood radius: <b>{search_radius_m:.1f} m</b>)...")

    updated_records = []
    for i, feat in enumerate(lyr):
        geom = feat.GetGeometryRef()
        if not geom:
            continue
        gx = geom.GetX() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetX()
        gy = geom.GetY() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetY()

        c = int((gx - gt[0]) / gt[1])
        r = int((gy - gt[3]) / gt[5])

        h_val = 0.0
        if 0 <= r < chm.shape[0] and 0 <= c < chm.shape[1]:
            if pix_rad > 0:
                r_min = max(0, r - pix_rad)
                r_max = min(chm.shape[0], r + pix_rad + 1)
                c_min = max(0, c - pix_rad)
                c_max = min(chm.shape[1], c + pix_rad + 1)
                sub = chm[r_min:r_max, c_min:c_max]
                h_val = float(np.nanmax(sub)) if sub.size > 0 else float(chm[r, c])
            else:
                h_val = float(chm[r, c])

        t_id = feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else (i + 1)
        updated_records.append({
            "id": t_id,
            "x": gx,
            "y": gy,
            "height": max(0.0, h_val)
        })

        if i % 500 == 0:
            progress(10 + int((i / max(1, tree_count)) * 70), f"Processed {i:,} / {tree_count:,} trees...")

    write_tree_points_vector(output_vector_path, updated_records, wkt)
    heights = [r["height"] for r in updated_records]

    res = {
        "total_trees": len(updated_records),
        "mean_height": float(np.mean(heights)),
        "max_height": float(np.max(heights)),
        "min_height": float(np.min(heights)),
        "median_height": float(np.median(heights)),
        "output_vector": output_vector_path
    }
    progress(100, f"Extracted heights for {len(updated_records):,} trees!")
    return res
