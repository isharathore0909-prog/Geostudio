# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - Raster Processing & Remote Sensing Tasks
Calculates Spectral Indices (NDVI, NDWI, EVI, NDBI, NBR, False-Color),
clips raster datasets using vector masks, and computes detailed statistics & histograms.
"""

import os
import json
import numpy as np

from common import report_progress, report_result


def task_satellite_index(args):
    """Calculates Spectral Indices: NDVI, EVI, NDWI, NDBI, NBR, and False Color Composite."""
    from osgeo import gdal
    gdal.UseExceptions()

    raster_path = args.input
    if not raster_path or not os.path.exists(raster_path):
        raise FileNotFoundError(f"Input raster not found: {raster_path}")

    index_name = (args.mode or args.param1 or "ndvi").upper().replace("-", "_").replace(" ", "_")
    out_path = args.output or os.path.splitext(raster_path)[0] + f"_{index_name}.tif"

    report_progress(15, f"Opening multispectral raster for {index_name}...")
    ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
    band_count = ds.RasterCount
    if band_count < 1:
        raise ValueError(f"Raster dataset has no bands: {raster_path}")

    # Parse custom band mapping if provided in param2 as JSON
    band_map = {}
    if args.param2:
        try:
            band_map = json.loads(args.param2)
        except Exception:
            pass

    from tasks.spectral_helpers import find_sibling_band, read_band_array, align_shapes

    # Resolve individual band files if single-band raster or explicitly provided
    nir_file = band_map.get("nir_file") or (find_sibling_band(raster_path, ["B5", "B8", "B08", "5", "8"]) if band_count == 1 else None)
    red_file = band_map.get("red_file") or (find_sibling_band(raster_path, ["B4", "B04", "4"]) if band_count == 1 else None)
    green_file = band_map.get("green_file") or (find_sibling_band(raster_path, ["B3", "B03", "3"]) if band_count == 1 else None)
    blue_file = band_map.get("blue_file") or (find_sibling_band(raster_path, ["B2", "B02", "2"]) if band_count == 1 else None)
    swir1_file = band_map.get("swir1_file") or (find_sibling_band(raster_path, ["B6", "B11", "6"]) if band_count == 1 else None)
    swir2_file = band_map.get("swir2_file") or (find_sibling_band(raster_path, ["B7", "B12", "7"]) if band_count == 1 else None)

    if band_count == 1 and not nir_file and not red_file:
        raise ValueError(
            f"The selected raster '{os.path.basename(raster_path)}' contains only 1 band. "
            f"NDVI requires NIR and Red bands. Sibling band files (_B5/_B4) were not found in this folder."
        )

    # Defaults according to sensor preset or available band count
    nir_band = max(1, min(band_count, int(band_map.get("nir", 8 if band_count >= 8 else (5 if band_count >= 5 else 1)))))
    red_band = max(1, min(band_count, int(band_map.get("red", 4 if band_count >= 4 else (3 if band_count >= 3 else 1)))))
    green_band = max(1, min(band_count, int(band_map.get("green", 3 if band_count >= 3 else (2 if band_count >= 2 else 1)))))
    blue_band = max(1, min(band_count, int(band_map.get("blue", 2 if band_count >= 2 else 1))))
    swir1_band = max(1, min(band_count, int(band_map.get("swir1", 11 if band_count >= 11 else (6 if band_count >= 6 else 1)))))
    swir2_band = max(1, min(band_count, int(band_map.get("swir2", 12 if band_count >= 12 else (7 if band_count >= 7 else 1)))))

    # Reference dataset for dimensions and projection
    ref_ds = gdal.Open(nir_file or red_file, gdal.GA_ReadOnly) if (nir_file or red_file) else ds
    driver = gdal.GetDriverByName("GTiff")
    geo_xform = ref_ds.GetGeoTransform()
    proj_ref = ref_ds.GetProjection()
    x_size = ref_ds.RasterXSize
    y_size = ref_ds.RasterYSize
    if ref_ds != ds:
        ref_ds = None

    np.seterr(divide='ignore', invalid='ignore')

    if index_name in ("FALSE_COLOR", "FALSECOLOR", "COMPOSITE"):
        report_progress(35, "Generating False-Color Infrared Composite (NIR / Red / Green)...")
        arr_r = read_band_array(ds, nir_band, nir_file)
        report_progress(55, "Enhancing color contrast dynamics...")
        arr_g = read_band_array(ds, red_band, red_file)
        arr_b = read_band_array(ds, green_band, green_file)

        def stretch(arr):
            valid = arr[np.isfinite(arr)]
            if valid.size == 0:
                return np.zeros_like(arr, dtype=np.uint8)
            p2, p98 = np.percentile(valid, (2, 98))
            if p98 <= p2:
                p2, p98 = valid.min(), valid.max()
            if p98 <= p2:
                p98 = p2 + 1e-5
            scaled = (np.clip(arr, p2, p98) - p2) / (p98 - p2) * 255.0
            return np.nan_to_num(scaled, nan=0.0).astype(np.uint8)

        out_ds = driver.Create(out_path, x_size, y_size, 3, gdal.GDT_Byte, ["COMPRESS=DEFLATE"])
        out_ds.SetGeoTransform(geo_xform)
        out_ds.SetProjection(proj_ref)
        out_ds.GetRasterBand(1).WriteArray(stretch(arr_r))
        out_ds.GetRasterBand(2).WriteArray(stretch(arr_g))
        out_ds.GetRasterBand(3).WriteArray(stretch(arr_b))
        out_ds.FlushCache()
        out_ds = None
        ds = None

        report_progress(100, "False Color composite generated successfully")
        report_result(True, {"output_file": out_path, "index": index_name})
        return

    report_progress(40, f"Reading multispectral bands for {index_name} calculation...")
    nir = read_band_array(ds, nir_band, nir_file)
    red = read_band_array(ds, red_band, red_file)
    target_shape = nir.shape
    red = align_shapes(red, target_shape)
    x_size, y_size = target_shape[1], target_shape[0]

    report_progress(65, f"Computing {index_name} formula...")
    if index_name == "NDVI":
        denom = nir + red
        denom[denom == 0] = 1e-6
        result = (nir - red) / denom
        result = np.clip(result, -1.0, 1.0)
    elif index_name in ("NDWI", "WATER"):
        green = align_shapes(read_band_array(ds, green_band, green_file), target_shape)
        denom = green + nir
        denom[denom == 0] = 1e-6
        result = (green - nir) / denom
        result = np.clip(result, -1.0, 1.0)
    elif index_name == "EVI":
        blue = align_shapes(read_band_array(ds, blue_band, blue_file), target_shape)
        denom = nir + 6.0 * red - 7.5 * blue + 1.0
        denom[denom == 0] = 1e-6
        result = 2.5 * (nir - red) / denom
        result = np.clip(result, -1.5, 1.5)
    elif index_name == "NDBI":
        swir1 = align_shapes(read_band_array(ds, swir1_band, swir1_file), target_shape)
        denom = swir1 + nir
        denom[denom == 0] = 1e-6
        result = (swir1 - nir) / denom
        result = np.clip(result, -1.0, 1.0)
    elif index_name in ("NBR", "BURN"):
        swir2 = align_shapes(read_band_array(ds, swir2_band, swir2_file), target_shape)
        denom = nir + swir2
        denom[denom == 0] = 1e-6
        result = (nir - swir2) / denom
        result = np.clip(result, -1.0, 1.0)
    else:
        denom = nir + red
        denom[denom == 0] = 1e-6
        result = (nir - red) / denom
        result = np.clip(result, -1.0, 1.0)

    report_progress(85, f"Writing output GeoTIFF for {index_name}...")
    out_ds = driver.Create(out_path, x_size, y_size, 1, gdal.GDT_Float32, ["COMPRESS=DEFLATE"])
    out_ds.SetGeoTransform(geo_xform)
    out_ds.SetProjection(proj_ref)
    band_out = out_ds.GetRasterBand(1)
    band_out.SetNoDataValue(-9999.0)
    result = np.nan_to_num(result, nan=-9999.0)
    band_out.WriteArray(result)
    out_ds.FlushCache()
    out_ds = None
    ds = None

    report_progress(100, f"{index_name} calculation finished successfully")
    report_result(True, {"output_file": out_path, "index": index_name})


def task_clip_raster(args):
    """Clips raster dataset using vector boundary polygon or bounding box."""
    report_progress(5, "Initializing Clip Raster...")
    from osgeo import gdal
    gdal.UseExceptions()

    in_file = args.input
    if not in_file or not os.path.exists(in_file):
        raise ValueError(f"Input raster file not found: {in_file}")

    mask_file = args.param1
    if not mask_file:
        raise ValueError("Clipping mask (vector polygon file or bounding box) is required.")

    out_file = args.output
    if not out_file:
        base, ext = os.path.splitext(in_file)
        out_file = f"{base}_clipped.tif"

    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    report_progress(20, "Configuring GDAL Warp...")

    def _gdal_prog(pct, msg, x):
        report_progress(int(20 + pct * 75), f"Clipping: {int(pct * 100)}%")
        return 1

    if os.path.exists(mask_file):
        warp_opts = gdal.WarpOptions(
            cutlineDSName=mask_file,
            cropToCutline=True,
            callback=_gdal_prog
        )
    else:
        parts = [float(p.strip()) for p in mask_file.split(",")]
        if len(parts) == 4:
            warp_opts = gdal.WarpOptions(
                outputBounds=parts,
                outputBoundsSRS='EPSG:4326',
                callback=_gdal_prog
            )
        else:
            raise ValueError(f"Mask file not found and not a valid bounding box: {mask_file}")

    gdal.Warp(out_file, in_file, options=warp_opts)
    report_progress(100, "Raster clip complete")
    report_result(True, {"output_file": out_file})


def task_raster_stats(args):
    """Computes Min, Max, Mean, StdDev, and 256-bin histogram for a raster band."""
    report_progress(10, "Opening raster dataset...")
    from osgeo import gdal
    gdal.UseExceptions()

    in_file = args.input
    if not in_file or not os.path.exists(in_file):
        raise ValueError(f"Input raster not found: {in_file}")

    ds = gdal.Open(in_file, gdal.GA_ReadOnly)
    band_idx = int(args.param1) if args.param1 and args.param1.isdigit() else 1
    if band_idx < 1 or band_idx > ds.RasterCount:
        band_idx = 1

    band = ds.GetRasterBand(band_idx)
    report_progress(40, f"Calculating statistics for Band {band_idx}...")
    stats = band.GetStatistics(True, True)

    report_progress(70, "Generating histogram...")
    min_v, max_v = stats[0], stats[1]
    if min_v == max_v:
        max_v = min_v + 1.0
    hist = band.GetHistogram(min_v, max_v, 256, False, False)

    nodata = band.GetNoDataValue()
    data_type = gdal.GetDataTypeName(band.DataType)
    w, h = ds.RasterXSize, ds.RasterYSize
    gt = ds.GetGeoTransform()
    srs = ds.GetProjection()

    report_progress(100, "Raster statistics computed")
    report_result(True, {
        "band": band_idx,
        "band_count": ds.RasterCount,
        "min": round(stats[0], 4),
        "max": round(stats[1], 4),
        "mean": round(stats[2], 4),
        "stddev": round(stats[3], 4),
        "histogram": list(hist),
        "nodata": nodata,
        "data_type": data_type,
        "width": w,
        "height": h,
        "pixel_size_x": abs(gt[1]) if gt else 0,
        "pixel_size_y": abs(gt[5]) if gt else 0,
        "crs": srs
    })
    ds = None


def task_viewshed(args):
    """Calculates 3D line-of-sight visibility / viewshed from observer point using GDAL."""
    import math
    from osgeo import gdal, osr
    gdal.UseExceptions()

    # Safety for PROJ database lookup across Windows environments
    for p in [r"C:\Program Files\QGIS 3.40.14\share\proj", r"C:\Program Files\QGIS 3.40.14\apps\proj\share\proj"]:
        if os.path.exists(p):
            os.environ["PROJ_LIB"] = p
            os.environ["PROJ_DATA"] = p
            try:
                osr.SetPROJSearchPaths([p])
            except Exception:
                pass
            break

    dem_path = args.input
    if not dem_path or not os.path.exists(dem_path):
        raise FileNotFoundError(f"Input DEM raster not found: {dem_path}")

    # Parse parameters
    params = {}
    if args.param1:
        try:
            params = json.loads(args.param1)
        except Exception:
            pass

    out_path = args.output
    if not out_path:
        out_path = os.path.splitext(dem_path)[0] + "_viewshed.tif"

    report_progress(10, "Opening DEM for line-of-sight analysis...")
    ds = gdal.Open(dem_path, gdal.GA_ReadOnly)
    gt = ds.GetGeoTransform()

    # Determine coordinate system (Geographic vs Projected)
    is_geo = False
    srs_wkt = ds.GetProjection()
    if srs_wkt:
        try:
            srs = osr.SpatialReference(srs_wkt)
            is_geo = bool(srs.IsGeographic())
        except Exception:
            pass
    if not is_geo and abs(gt[0]) <= 180.0 and abs(gt[3]) <= 90.0:
        is_geo = True

    # Raster spatial bounds
    x_min = min(gt[0], gt[0] + ds.RasterXSize * gt[1])
    x_max = max(gt[0], gt[0] + ds.RasterXSize * gt[1])
    y_min = min(gt[3], gt[3] + ds.RasterYSize * gt[5])
    y_max = max(gt[3], gt[3] + ds.RasterYSize * gt[5])

    center_x = (x_min + x_max) / 2.0
    center_y = (y_min + y_max) / 2.0

    obs_x = float(params.get("observer_x", center_x))
    obs_y = float(params.get("observer_y", center_y))
    obs_h = float(params.get("observer_h", 2.0))
    tgt_h = float(params.get("target_h", 0.0))
    max_d_m = float(params.get("max_distance", 5000.0))
    curv_coeff = float(params.get("curvature_coeff", 0.85714))

    # Clamp observer coordinates into raster extent to prevent out-of-bounds error
    obs_x = max(x_min, min(x_max, obs_x))
    obs_y = max(y_min, min(y_max, obs_y))

    # Convert distance to native raster coordinate units and calculate cell area in m^2
    extent_diag = math.hypot(abs(x_max - x_min), abs(y_max - y_min))
    if is_geo:
        rad_lat = math.radians(min(89.0, max(-89.0, obs_y)))
        cos_lat = max(0.01, math.cos(rad_lat))
        deg_per_m_lat = 1.0 / 111320.0
        deg_per_m_lon = 1.0 / (111320.0 * cos_lat)

        max_d_native = max_d_m * max(deg_per_m_lat, deg_per_m_lon)
        if max_d_m <= 0 or max_d_native >= extent_diag:
            gdal_max_dist = 0.0  # GDAL 0.0 = compute without distance clipping error
        else:
            gdal_max_dist = float(max_d_native)

        cell_w_m = abs(gt[1]) * 111320.0 * cos_lat
        cell_h_m = abs(gt[5]) * 111320.0
        cell_area_m2 = cell_w_m * cell_h_m
    else:
        if max_d_m <= 0 or max_d_m >= extent_diag:
            gdal_max_dist = 0.0
        else:
            gdal_max_dist = float(max_d_m)
        cell_area_m2 = abs(gt[1] * gt[5])

    report_progress(25, "Optimizing surface resolution and observer geometry...")

    # Performance optimization for ultra-high-resolution drone datasets (> 4000x4000 pixels)
    vrt_ds = None
    src_band = ds.GetRasterBand(1)
    max_dim = max(ds.RasterXSize, ds.RasterYSize)
    if max_dim > 4000:
        scale_factor = int(math.ceil(max_dim / 4000.0))
        vrt_options = gdal.BuildVRTOptions(
            xRes=abs(gt[1]) * scale_factor,
            yRes=abs(gt[5]) * scale_factor,
            resampleAlg='bilinear'
        )
        vrt_ds = gdal.BuildVRT('', [dem_path], options=vrt_options)
        src_band = vrt_ds.GetRasterBand(1)
        cell_area_m2 = cell_area_m2 * (scale_factor ** 2)

    report_progress(40, f"Computing Viewshed from observer ({obs_x:.4f}, {obs_y:.4f}) radius {max_d_m:,.0f}m...")

    mode_val = getattr(gdal, "GVM_Diagonal", 2)
    vs_ds = gdal.ViewshedGenerate(
        srcBand=src_band,
        driverName="GTiff",
        targetRasterName=out_path,
        creationOptions=["TILED=YES", "COMPRESS=LZW"],
        observerX=obs_x,
        observerY=obs_y,
        observerHeight=obs_h,
        targetHeight=tgt_h,
        visibleVal=255.0,
        invisibleVal=0.0,
        outOfRangeVal=0.0,
        noDataVal=0.0,
        dfCurvCoeff=curv_coeff,
        mode=mode_val,
        maxDistance=gdal_max_dist
    )
    vs_ds = None
    src_band = None
    vrt_ds = None
    ds = None

    report_progress(80, "Calculating visibility metrics & surface coverage...")

    out_ds = gdal.Open(out_path, gdal.GA_ReadOnly)
    out_band = out_ds.GetRasterBand(1)
    arr = out_band.ReadAsArray()

    visible_count = int(np.count_nonzero(arr == 255))
    radius_area_m2 = np.pi * (max_d_m ** 2)
    visible_area_m2 = visible_count * cell_area_m2
    visible_ha = visible_area_m2 / 10000.0
    visible_km2 = visible_area_m2 / 1000000.0
    radius_km2 = radius_area_m2 / 1000000.0
    coverage_pct = (visible_area_m2 / radius_area_m2 * 100.0) if radius_area_m2 > 0 else 0.0

    out_ds = None

    report_progress(100, "Viewshed analysis complete!")
    report_result(True, {
        "output_path": out_path,
        "observer_x": obs_x,
        "observer_y": obs_y,
        "observer_h": obs_h,
        "target_h": tgt_h,
        "max_distance": max_d_m,
        "visible_cells": visible_count,
        "visible_area_m2": round(visible_area_m2, 2),
        "visible_ha": round(visible_ha, 2),
        "visible_km2": round(visible_km2, 4),
        "total_radius_km2": round(radius_km2, 4),
        "coverage_percentage": round(coverage_pct, 2)
    })

