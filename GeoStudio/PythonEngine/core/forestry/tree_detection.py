# -*- coding: utf-8 -*-
"""
GeoStudio - Individual Tree Detection (ITD) Module
Implements Gaussian smoothing and Height-Adaptive Variable Window Filtering (VWF)
with topological crown saddle prominence: P >= max(P_min, alpha * H_apex).
"""

from typing import Dict, Any, List, Tuple, Optional, Callable
import numpy as np
from scipy import ndimage
from osgeo import gdal

from .point_cloud_chm import is_point_cloud_file, derive_chm_from_point_cloud


def detect_tree_apexes(
    chm_path: str,
    min_height: float = 2.0,
    search_mode: str = "vwf_mixed",
    window_size: int = 5,
    smoothing_sigma: float = 0.8,
    min_prominence: float = 0.35,
    alpha_prominence: float = 0.10,
    ground_coverage_threshold_pct: float = 15.0,
    vwf_a: float = 0.28,
    vwf_b: float = 1.5,
    vwf_min_win: int = 3,
    vwf_max_win: int = 15,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[List[Dict[str, Any]], np.ndarray, Tuple[float, ...], str, Dict[str, Any]]:
    """
    Detects individual tree apexes using Height-Adaptive Variable Window Filtering (VWF)
    or fixed-window local maxima filtering with topological crown saddle prominence:
    P >= max(P_min, alpha * H_apex).
    Returns: (tree_records, chm_array, geotransform, projection_wkt, metadata_stats)
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    derived_tif = None
    point_cloud_meta = {}
    if is_point_cloud_file(chm_path):
        progress(5, "Input is LiDAR point cloud. Deriving normalized canopy height model (CHM)...")
        chm_res = derive_chm_from_point_cloud(
            point_cloud_path=chm_path,
            resolution=0.5,
            ground_coverage_threshold_pct=ground_coverage_threshold_pct,
            progress_callback=progress_callback,
            log_callback=log_callback
        )
        chm, gt, proj_wkt, derived_tif = chm_res[0], chm_res[1], chm_res[2], chm_res[3]
        if hasattr(chm_res, "metadata"):
            point_cloud_meta = chm_res.metadata
    else:
        progress(5, "Opening Canopy Height Model (CHM)...")
        ds = gdal.Open(chm_path, gdal.GA_ReadOnly)

        if not ds:
            raise RuntimeError(f"Could not open input CHM or point cloud: {chm_path}")

        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        chm = band.ReadAsArray().astype(np.float32)

        if nodata is not None:
            chm[chm == nodata] = 0.0
        chm[np.isnan(chm)] = 0.0
        chm[chm < 0] = 0.0

        gt = ds.GetGeoTransform()
        proj_wkt = ds.GetProjection()

    x_res = abs(gt[1])
    y_res = abs(gt[5])
    is_geo = (abs(gt[0]) <= 180 and abs(gt[3]) <= 90)
    if is_geo:
        import math
        mean_lat = gt[3] - (chm.shape[0] * y_res) / 2.0
        m_lon = max(1.0, 111412.84 * math.cos(math.radians(mean_lat)))
        m_lat = max(1.0, 111132.954 - 559.822 * math.cos(2 * math.radians(mean_lat)))
        cell_area_m2 = (x_res * m_lon) * (y_res * m_lat)
        res_display_m = ((x_res * m_lon) + (y_res * m_lat)) / 2.0
    else:
        cell_area_m2 = x_res * y_res
        res_display_m = (x_res + y_res) / 2.0

    total_valid_pixels = int(np.sum(chm >= min_height))
    forest_area_ha = (total_valid_pixels * cell_area_m2) / 10000.0

    log(f"CHM dimensions: <b>{chm.shape[1]} × {chm.shape[0]}</b> pixels (Resolution: <b>{res_display_m:.2f} m</b>)")
    log(f"Canopy coverage area above {min_height:.1f}m: <b>{forest_area_ha:.2f} ha</b>")

    # 2. Smooth CHM to suppress single-leaf noise
    progress(20, "Applying Gaussian canopy smoothing...")
    if smoothing_sigma > 0.01:
        smoothed = ndimage.gaussian_filter(chm, sigma=smoothing_sigma)
    else:
        smoothed = chm.copy()

    # 3. Individual Tree Apex Detection: Variable Window Filter (VWF) vs Fixed LMF
    progress(35, "Searching tree apexes with Height-Adaptive Crown Modeling & Topological Saddle Prominence...")

    peaks_mask = np.zeros_like(smoothed, dtype=bool)

    if search_mode.startswith("vwf") or search_mode == "custom":
        if search_mode == "vwf_conifer":
            a, b = 0.22, 1.2
            min_w, max_w = 3, 11
            model_name = "Adaptive Conifer (Popescu & Wynne allometry)"
        elif search_mode == "vwf_deciduous":
            a, b = 0.32, 1.8
            min_w, max_w = 3, 13
            model_name = "Adaptive Deciduous / Broadleaf (allometric model)"
        elif search_mode == "custom":
            a, b = vwf_a, vwf_b
            min_w, max_w = max(3, vwf_min_win), max(min_w, vwf_max_win)
            model_name = f"Custom Calibrated VWF (a={a:.3f}, b={b:.2f}m)"
        else:
            a, b = 0.28, 1.5
            min_w, max_w = 3, 11
            model_name = "Adaptive Mixed Stand (allometric model)"

        log(f"Using <b>{model_name}</b>: Crown Width = <b>{a:.2f} × H + {b:.1f} m</b>")
        log(f"Topological Prominence Criterion: <b>P ≥ max({min_prominence:.2f} m, {alpha_prominence:.2f}·H_apex)</b>")

        # Multi-scale height tiers mapped to adaptive window sizes
        tier_cuts = [min_height, 5.0, 9.0, 14.0, 20.0, 30.0, 150.0]
        for idx in range(len(tier_cuts) - 1):
            h_low, h_high = tier_cuts[idx], tier_cuts[idx + 1]
            mid_h = (h_low + min(h_high, 40.0)) / 2.0
            expected_crown_m = a * mid_h + b
            win_sz = int(round(expected_crown_m / max(0.1, res_display_m)))
            if win_sz % 2 == 0:
                win_sz += 1
            win_sz = max(min_w, min(max_w, win_sz))

            tier_mask = (smoothed >= h_low) & (smoothed < h_high)
            if not np.any(tier_mask):
                continue

            loc_max = ndimage.maximum_filter(smoothed, size=(win_sz, win_sz))
            # Topological crown saddle calculation: perimeter base depression
            prom_win = max(win_sz + 2, 7)
            loc_min = ndimage.minimum_filter(smoothed, size=(prom_win, prom_win))
            topological_prom = smoothed - loc_min

            # Standard prominence criterion: P >= max(P_min, alpha * H_apex)
            prominence_threshold = np.maximum(min_prominence, alpha_prominence * smoothed)

            is_tier_peak = (smoothed == loc_max) & tier_mask & (topological_prom >= prominence_threshold)
            peaks_mask |= is_tier_peak

    else:
        # Fixed Window LMF
        log(f"Using Fixed Window LMF: <b>{window_size}×{window_size}</b> kernel.")
        log(f"Topological Prominence Criterion: <b>P ≥ max({min_prominence:.2f} m, {alpha_prominence:.2f}·H_apex)</b>")
        footprint = np.ones((window_size, window_size), dtype=bool)
        local_max = ndimage.maximum_filter(smoothed, footprint=footprint)
        prom_win = max(window_size + 2, 7)
        local_min = ndimage.minimum_filter(smoothed, size=(prom_win, prom_win))
        topological_prom = smoothed - local_min
        prominence_threshold = np.maximum(min_prominence, alpha_prominence * smoothed)
        peaks_mask = (smoothed == local_max) & (smoothed >= min_height) & (topological_prom >= prominence_threshold)

    peak_rows, peak_cols = np.where(peaks_mask)
    total_trees = len(peak_rows)

    if total_trees == 0:
        raise RuntimeError(f"No tree apexes detected above {min_height:.1f}m. Try lowering the minimum height.")

    progress(55, f"Detected <b>{total_trees:,}</b> tree apexes! Generating records...")
    log(f"Detected <b>{total_trees:,}</b> individual tree apexes.")

    tree_records = []
    for i in range(total_trees):
        r = int(peak_rows[i])
        c = int(peak_cols[i])
        gx = gt[0] + (c + 0.5) * gt[1] + (r + 0.5) * gt[2]
        gy = gt[3] + (c + 0.5) * gt[4] + (r + 0.5) * gt[5]
        h = float(chm[r, c])
        tree_records.append({
            "id": i + 1,
            "x": gx,
            "y": gy,
            "row": r,
            "col": c,
            "height": h
        })

    heights = [t["height"] for t in tree_records]
    mean_h = float(np.mean(heights))
    max_h = float(np.max(heights))
    min_h_val = float(np.min(heights))
    std_h = float(np.std(heights))
    density_per_ha = (total_trees / forest_area_ha) if forest_area_ha > 0.001 else 0.0

    stats = {
        "total_trees": total_trees,
        "forest_area_ha": forest_area_ha,
        "density_per_ha": density_per_ha,
        "mean_height": mean_h,
        "max_height": max_h,
        "min_height": min_h_val,
        "std_height": std_h,
        "chm_resolution_m": round(res_display_m, 2),
        "search_mode": search_mode,
        "vwf_model": model_name if (search_mode.startswith("vwf") or search_mode == "custom") else f"Fixed LMF ({window_size}x{window_size})",
        "vwf_equation": f"{a:.2f}H + {b:.2f}" if (search_mode.startswith("vwf") or search_mode == "custom") else "N/A",
        "smoothing_sigma": smoothing_sigma,
        "min_height_threshold": min_height,
        "min_prominence": min_prominence,
        "alpha_prominence": alpha_prominence,
        "point_cloud_meta": point_cloud_meta
    }

    return tree_records, chm, gt, proj_wkt, stats
