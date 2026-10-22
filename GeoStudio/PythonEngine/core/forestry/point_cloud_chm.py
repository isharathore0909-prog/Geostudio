# -*- coding: utf-8 -*-
"""
GeoStudio - Point Cloud to Canopy Height Model (CHM) Converter
High-speed pure Python/NumPy + laspy derivation of normalized Canopy Height Models (CHM)
directly from raw or classified LiDAR point clouds (.las, .laz, .copc.laz).
"""

import os
import time
import tempfile
from typing import Tuple, Optional, Callable
import numpy as np
from scipy.ndimage import distance_transform_edt
from osgeo import gdal, osr
import laspy


def is_point_cloud_file(path: str) -> bool:
    """Checks if a file path points to a LAS/LAZ/COPC point cloud dataset."""
    if not path or not isinstance(path, str):
        return False
    low = path.lower()
    return low.endswith(".las") or low.endswith(".laz") or low.endswith(".copc.laz")


class CHMDerivationResult(tuple):
    """4-tuple subclass preserving (chm, gt, crs_wkt, out_tif) unpacking while exposing auditable metadata."""
    def __new__(cls, chm, gt, crs_wkt, out_tif, metadata=None):
        return super().__new__(cls, (chm, gt, crs_wkt, out_tif))

    def __init__(self, chm, gt, crs_wkt, out_tif, metadata=None):
        self.metadata = metadata or {}


