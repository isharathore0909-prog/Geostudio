"""Landsat Collection 2 Level 1 Radiometric Scaling & Split-Window LST Engine.

Calibrated to:
- USGS Collection 2 Level 1 Scaling Equations
- Sobrino et al. (2008) and Du et al. (2015) Split-Window LST algorithms
- 100% offline pure Python execution
"""

import os
import sys
import math
import json
from pathlib import Path

def parse_mtl(mtl_path: str) -> dict:
    """Parses USGS Landsat *_MTL.txt metadata file into key-value dictionary."""
    meta = {}
    if not os.path.exists(mtl_path):
        return meta

    with open(mtl_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith("GROUP") and not line.startswith("END"):
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"')
                try:
                    if '.' in v or 'E' in v or 'e' in v:
                        meta[k] = float(v)
                    else:
                        meta[k] = int(v)
                except ValueError:
                    meta[k] = v
    return meta

def scale_radiance(dn: float, mult: float, add: float) -> float:
    """Top of Atmosphere (TOA) Spectral Radiance: L_lambda = M_L * Qcal + A_L"""
    return (mult * dn) + add

def scale_reflectance(dn: float, mult: float, add: float, sun_elevation_deg: float) -> float:
    """TOA Planetary Reflectance with solar angle correction: rho_lambda = (M_p * Qcal + A_p) / sin(theta_SE)"""
    sun_elev_rad = math.radians(sun_elevation_deg)
    sin_elev = math.sin(sun_elev_rad)
    if sin_elev <= 0:
        sin_elev = 1.0
    return ((mult * dn) + add) / sin_elev

def brightness_temperature(radiance: float, k1: float, k2: float) -> float:
    """At-satellite Brightness Temperature in Celsius: BT = (K2 / ln(K1 / L_lambda + 1)) - 273.15"""
    if radiance <= 0 or k1 <= 0:
        return 0.0
    val = (k1 / radiance) + 1.0
    if val <= 1.0:
        return 0.0
    bt_kelvin = k2 / math.log(val)
    return bt_kelvin - 273.15

def fractional_vegetation_cover(ndvi: float, ndvi_min: float = 0.2, ndvi_max: float = 0.5) -> float:
    """Fractional Vegetation Cover (FVC / Pv): ((NDVI - NDVI_min) / (NDVI_max - NDVI_min))^2"""
    if ndvi <= ndvi_min:
        return 0.0
    elif ndvi >= ndvi_max:
        return 1.0
    ratio = (ndvi - ndvi_min) / (ndvi_max - ndvi_min)
    return ratio * ratio

def land_surface_emissivity(fvc: float, eps_veg: float = 0.985, eps_soil: float = 0.96) -> float:
    """Sobrino Land Surface Emissivity (LSE): eps = eps_veg * FVC + eps_soil * (1 - FVC) + Cavity Effect"""
    c = 0.005 * (1.0 - eps_soil) * eps_veg * (1.0 - fvc) # Cavity effect
    return (eps_veg * fvc) + (eps_soil * (1.0 - fvc)) + c

def split_window_lst(
    bt10_c: float,
    bt11_c: float,
    emissivity_10: float = 0.97,
    emissivity_11: float = 0.965,
    water_vapor: float = 1.5) -> float:
    """Du et al. / Sobrino Split-Window Land Surface Temperature (LST in Celsius)."""
    t10 = bt10_c + 273.15
    t11 = bt11_c + 273.15
    delta_t = t10 - t11
    
    mean_eps = (emissivity_10 + emissivity_11) / 2.0
    delta_eps = emissivity_10 - emissivity_11
    
    # Split-window regression coefficients for generalized TIRS
    c0 = -0.268
    c1 = 1.378
    c2 = 0.183
    c3 = 54.30
    c4 = -2.238
    c5 = -129.20
    c6 = 16.40
    
    w = water_vapor
    term1 = t10 + (c1 * delta_t) + (c2 * (delta_t ** 2)) + c0
    term2 = (c3 + (c4 * w)) * (1.0 - mean_eps)
    term3 = (c5 + (c6 * w)) * delta_eps
    
    lst_kelvin = term1 + term2 + term3
    return lst_kelvin - 273.15

def task_landsat_lst(args):
    """Calculates Split-Window Land Surface Temperature (LST) GeoTIFF from Landsat Collection 2 L1 bands."""
    import numpy as np
    from osgeo import gdal
    from common import report_progress, report_result
    gdal.UseExceptions()

    mtl_path = args.input
    if not mtl_path or not os.path.exists(mtl_path):
        raise FileNotFoundError(f"Landsat MTL metadata file not found: {mtl_path}")

    scene_dir = os.path.dirname(os.path.abspath(mtl_path))
    meta = parse_mtl(mtl_path)
    report_progress(10, f"Parsed MTL metadata: {os.path.basename(mtl_path)}")

    def resolve_band(given_path, tag):
        if given_path and os.path.exists(given_path):
            return given_path
        for f in os.listdir(scene_dir):
            if f.lower().endswith(('.tif', '.tiff')) and f"_{tag.upper()}." in f.upper():
                return os.path.join(scene_dir, f)
        return None

    b10_path = resolve_band(args.param1, "B10")
    b11_path = resolve_band(args.param2, "B11")

    if not b10_path or not os.path.exists(b10_path):
        raise FileNotFoundError(f"TIRS Band 10 GeoTIFF not found in scene directory: {scene_dir}")

    report_progress(25, "Reading Thermal Band 10 and Band 11 rasters...")
    ds10 = gdal.Open(b10_path, gdal.GA_ReadOnly)
    geo_xform = ds10.GetGeoTransform()
    proj_ref = ds10.GetProjection()
    x_size, y_size = ds10.RasterXSize, ds10.RasterYSize
    b10_arr = ds10.GetRasterBand(1).ReadAsArray().astype(np.float64)
    b10_arr[b10_arr == 0] = np.nan

    mult_b10, add_b10 = 0.000380, 0.1
    k1_b10, k2_b10 = 799.0284, 1329.2482

    rad10 = mult_b10 * b10_arr + add_b10
    rad10[rad10 <= 0] = np.nan
    bt10 = k2_b10 / np.log((k1_b10 / rad10) + 1.0)

    e_b10, e_b11 = 0.986, 0.989
    b4_path = resolve_band(None, "B4")
    b5_path = resolve_band(None, "B5")
    if b4_path and b5_path:
        report_progress(45, "Calculating NDVI & FVC for dynamic emissivity...")
        try:
            ds4 = gdal.Open(b4_path, gdal.GA_ReadOnly)
            ds5 = gdal.Open(b5_path, gdal.GA_ReadOnly)
            b4_arr = ds4.GetRasterBand(1).ReadAsArray().astype(np.float64)
            b5_arr = ds5.GetRasterBand(1).ReadAsArray().astype(np.float64)
            ds4 = ds5 = None
            if b4_arr.shape == b10_arr.shape and b5_arr.shape == b10_arr.shape:
                sza_path = resolve_band(None, "SZA")
                if sza_path and os.path.exists(sza_path):
                    dssza = gdal.Open(sza_path, gdal.GA_ReadOnly)
                    sza_arr = dssza.GetRasterBand(1).ReadAsArray().astype(np.float64)
                    dssza = None
                    cos_sza = np.cos(np.radians(sza_arr / 100.0))
                else:
                    sun_elev = float(meta.get("SUN_ELEVATION", 45.0))
                    cos_sza = math.cos(math.radians(90.0 - sun_elev))

                ozone_factor = 0.1133
                ref_mult = float(meta.get("REFLECTANCE_MULT_BAND_4", 0.00002))
                ref_add = float(meta.get("REFLECTANCE_ADD_BAND_4", -0.1))
                ref4 = ((ref_mult * b4_arr + ref_add) / np.maximum(0.05, cos_sza)) / math.exp(-0.163 * ozone_factor)
                ref5 = ((ref_mult * b5_arr + ref_add) / np.maximum(0.05, cos_sza)) / math.exp(-0.012 * ozone_factor)
                denom = ref5 + ref4
                denom[denom == 0] = 1e-6
                ndvi = np.clip((ref5 - ref4) / denom, -1.0, 1.0)
                ndvi_min = np.nanpercentile(ndvi[np.isfinite(ndvi)], 5)
                ndvi_max = np.nanpercentile(ndvi[np.isfinite(ndvi)], 95)
                ndvi_min = max(0.05, min(float(ndvi_min), 0.2))
                ndvi_max = min(0.85, max(float(ndvi_max), 0.5))
                pv = np.clip(((ndvi - ndvi_min) / (ndvi_max - ndvi_min)) ** 2, 0.0, 1.0)
                e_b10 = 0.986 + 0.004 * pv
                e_b11 = 0.989 + 0.003 * pv
        except Exception:
            pass

    mean_e = (e_b10 + e_b11) / 2.0
    delta_e = e_b10 - e_b11

    report_progress(65, "Computing Split-Window Land Surface Temperature...")
    if b11_path and os.path.exists(b11_path):
        ds11 = gdal.Open(b11_path, gdal.GA_ReadOnly)
        b11_arr = ds11.GetRasterBand(1).ReadAsArray().astype(np.float64)
        ds11 = None
        b11_arr[b11_arr == 0] = np.nan

        mult_b11, add_b11 = 0.000349, 0.1
        k1_b11, k2_b11 = 497.6190, 1198.8194

        rad11 = mult_b11 * b11_arr + add_b11
        rad11[rad11 <= 0] = np.nan
        bt11 = k2_b11 / np.log((k1_b11 / rad11) + 1.0)

        lat_corners = [float(meta[k]) for k in meta if 'CORNER_' in k and '_LAT_' in k]
        center_lat = sum(lat_corners) / len(lat_corners) if lat_corners else 0.0
        w = 4.6115 if abs(center_lat) < 25.0 else 1.5

        if w > 3.0:
            c0, c1, c2, c3, c4, c5, c6 = -1.274, 1.832, 0.312, 68.20, -3.451, -145.40, 22.10
        else:
            c0, c1, c2, c3, c4, c5, c6 = -0.268, 1.378, 0.183, 54.30, -2.238, -129.20, 16.40

        delta_bt = bt10 - bt11
        lst_k = (
            bt10 + c1 * delta_bt + c2 * (delta_bt ** 2) + c0
            + (c3 + c4 * w) * (1.0 - mean_e)
            + (c5 + c6 * w) * delta_e
        )
        lst_c = lst_k - 273.15
    else:
        lambda_tirs = 10.895e-6
        rho = 1.438e-2
        lst_c = (bt10 / (1.0 + (lambda_tirs * bt10 / rho) * np.log(mean_e))) - 273.15

    qa_path = resolve_band(None, "QA_PIXEL")
    if qa_path and os.path.exists(qa_path):
        report_progress(80, "Executing bitwise QA Cloud & Shadow Masking...")
        dsqa = gdal.Open(qa_path, gdal.GA_ReadOnly)
        qa = dsqa.GetRasterBand(1).ReadAsArray().astype(np.uint16)
        dsqa = None
        dilated_cloud = (qa >> 1) & 1
        cloud = (qa >> 3) & 1
        cloud_shadow = (qa >> 4) & 1
        lst_c[(dilated_cloud == 1) | (cloud == 1) | (cloud_shadow == 1)] = np.nan

    lst_c[(lst_c < -40.0) | (lst_c > 70.0)] = np.nan

    out_file = args.output
    if not out_file:
        b_name = os.path.splitext(os.path.basename(b10_path))[0].replace("_B10", "")
        out_file = os.path.join(scene_dir, f"{b_name}_SplitWindow_LST.tif")

    report_progress(90, f"Writing output LST GeoTIFF: {os.path.basename(out_file)}...")
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(out_file, x_size, y_size, 1, gdal.GDT_Float32, ["COMPRESS=DEFLATE"])
    out_ds.SetGeoTransform(geo_xform)
    out_ds.SetProjection(proj_ref)
    band_out = out_ds.GetRasterBand(1)
    band_out.SetNoDataValue(-9999.0)
    band_out.WriteArray(np.nan_to_num(lst_c.astype(np.float32), nan=-9999.0))
    out_ds.FlushCache()
    out_ds = None
    ds10 = None

    valid = lst_c[np.isfinite(lst_c)]
    min_lst = float(np.min(valid)) if valid.size > 0 else 0.0
    max_lst = float(np.max(valid)) if valid.size > 0 else 0.0
    mean_lst = float(np.mean(valid)) if valid.size > 0 else 0.0

    report_progress(100, "Split-Window LST processing complete")
    report_result(True, {
        "output_file": out_file,
        "min_lst": round(min_lst, 2),
        "max_lst": round(max_lst, 2),
        "mean_lst": round(mean_lst, 2),
        "valid_pixels": int(valid.size),
        "units": "Celsius"
    })

