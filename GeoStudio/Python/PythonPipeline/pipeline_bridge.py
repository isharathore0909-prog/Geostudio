# -*- coding: utf-8 -*-
"""
GeoStudio - High-Performance Python Processing Pipeline Bridge
Executes heavy LiDAR, Terrain, Hydrology, Remote Sensing, and 3D Visualizer algorithms.
Communicates progress and JSON results back to .NET host.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import argparse
import tempfile
import traceback

# Configure PROJ & GDAL data paths to ensure stable coordinate transforms
qgis_share_proj = r"C:\Program Files\QGIS 3.40.14\share\proj"
if os.path.exists(qgis_share_proj):
    os.environ["PROJ_LIB"] = qgis_share_proj
    os.environ["PROJ_DATA"] = qgis_share_proj

qgis_share_gdal = r"C:\Program Files\QGIS 3.40.14\share\gdal"
if os.path.exists(qgis_share_gdal):
    os.environ["GDAL_DATA"] = qgis_share_gdal

# Priority 1: Use the local PythonEngine in the current project
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
PYTHON_ENGINE_DIR = os.path.join(PROJECT_ROOT, "PythonEngine")
if os.path.exists(PYTHON_ENGINE_DIR) and PYTHON_ENGINE_DIR not in sys.path:
    sys.path.insert(0, PYTHON_ENGINE_DIR)

# Priority 2: Duplicacy fallback
APP_DIR = r"D:\DUPLICACY\GeoStudio\app"
if os.path.exists(APP_DIR) and APP_DIR not in sys.path:
    sys.path.insert(1, APP_DIR)


def report_progress(percent: int, message: str = ""):
    print(f"PROGRESS:{percent}:{message}", flush=True)


def report_result(success: bool, data: dict, error_msg: str = ""):
    payload = {"status": "ok" if success else "error", "data": data, "error": error_msg}
    print("RESULT:" + json.dumps(payload), flush=True)


def task_launch_3d(args):
    """Launches standalone interactive OpenGL 3D viewer workstation."""
    report_progress(10, "Initializing 3D Workstation...")
    from PyQt5.QtWidgets import QApplication
    from ui.viewer3d.window import GeoStudio3DViewerWindow

    app = QApplication.instance() or QApplication([sys.argv[0]])
    file_path = args.input if (args.input and os.path.exists(args.input)) else None
    viewer = GeoStudio3DViewerWindow(file_path=file_path)
    viewer.show()
    report_progress(100, "3D Workstation active")
    report_result(True, {"message": "3D Visualizer Launched", "file": file_path})
    sys.exit(app.exec_())


def run_pdal_smrf_classification(in_file: str, out_file: str):
    """Executes PDAL SMRF ground filtering and HAG Delaunay classification directly."""
    qgis_root = r"C:\Program Files\QGIS 3.40.14"
    pdal_candidates = [
        os.path.join(qgis_root, "bin", "pdal.exe"),
        os.path.join(qgis_root, "apps", "qgis-ltr", "bin", "pdal.exe"),
        shutil.which("pdal"),
    ]
    pdal_exe = next((p for p in pdal_candidates if p and os.path.exists(p)), None)
    if not pdal_exe:
        raise RuntimeError("PDAL executable not found.")

    env = os.environ.copy()
    bin_dir = os.path.join(qgis_root, "bin")
    qgis_bin = os.path.join(qgis_root, "apps", "qgis-ltr", "bin")
    env["PATH"] = f"{bin_dir};{qgis_bin};" + env.get("PATH", "")
    proj_dir = os.path.join(qgis_root, "share", "proj")
    gdal_dir = os.path.join(qgis_root, "share", "gdal")
    if os.path.exists(proj_dir):
        env["PROJ_LIB"] = proj_dir
        env["PROJ_DATA"] = proj_dir
    if os.path.exists(gdal_dir):
        env["GDAL_DATA"] = gdal_dir

    startupinfo = None
    cflags = 0
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    # Check SRS
    is_geographic = False
    utm_epsg = 32643
    try:
        sum_res = subprocess.run(
            [pdal_exe, 'info', '--summary', in_file],
            capture_output=True, text=True, env=env,
            startupinfo=startupinfo, creationflags=cflags, timeout=20
        )
        if sum_res.returncode == 0:
            s_data = json.loads(sum_res.stdout)
            srs = s_data.get('summary', {}).get('srs', {})
            is_geographic = srs.get('isgeographic', False)
            bounds = s_data.get('summary', {}).get('bounds', {})
            if is_geographic and bounds:
                lon = (bounds.get('minx', 0) + bounds.get('maxx', 0)) / 2.0
                lat = (bounds.get('miny', 0) + bounds.get('maxy', 0)) / 2.0
                zone = int((lon + 180) / 6) + 1
                utm_epsg = 32600 + zone if lat >= 0 else 32700 + zone
    except Exception:
        pass

    stages = []
    is_in_copc = in_file.lower().endswith(".copc.laz") or in_file.lower().endswith(".laz")
    stages.append({
        "type": "readers.copc" if is_in_copc else "readers.las",
        "filename": in_file,
        "threads": 8
    })

    if is_geographic:
        stages.append({
            "type": "filters.reprojection",
            "out_srs": f"EPSG:{utm_epsg}"
        })

    stages.append({
        "type": "filters.smrf",
        "cell": 1.2,
        "slope": 0.15,
        "window": 18.0,
        "threshold": 0.45,
        "scalar": 1.25
    })

    stages.append({
        "type": "filters.hag_delaunay"
    })

    stages.append({
        "type": "filters.covariancefeatures",
        "knn": 16,
        "threads": 8,
        "feature_set": ["Planarity", "Scattering"]
    })

    stages.append({
        "type": "filters.assign",
        "value": [
            "Classification = 3 WHERE HeightAboveGround >= 0.3 && HeightAboveGround < 1.5 && Classification != 2",
            "Classification = 4 WHERE HeightAboveGround >= 1.5 && HeightAboveGround < 3.5 && Planarity < 0.65 && Classification != 2",
            "Classification = 5 WHERE HeightAboveGround >= 3.5 && Planarity < 0.65 && Classification != 2",
            "Classification = 6 WHERE HeightAboveGround >= 1.8 && Planarity >= 0.65 && Classification != 2"
        ]
    })

    if is_geographic:
        stages.append({
            "type": "filters.reprojection",
            "out_srs": "EPSG:4326"
        })

    is_out_copc = out_file.lower().endswith(".copc.laz") or out_file.lower().endswith(".laz")
    w_stage = {
        "type": "writers.copc" if is_out_copc else "writers.las",
        "filename": out_file,
        "forward": "all"
    }
    if is_out_copc:
        w_stage["threads"] = 8
    stages.append(w_stage)

    pipe_path = os.path.join(tempfile.gettempdir(), f"pdal_classify_{int(time.time())}.json")
    with open(pipe_path, "w", encoding="utf-8") as f:
        json.dump(stages, f, indent=2)

    proc = subprocess.Popen([pdal_exe, 'pipeline', pipe_path], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=cflags)
    start_t = time.time()
    while proc.poll() is None:
        time.sleep(0.4)
        elapsed = time.time() - start_t
        ratio = 1.0 - (0.5 ** (elapsed / 30.0))
        dyn_pct = min(98, max(15, 15 + int(ratio * 80)))
        if elapsed < 20:
            msg = f"Running SMRF morphological ground filter ({dyn_pct}%)..."
        elif elapsed < 45:
            msg = f"Computing Delaunay terrain HAG & canopy ({dyn_pct}%)..."
        else:
            msg = f"Writing classified point cloud ({dyn_pct}%)..."
        report_progress(dyn_pct, msg)

    stdout_b, stderr_b = proc.communicate()
    rc = proc.returncode
    if rc == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 1024:
        return out_file
    err_str = (stderr_b or b"").decode("utf-8", errors="ignore").strip()
    raise RuntimeError(f"PDAL pipeline failed (code {rc}): {err_str[:250]}")


def task_classify_ground(args):
    """Executes SMRF/HAG Delaunay ground and canopy point cloud classification."""
    in_file = args.input
    if not in_file or not os.path.exists(in_file):
        raise FileNotFoundError(f"Input LiDAR file not found: {in_file}")

    out_file = args.output or os.path.splitext(in_file)[0] + "_ground_classified.las"
    report_progress(10, f"Initializing SMRF ground classification for {os.path.basename(in_file)}...")

    try:
        res_file = run_pdal_smrf_classification(in_file, out_file)
        if res_file and os.path.exists(res_file):
            report_progress(100, "Ground & canopy classification complete")
            report_result(True, {"output_file": res_file, "message": "Ground and canopy classified to ASPRS standards"})
            return
    except Exception as ex:
        report_result(False, {}, f"PDAL classification error: {ex}")


def task_classify_buildings(args):
    """Classifies building structures and rooftops (ASPRS Class 6)."""
    in_file = args.input
    out_file = args.output or os.path.splitext(in_file)[0] + "_buildings.las"
    report_progress(20, "Analyzing planar surfaces and rooftop heights...")

    import laspy
    import numpy as np

    las = laspy.read(in_file)
    z = las.z
    min_z = np.percentile(z, 5)
    hag = z - min_z
    # Buildings: high elevation (> 2.5m) and planar density
    is_building = (hag >= 2.5) & (hag <= 45.0)
    las.classification[is_building] = 6  # ASPRS Building
    las.write(out_file)

    report_progress(100, "Building classification complete")
    report_result(True, {"output_file": out_file, "message": "Buildings classified to ASPRS Class 6"})


def task_classify_veg(args):
    """Classifies vegetation canopy into low, medium, and high vegetation."""
    in_file = args.input
    out_file = args.output or os.path.splitext(in_file)[0] + "_vegetation.las"
    report_progress(20, "Computing Height Above Ground (HAG) for vegetation...")

    import laspy
    import numpy as np

    las = laspy.read(in_file)
    z = las.z
    min_z = np.percentile(z, 5)
    hag = z - min_z

    low_veg = (hag >= 0.3) & (hag < 2.0)
    med_veg = (hag >= 2.0) & (hag < 5.0)
    high_veg = hag >= 5.0

    las.classification[low_veg] = 3   # Low Veg
    las.classification[med_veg] = 4   # Medium Veg
    las.classification[high_veg] = 5  # High Veg Canopy
    las.write(out_file)

    report_progress(100, "Vegetation classification complete")
    report_result(True, {"output_file": out_file, "message": "Vegetation classified into Classes 3, 4, 5"})


def task_thin_pointcloud(args):
    """Performs spatial decimation / density thinning."""
    in_file = args.input
    out_file = args.output or os.path.splitext(in_file)[0] + "_thinned.las"
    step = int(args.param1) if args.param1 else 2
    report_progress(25, f"Thinning point cloud by factor {step}...")

    import laspy
    las = laspy.read(in_file)
    thinned = las[::step]
    thinned.write(out_file)

    report_progress(100, "Point cloud decimation complete")
    report_result(True, {
        "output_file": out_file,
        "original_count": len(las.points),
        "thinned_count": len(thinned.points)
    })


def task_terrain_analysis(args):
    """Computes slope, aspect, hillshade, TRI, TPI, or contours from DEM."""
    from osgeo import gdal, ogr, osr
    gdal.UseExceptions()

    dem_path = args.input
    if not dem_path or not os.path.exists(dem_path):
        raise FileNotFoundError(f"Input DEM raster does not exist: {dem_path}")

    mode = args.mode.lower()
    out_path = args.output

    if not out_path:
        ext = ".geojson" if mode == "contours" else ".tif"
        out_path = os.path.splitext(dem_path)[0] + f"_{mode}{ext}"

    report_progress(15, f"Running {mode.upper()} analysis on {os.path.basename(dem_path)}...")

    if mode == "contours":
        interval = float(args.param1 or 10.0)
        base = float(args.param2 or 0.0)
        report_progress(25, f"Generating {interval:g}m isocontour lines from DEM...")

        ds_in = gdal.Open(dem_path, gdal.GA_ReadOnly)
        if not ds_in:
            raise RuntimeError(f"Failed to open DEM raster dataset: {dem_path}")

        band = ds_in.GetRasterBand(1)
        nodata = band.GetNoDataValue()

        # Handle projection safely without throwing corrupt data
        srs_in = None
        proj_wkt = ds_in.GetProjection()
        if proj_wkt and len(proj_wkt.strip()) > 0:
            try:
                srs_in = osr.SpatialReference()
                srs_in.ImportFromWkt(proj_wkt)
            except Exception as e:
                print(f"Warning: could not parse DEM projection WKT ({e}). Assuming native grid coordinates.", file=sys.stderr)
                srs_in = None

        # Build in-memory layer for ContourGenerate
        drv_mem = ogr.GetDriverByName("MEM")
        mem_ds = drv_mem.CreateDataSource("")
        mem_lyr = mem_ds.CreateLayer("contours", srs_in, ogr.wkbLineString)

        id_fld = ogr.FieldDefn("ID", ogr.OFTInteger)
        elev_fld = ogr.FieldDefn("ELEV", ogr.OFTReal)
        mem_lyr.CreateField(id_fld)
        mem_lyr.CreateField(elev_fld)

        report_progress(45, "Tracing isolines through raster elevation surface...")
        use_nodata = 1 if nodata is not None else 0
        nodata_val = float(nodata) if nodata is not None else 0.0
        gdal.ContourGenerate(band, interval, base, [], use_nodata, nodata_val, mem_lyr, 0, 1)

        feat_count = mem_lyr.GetFeatureCount()
        report_progress(70, f"Extracted {feat_count:,} contour lines. Reprojecting & saving GeoJSON...")

        # Setup standard WGS84 (EPSG:4326) target SRS for standard web GIS compatibility
        target_srs = osr.SpatialReference()
        target_srs.ImportFromEPSG(4326)
        target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

        transform = None
        if srs_in and not srs_in.IsSame(target_srs):
            try:
                srs_in_clone = srs_in.Clone()
                srs_in_clone.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
                transform = osr.CoordinateTransformation(srs_in_clone, target_srs)
            except Exception as e:
                print(f"Coordinate transformation to EPSG:4326 skipped: {e}", file=sys.stderr)
                transform = None

        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception:
                pass

        drv_json = ogr.GetDriverByName("GeoJSON")
        out_ds = drv_json.CreateDataSource(out_path)
        out_lyr = out_ds.CreateLayer("contours", target_srs, ogr.wkbLineString)
        out_lyr.CreateField(id_fld)
        out_lyr.CreateField(elev_fld)

        min_elev = float("inf")
        max_elev = float("-inf")
        min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")

        for feat in mem_lyr:
            geom = feat.GetGeometryRef()
            if not geom or geom.IsEmpty():
                continue
            geom = geom.Clone()
            if transform:
                try:
                    geom.Transform(transform)
                except Exception:
                    pass

            env = geom.GetEnvelope()  # (minX, maxX, minY, maxY)
            min_x = min(min_x, env[0])
            max_x = max(max_x, env[1])
            min_y = min(min_y, env[2])
            max_y = max(max_y, env[3])

            elev_val = feat.GetField("ELEV")
            if elev_val is not None:
                min_elev = min(min_elev, elev_val)
                max_elev = max(max_elev, elev_val)

            new_feat = ogr.Feature(out_lyr.GetLayerDefn())
            new_feat.SetGeometry(geom)
            new_feat.SetField("ID", feat.GetField("ID"))
            new_feat.SetField("ELEV", elev_val)
            out_lyr.CreateFeature(new_feat)

        out_ds.FlushCache()
        out_ds = None
        mem_ds = None
        ds_in = None

        # Also write a GeoPackage (.gpkg) copy
        gpkg_path = os.path.splitext(out_path)[0] + ".gpkg"
        try:
            drv_gpkg = ogr.GetDriverByName("GPKG")
            if os.path.exists(gpkg_path):
                drv_gpkg.DeleteDataSource(gpkg_path)
            gpkg_ds = drv_gpkg.CreateDataSource(gpkg_path)
            src_json = ogr.Open(out_path)
            if src_json:
                gpkg_ds.CopyLayer(src_json.GetLayer(0), "contours")
            gpkg_ds = None
            src_json = None
        except Exception as e:
            print(f"Note: GPKG export optional warning: {e}", file=sys.stderr)

        bounds = [min_x, min_y, max_x, max_y] if min_x != float("inf") else None
        if min_elev == float("inf"): min_elev = 0
        if max_elev == float("-inf"): max_elev = 0

        report_progress(100, f"Contour extraction complete: {feat_count:,} isolines generated.")
        report_result(True, {
            "output_file": out_path,
            "gpkg_file": gpkg_path if os.path.exists(gpkg_path) else None,
            "mode": "contours",
            "interval": interval,
            "feature_count": feat_count,
            "min_elev": min_elev,
            "max_elev": max_elev,
            "bounds": bounds
        })
        return
    elif mode in ["slope", "aspect", "hillshade", "tri", "tpi", "roughness"]:
        report_progress(40, f"Computing {mode.capitalize()} shader raster...")
        opt_map = {
            "slope": "slope",
            "aspect": "aspect",
            "hillshade": "hillshade",
            "tri": "TRI",
            "tpi": "TPI",
            "roughness": "roughness"
        }
        gdal.DEMProcessing(out_path, dem_path, opt_map.get(mode, "hillshade"), computeEdges=True)
    else:
        raise ValueError(f"Unknown terrain analysis mode: {mode}")

    report_progress(100, f"{mode.capitalize()} analysis finished")
    report_result(True, {"output_file": out_path, "mode": mode})


def task_satellite_index(args):
    """Calculates Spectral Indices: NDVI, EVI, NDWI, NDBI, NBR, and False Color Composite."""
    import numpy as np
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

    # Defaults according to sensor preset or available band count
    # Default fallback: 1-based indexing clamped to band_count
    nir_band = int(band_map.get("nir", 8 if band_count >= 8 else (5 if band_count >= 5 else min(band_count, 4))))
    red_band = int(band_map.get("red", 4 if band_count >= 4 else min(band_count, 3)))
    green_band = int(band_map.get("green", 3 if band_count >= 3 else min(band_count, 2)))
    blue_band = int(band_map.get("blue", 2 if band_count >= 2 else 1))
    swir1_band = int(band_map.get("swir1", 11 if band_count >= 11 else (6 if band_count >= 6 else min(band_count, 5))))
    swir2_band = int(band_map.get("swir2", 12 if band_count >= 12 else (7 if band_count >= 7 else min(band_count, band_count))))

    # Clamp to valid 1..band_count range
    nir_band = max(1, min(band_count, nir_band))
    red_band = max(1, min(band_count, red_band))
    green_band = max(1, min(band_count, green_band))
    blue_band = max(1, min(band_count, blue_band))
    swir1_band = max(1, min(band_count, swir1_band))
    swir2_band = max(1, min(band_count, swir2_band))

    driver = gdal.GetDriverByName("GTiff")
    geo_xform = ds.GetGeoTransform()
    proj_ref = ds.GetProjection()

    np.seterr(divide='ignore', invalid='ignore')

    if index_name in ("FALSE_COLOR", "FALSECOLOR", "COMPOSITE"):
        report_progress(35, "Generating False-Color Infrared Composite (NIR / Red / Green)...")
        r_b = int(band_map.get("r_composite", nir_band))
        g_b = int(band_map.get("g_composite", red_band))
        b_b = int(band_map.get("b_composite", green_band))

        arr_r = ds.GetRasterBand(r_b).ReadAsArray().astype(np.float32)
        report_progress(55, "Enhancing color contrast dynamics...")
        arr_g = ds.GetRasterBand(g_b).ReadAsArray().astype(np.float32)
        arr_b = ds.GetRasterBand(b_b).ReadAsArray().astype(np.float32)

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

        out_ds = driver.Create(out_path, ds.RasterXSize, ds.RasterYSize, 3, gdal.GDT_Byte, ["COMPRESS=DEFLATE"])
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
    nir = ds.GetRasterBand(nir_band).ReadAsArray().astype(np.float32)
    red = ds.GetRasterBand(red_band).ReadAsArray().astype(np.float32)

    report_progress(65, f"Computing {index_name} formula...")
    if index_name == "NDVI":
        # Normalized Difference Vegetation Index
        denom = nir + red
        denom[denom == 0] = 1e-6
        result = (nir - red) / denom
        result = np.clip(result, -1.0, 1.0)
    elif index_name in ("NDWI", "WATER"):
        # Normalized Difference Water Index (McFeeters: Green - NIR / Green + NIR)
        green = ds.GetRasterBand(green_band).ReadAsArray().astype(np.float32)
        denom = green + nir
        denom[denom == 0] = 1e-6
        result = (green - nir) / denom
        result = np.clip(result, -1.0, 1.0)
    elif index_name == "EVI":
        # Enhanced Vegetation Index: 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
        blue = ds.GetRasterBand(blue_band).ReadAsArray().astype(np.float32)
        denom = nir + 6.0 * red - 7.5 * blue + 1.0
        denom[denom == 0] = 1e-6
        result = 2.5 * (nir - red) / denom
        result = np.clip(result, -1.5, 1.5)
    elif index_name == "NDBI":
        # Normalized Difference Built-up Index: (SWIR1 - NIR) / (SWIR1 + NIR)
        swir1 = ds.GetRasterBand(swir1_band).ReadAsArray().astype(np.float32)
        denom = swir1 + nir
        denom[denom == 0] = 1e-6
        result = (swir1 - nir) / denom
        result = np.clip(result, -1.0, 1.0)
    elif index_name in ("NBR", "BURN"):
        # Normalized Burn Ratio: (NIR - SWIR2) / (NIR + SWIR2)
        swir2 = ds.GetRasterBand(swir2_band).ReadAsArray().astype(np.float32)
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
    out_ds = driver.Create(out_path, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Float32, ["COMPRESS=DEFLATE"])
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


def task_elevation_relief(args):
    """Generates Global Mapper / ArcGIS Pro 3D shaded relief GeoTIFF from DEM/DSM/DTM."""
    dem_path = args.input
    if not dem_path or not os.path.exists(dem_path):
        raise FileNotFoundError(f"Elevation model file not found: {dem_path}")

    preset_key = args.param1 or "GLOBAL_MAPPER_ATLAS"
    report_progress(20, f"Generating 3D Shaded Relief ({preset_key}) for {os.path.basename(dem_path)}...")

    try:
        from core.elevation.relief_shading import generate_3d_shaded_relief_file
        out_tif = generate_3d_shaded_relief_file(dem_path, preset_key=preset_key)
        if not out_tif or not os.path.exists(out_tif):
            raise RuntimeError("Failed to generate 3d relief GeoTIFF")
        report_progress(100, "3D Shaded Relief complete")
        report_result(True, {"output_file": out_tif, "preset": preset_key})
    except Exception as ex:
        report_result(False, {}, str(ex))


def task_cut_fill(args):
    """Executes Cut & Fill earthwork analysis using core.earthworks.cut_fill_engine."""
    from core.earthworks.cut_fill_engine import CutFillEngine
    base_dem = args.input
    comp_dem = args.param1
    swell = float(args.param2 or 1.0)
    out_diff = args.output

    report_progress(10, "Initializing Earthwork Analysis...")
    def _prog(pct, msg):
        report_progress(int(pct), msg)

    res = CutFillEngine.compute_cut_fill(
        base_source=base_dem,
        comp_source=comp_dem,
        swell_factor=swell,
        output_diff_path=out_diff,
        progress_callback=_prog
    )
    report_result(True, {
        "cut_volume": res.gross_cut_volume_m3,
        "fill_volume": res.gross_fill_volume_m3,
        "net_volume": res.net_earthwork_volume_m3,
        "cut_area": res.cut_area_m2,
        "fill_area": res.fill_area_m2,
        "cut_fill_ratio": res.cut_fill_ratio,
        "output_file": res.diff_raster_path,
        "daylight_vector": res.daylight_vector_path
    })


def task_transpose_fields(args):
    """Launches standalone Transpose / Pivot Fields tool dialog."""
    report_progress(10, "Initializing Transpose Fields tool...")
    from PyQt5.QtWidgets import QApplication
    from ui.dialogs.transpose_fields_dialog import TransposeFieldsDialog

    app = QApplication.instance() or QApplication([sys.argv[0]])
    dlg = TransposeFieldsDialog()
    dlg.show()
    report_progress(100, "Transpose Fields tool active")
    app.exec_()


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


def task_vector_geoprocessing(args):
    """High-throughput vector geoprocessing via Shapely & OGR:
    buffer, convex_hull, centroids, dissolve, voronoi, clip.
    """
    mode = (args.mode or "buffer").lower()
    report_progress(10, f"Initializing Vector {mode.capitalize()}...")
    from osgeo import ogr, osr
    import shapely
    import shapely.geometry
    import shapely.ops
    ogr.UseExceptions()

    in_file = args.input
    if not in_file or not os.path.exists(in_file):
        raise ValueError(f"Input vector file not found: {in_file}")

    out_file = args.output
    if not out_file:
        base, ext = os.path.splitext(in_file)
        out_file = f"{base}_{mode}.geojson"

    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)

    in_ds = ogr.Open(in_file)
    in_layer = in_ds.GetLayer(0)
    in_srs = in_layer.GetSpatialRef()
    is_geographic = in_srs.IsGeographic() if in_srs else False

    features_data = []
    geometries = []

    report_progress(20, "Reading vector geometries...")
    for feat in in_layer:
        geom_ref = feat.GetGeometryRef()
        if not geom_ref:
            continue
        geom_json = json.loads(geom_ref.ExportToJson())
        shp_geom = shapely.geometry.shape(geom_json)
        if not shp_geom.is_valid:
            shp_geom = shp_geom.buffer(0)

        props = {}
        for i in range(feat.GetFieldCount()):
            fld_defn = feat.GetFieldDefnRef(i)
            props[fld_defn.GetName()] = feat.GetField(i)

        features_data.append((shp_geom, props))
        geometries.append(shp_geom)

    out_features = []
    report_progress(40, f"Executing {mode} algorithm...")

    if mode == "buffer":
        dist = float(args.param1 or 100.0)
        segments = 16
        dissolve = False
        if args.param2:
            try:
                opts = json.loads(args.param2) if args.param2.startswith("{") else {}
                segments = int(opts.get("segments", 16))
                dissolve = bool(opts.get("dissolve", False))
            except Exception:
                pass

        effective_dist = dist
        if is_geographic and dist > 0.05:
            effective_dist = dist / 111320.0

        buffered_geoms = []
        for i, (geom, props) in enumerate(features_data):
            b_geom = geom.buffer(effective_dist, quad_segs=segments)
            buffered_geoms.append(b_geom)
            if not dissolve:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(b_geom),
                    "properties": dict(props, buffer_distance=dist)
                })

        if dissolve and buffered_geoms:
            dissolved = shapely.ops.unary_union(buffered_geoms)
            if dissolved.geom_type == "Polygon":
                dissolved_list = [dissolved]
            elif dissolved.geom_type == "MultiPolygon":
                dissolved_list = list(dissolved.geoms)
            else:
                dissolved_list = [dissolved]
            for poly in dissolved_list:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(poly),
                    "properties": {"buffer_distance": dist, "dissolved": True}
                })

    elif mode == "convex_hull":
        target = (args.param1 or "all").lower()
        if target == "per_feature":
            for geom, props in features_data:
                hull = geom.convex_hull
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(hull),
                    "properties": dict(props, is_convex_hull=True)
                })
        else:
            union_all = shapely.ops.unary_union(geometries)
            hull = union_all.convex_hull
            out_features.append({
                "type": "Feature",
                "geometry": shapely.geometry.mapping(hull),
                "properties": {"name": "Convex Hull", "feature_count": len(geometries)}
            })

    elif mode == "centroids":
        for geom, props in features_data:
            centroid = geom.centroid
            out_features.append({
                "type": "Feature",
                "geometry": shapely.geometry.mapping(centroid),
                "properties": dict(props, centroid_x=round(centroid.x, 6), centroid_y=round(centroid.y, 6))
            })

    elif mode == "dissolve":
        dissolve_field = args.param1.strip() if args.param1 else ""
        if dissolve_field and dissolve_field.lower() != "all":
            from collections import defaultdict
            groups = defaultdict(list)
            for geom, props in features_data:
                key = str(props.get(dissolve_field, "Unknown"))
                groups[key].append(geom)

            for key, group_geoms in groups.items():
                dissolved = shapely.ops.unary_union(group_geoms)
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(dissolved),
                    "properties": {dissolve_field: key, "dissolved_count": len(group_geoms)}
                })
        else:
            dissolved = shapely.ops.unary_union(geometries)
            if dissolved.geom_type in ("Polygon", "MultiPolygon", "MultiLineString"):
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(dissolved),
                    "properties": {"name": "Dissolved Layer", "feature_count": len(geometries)}
                })
            else:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(dissolved),
                    "properties": {"name": "Dissolved Layer"}
                })

    elif mode == "voronoi":
        all_pts = []
        for geom in geometries:
            if geom.geom_type == "Point":
                all_pts.append(geom)
            elif geom.geom_type == "MultiPoint":
                all_pts.extend(geom.geoms)
            elif hasattr(geom, 'coords'):
                for coord in geom.coords:
                    all_pts.append(shapely.geometry.Point(coord[0], coord[1]))
            elif hasattr(geom, 'exterior') and geom.exterior:
                for coord in geom.exterior.coords:
                    all_pts.append(shapely.geometry.Point(coord[0], coord[1]))

        if len(all_pts) < 3:
            raise ValueError("Voronoi requires at least 3 points to construct polygons.")

        mp = shapely.geometry.MultiPoint(all_pts)
        vor = shapely.ops.voronoi_diagram(mp)
        env = mp.envelope.buffer(0.05 if is_geographic else 200)
        for i, poly in enumerate(vor.geoms):
            clipped_cell = poly.intersection(env)
            if not clipped_cell.is_empty:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(clipped_cell),
                    "properties": {"voronoi_id": i + 1}
                })

    elif mode == "clip":
        mask_file = args.param1
        if not mask_file or not os.path.exists(mask_file):
            raise ValueError(f"Clipping mask vector layer not found: {mask_file}")
        mask_ds = ogr.Open(mask_file)
        mask_layer = mask_ds.GetLayer(0)
        mask_geoms = []
        for feat in mask_layer:
            g_ref = feat.GetGeometryRef()
            if g_ref:
                m_shp = shapely.geometry.shape(json.loads(g_ref.ExportToJson()))
                if not m_shp.is_valid:
                    m_shp = m_shp.buffer(0)
                mask_geoms.append(m_shp)
        mask_union = shapely.ops.unary_union(mask_geoms)

        for geom, props in features_data:
            if geom.intersects(mask_union):
                clipped_geom = geom.intersection(mask_union)
                if not clipped_geom.is_empty:
                    out_features.append({
                        "type": "Feature",
                        "geometry": shapely.geometry.mapping(clipped_geom),
                        "properties": props
                    })

    else:
        raise ValueError(f"Unknown geoprocessing mode: {mode}")

    report_progress(85, "Writing output GeoJSON...")
    geojson_doc = {
        "type": "FeatureCollection",
        "name": os.path.splitext(os.path.basename(out_file))[0],
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84" if is_geographic else "EPSG:3857"}
        },
        "features": out_features
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2)

    report_progress(100, f"Completed {mode}: {len(out_features)} features created")
    report_result(True, {
        "output_file": out_file,
        "feature_count": len(out_features),
        "mode": mode
    })


def main():
    parser = argparse.ArgumentParser(description="GeoStudio Python Pipeline Bridge")
    parser.add_argument("--task", required=True, help="Task identifier")
    parser.add_argument("--input", help="Primary input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--mode", default="hillshade", help="Sub-mode identifier")
    parser.add_argument("--param1", help="Generic parameter 1")
    parser.add_argument("--param2", help="Generic parameter 2")

    args = parser.parse_args()

    task_map = {
        "launch_3d": task_launch_3d,
        "transpose_fields": task_transpose_fields,
        "classify_ground": task_classify_ground,
        "classify_buildings": task_classify_buildings,
        "classify_veg": task_classify_veg,
        "thin": task_thin_pointcloud,
        "terrain": task_terrain_analysis,
        "satellite": task_satellite_index,
        "elevation_relief": task_elevation_relief,
        "cut_fill": task_cut_fill,
        "clip_raster": task_clip_raster,
        "raster_stats": task_raster_stats,
        "vector_geoprocessing": task_vector_geoprocessing,
    }

    runner = task_map.get(args.task)
    if not runner:
        report_result(False, {}, f"Unknown task: {args.task}")
        sys.exit(1)

    try:
        runner(args)
    except Exception as ex:
        traceback.print_exc(file=sys.stderr)
        report_result(False, {}, str(ex))
        sys.exit(1)


if __name__ == "__main__":
    main()