def derive_chm_from_point_cloud(
    point_cloud_path: str,
    resolution: float = 0.5,
    coarse_res_m: float = 4.0,
    ground_coverage_threshold_pct: float = 15.0,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Tuple[np.ndarray, Tuple[float, ...], str, str]:
    """
    Derives a normalized Canopy Height Model (CHM) directly from a LiDAR point cloud (.las, .laz, .copc.laz)
    using out-of-core chunked streaming to prevent high RAM consumption.
    Returns: (chm_array, geotransform, proj_wkt, chm_geotiff_path)
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    t0 = time.time()
    progress(5, "Opening LiDAR point cloud header...")
    log(f"Reading LiDAR dataset: <b>{os.path.basename(point_cloud_path)}</b>")

    # 1. Read header metadata without loading all points into RAM
    with laspy.open(point_cloud_path) as fh:
        total_pts = fh.header.point_count
        x_min, x_max = float(fh.header.x_min), float(fh.header.x_max)
        y_min, y_max = float(fh.header.y_min), float(fh.header.y_max)
        z_min, z_max = float(fh.header.z_min), float(fh.header.z_max)
        header_crs = None
        try:
            header_crs = fh.header.parse_crs()
        except Exception:
            pass

    log(f"Dataset contains <b>{total_pts:,}</b> points. Extent: X=[{x_min:.4f}, {x_max:.4f}], Y=[{y_min:.4f}, {y_max:.4f}]")

    # 2. Coordinate System & Grid Dimensions
    is_geographic = (abs(x_min) <= 180 and abs(x_max) <= 180 and abs(y_min) <= 90 and abs(y_max) <= 90)
    if is_geographic:
        import math
        mean_lat = (y_min + y_max) / 2.0
        m_per_deg_lat = max(1000.0, 111132.954 - 559.822 * math.cos(2 * math.radians(mean_lat)))
        m_per_deg_lon = max(1000.0, 111412.84 * math.cos(math.radians(mean_lat)))
        res_x = max(1e-9, resolution / m_per_deg_lon)
        res_y = max(1e-9, resolution / m_per_deg_lat)
        c_res_x = max(1e-9, coarse_res_m / m_per_deg_lon)
        c_res_y = max(1e-9, coarse_res_m / m_per_deg_lat)
        span_x_m = (x_max - x_min) * m_per_deg_lon
        span_y_m = (y_max - y_min) * m_per_deg_lat
        log(f"Geographic WGS 84 coordinate reference detected: <b>{span_x_m:.1f} m × {span_y_m:.1f} m</b> ground extent.")
    else:
        res_x = resolution
        res_y = resolution
        c_res_x = coarse_res_m
        c_res_y = coarse_res_m

    cols = max(1, int(np.ceil((x_max - x_min) / res_x)))
    rows = max(1, int(np.ceil((y_max - y_min) / res_y)))
    c_cols = max(1, int(np.ceil((x_max - x_min) / c_res_x)))
    c_rows = max(1, int(np.ceil((y_max - y_min) / c_res_y)))
    log(f"Allocating raster models: Fine DSM/CHM: <b>{cols} × {rows}</b> px ({resolution:.2f} m), Coarse Terrain: <b>{c_cols} × {c_rows}</b> px.")

    # 3. CRS Detection
    crs_wkt = ""
    try:
        from qgis.core import QgsPointCloudLayer
        probe = QgsPointCloudLayer(point_cloud_path, "probe", "pdal")
        if not probe.isValid():
            probe = QgsPointCloudLayer(point_cloud_path, "probe", "copc")
        if probe.isValid() and probe.crs().isValid():
            crs_wkt = probe.crs().toWkt()
    except Exception:
        pass

    if not crs_wkt and header_crs:
        try:
            crs_wkt = header_crs.to_wkt()
        except Exception:
            pass

    if not crs_wkt:
        srs = osr.SpatialReference()
        if is_geographic:
            srs.ImportFromEPSG(4326)
        else:
            srs.ImportFromEPSG(32643)
        crs_wkt = srs.ExportToWkt()

    # 4. Out-of-Core Stream Ingestion & Statistical Outlier Filtering
    dsm_1d = np.full(rows * cols, -1e9, dtype=np.float32)
    c_min_1d = np.full(c_rows * c_cols, 1e9, dtype=np.float32)
    ground_min_1d = np.full(rows * cols, 1e9, dtype=np.float32)
    class_2_count = 0

    has_rgb_detected = False
    exg_sum = np.zeros(rows * cols, dtype=np.float32)
    exg_cnt = np.zeros(rows * cols, dtype=np.int32)

    chunk_size = 1_500_000
    processed_pts = 0

    progress(10, "Streaming 3D point chunks (Out-of-Core Memory Pipeline)...")

    with laspy.open(point_cloud_path) as fh:
        for chunk in fh.chunk_iterator(chunk_size):
            cx = np.array(chunk.x, copy=False)
            cy = np.array(chunk.y, copy=False)
            cz = np.array(chunk.z, copy=False)

            has_cls = hasattr(chunk, "classification")
            cls_arr = np.array(chunk.classification, copy=False) if has_cls else None

            # Outlier and noise filtering:
            # Drop ASPRS Class 7 (Low Point / Noise) and Class 18 (High Noise)
            valid_mask = (cz >= z_min) & (cz <= z_max)
            if cls_arr is not None:
                valid_mask &= (cls_arr != 7) & (cls_arr != 18)
                g_mask = (cls_arr == 2) & valid_mask
                if np.any(g_mask):
                    class_2_count += int(np.sum(g_mask))

            cx_v = cx[valid_mask]
            cy_v = cy[valid_mask]
            cz_v = cz[valid_mask]

            if len(cx_v) == 0:
                continue

            # Fine cell binning
            px = np.clip(((cx_v - x_min) / res_x).astype(np.int32), 0, cols - 1)
            py = np.clip(((y_max - cy_v) / res_y).astype(np.int32), 0, rows - 1)
            cell_idx = py * cols + px

            # Coarse cell binning
            c_px = np.clip(((cx_v - x_min) / c_res_x).astype(np.int32), 0, c_cols - 1)
            c_py = np.clip(((y_max - cy_v) / c_res_y).astype(np.int32), 0, c_rows - 1)
            c_cell = c_py * c_cols + c_px

            # Canopy DSM maximum and coarse terrain minimum
            np.maximum.at(dsm_1d, cell_idx, cz_v)
            np.minimum.at(c_min_1d, c_cell, cz_v)

            # Ground minimum if classified
            if cls_arr is not None and np.any(g_mask):
                cls_v = cls_arr[valid_mask]
                is_g = (cls_v == 2)
                np.minimum.at(ground_min_1d, cell_idx[is_g], cz_v[is_g])

            # RGB Foliage Accumulation
            if hasattr(chunk, "red") and hasattr(chunk, "green") and hasattr(chunk, "blue"):
                has_rgb_detected = True
                r = np.array(chunk.red, dtype=np.float32)[valid_mask]
                g = np.array(chunk.green, dtype=np.float32)[valid_mask]
                b = np.array(chunk.blue, dtype=np.float32)[valid_mask]
                norm_exg = (2.0 * g - r - b) / (r + g + b + 1e-6)
                np.add.at(exg_sum, cell_idx, norm_exg)
                np.add.at(exg_cnt, cell_idx, 1)

            processed_pts += len(cx)
            pct = 10 + int(45 * (processed_pts / max(1, total_pts)))
            progress(pct, f"Streaming point cloud: {processed_pts:,} / {total_pts:,} points...")

    stream_time = time.time() - t0
    log(f"Streamed <b>{processed_pts:,}</b> points in <b>{stream_time:.2f} s</b>. Classified Ground returns: <b>{class_2_count:,}</b>.")

    # 5. Bare-Earth Ground DTM Derivation with Spatial Coverage Validation
    progress(58, "Evaluating ground classification spatial coverage & deriving DTM...")
    from scipy.ndimage import grey_erosion, grey_dilation, zoom, gaussian_filter

    # Check both point count and spatial coverage (occupied coarse grid cells)
    has_class_2_points = (class_2_count > max(500, int(0.005 * total_pts)))
    ground_spatial_coverage_ratio = 0.0

    if has_class_2_points:
        dtm_g = ground_min_1d.copy()
        dtm_g[dtm_g > 1e8] = np.nan
        dtm_2d = dtm_g.reshape((rows, cols))
        valid_g_cells = ~np.isnan(dtm_2d)
        ground_spatial_coverage_ratio = float(np.sum(valid_g_cells) / max(1, np.sum(dsm_1d > -1e8)))

    # To trust ASPRS Class 2 directly, ground returns must adequately cover the survey footprint
    min_coverage_ratio = max(0.05, min(0.50, ground_coverage_threshold_pct / 100.0))
    trust_classified_ground = has_class_2_points and (ground_spatial_coverage_ratio >= min_coverage_ratio)
    dtm_source = "ASPRS Class 2" if trust_classified_ground else "Multi-Scale Morphological Opening"
    dtm_confidence = "HIGH" if trust_classified_ground else "MODERATE"

    log(f"• Ground cells occupied: <b>{ground_spatial_coverage_ratio * 100:.1f}%</b>")
    log(f"• Ground extraction source: <b>{dtm_source}</b>")
    log(f"• DTM topographic confidence: <b>{dtm_confidence}</b>")

    if trust_classified_ground:
        inv_dtm = np.isnan(dtm_2d)
        if np.any(inv_dtm):
            dist_g, idx_g = distance_transform_edt(inv_dtm, return_indices=True)
            dtm_2d[inv_dtm] = dtm_2d[idx_g[0][inv_dtm], idx_g[1][inv_dtm]]
        dtm_fine = dtm_2d
    else:
        c_min_1d[c_min_1d > 1e8] = np.nan
        c_grid = c_min_1d.reshape((c_rows, c_cols))
        c_inv = np.isnan(c_grid)
        if np.any(c_inv):
            _, idx_c = distance_transform_edt(c_inv, return_indices=True)
            c_grid[c_inv] = c_grid[idx_c[0][c_inv], idx_c[1][c_inv]]

        # Morphological opening (erosion then dilation) over coarse grid to eliminate tree canopies
        win = 5
        c_eroded = grey_erosion(c_grid, size=(win, win))
        c_opened = grey_dilation(c_eroded, size=(win, win))
        c_smoothed = gaussian_filter(c_opened, sigma=1.0)

        # Resample bare-earth DTM to fine grid resolution
        dtm_fine = zoom(c_smoothed, (rows / c_rows, cols / c_cols), order=1)[:rows, :cols]
        if dtm_fine.shape != (rows, cols):
            padded = np.full((rows, cols), np.mean(dtm_fine), dtype=np.float32)
            mr = min(rows, dtm_fine.shape[0])
            mc = min(cols, dtm_fine.shape[1])
            padded[:mr, :mc] = dtm_fine[:mr, :mc]
            dtm_fine = padded

    # 6. Normalized Canopy Height Model: CHM = DSM - DTM
    progress(72, "Computing normalized canopy height model (CHM = DSM - DTM)...")
    valid_dsm_mask = (dsm_1d > -1e8)
    dsm_2d = dsm_1d.reshape((rows, cols))
    dsm_2d[~valid_dsm_mask.reshape((rows, cols))] = np.nan

    valid_cells = ~np.isnan(dsm_2d)
    chm_2d = np.zeros((rows, cols), dtype=np.float32)
    chm_2d[valid_cells] = np.maximum(0.0, dsm_2d[valid_cells] - dtm_fine[valid_cells])

    # 7. RGB Spectral Greenness Validation (Optional Enhancement)
    if has_rgb_detected:
        progress(82, "Applying RGB spectral foliage validation (Excess Green Index)...")
        has_pts = exg_cnt > 0
        mean_exg = np.full(rows * cols, 0.0, dtype=np.float32)
        mean_exg[has_pts] = exg_sum[has_pts] / exg_cnt[has_pts]
        mean_exg_2d = mean_exg.reshape((rows, cols))

        # Filter out bare soil / road / artificial surfaces with neutral/negative ExG
        non_green = (mean_exg_2d <= 0.045) & valid_cells
        chm_2d[non_green] = 0.0
        log(f"Applied spectral RGB foliage mask: Cleared <b>{int(np.sum(non_green)):,}</b> non-vegetated bare ground pixels.")

    # 8. Write GeoTIFF
    clean_base = os.path.splitext(os.path.basename(point_cloud_path))[0]
    out_tif = os.path.join(tempfile.gettempdir(), f"{clean_base}_derived_chm.tif")

    gt = (x_min, res_x, 0.0, y_max, 0.0, -res_y)
    drv = gdal.GetDriverByName("GTiff")
    ds_out = drv.Create(out_tif, cols, rows, 1, gdal.GDT_Float32, ["TILED=YES", "COMPRESS=LZW"])
    ds_out.SetGeoTransform(gt)
    if crs_wkt:
        ds_out.SetProjection(crs_wkt)

    b = ds_out.GetRasterBand(1)
    b.SetNoDataValue(0.0)
    b.WriteArray(chm_2d)
    b.FlushCache()
    ds_out.FlushCache()
    ds_out = None

    elapsed = time.time() - t0
    log(f"Normalized CHM generated in <b>{elapsed:.2f} s</b> (Maximum Height: <b>{float(chm_2d.max()):.1f} m</b>).")
    meta = {
        "point_count": total_pts,
        "ground_cells_occupied_pct": round(ground_spatial_coverage_ratio * 100, 1),
        "ground_source": dtm_source,
        "dtm_confidence": dtm_confidence,
        "resolution_m": round((res_x + res_y) / 2.0, 2),
        "input_file": os.path.basename(point_cloud_path),
        "crs_wkt": crs_wkt
    }

    return CHMDerivationResult(chm_2d, gt, crs_wkt, out_tif, meta)

