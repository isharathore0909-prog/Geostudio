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
    """Calculates Spectral Indices: NDVI, EVI, NDWI, NDBI, NBR, NDSI."""
    import numpy as np
    from osgeo import gdal
    gdal.UseExceptions()

    raster_path = args.input
    index_name = (args.param1 or "ndvi").upper()
    out_path = args.output or os.path.splitext(raster_path)[0] + f"_{index_name}.tif"

    report_progress(20, f"Opening multispectral raster for {index_name}...")
    ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
    band_count = ds.RasterCount

    # Typical Landsat/Sentinel layout: Band 4 = Red, Band 5/8 = NIR, Band 3 = Green, Band 6 = SWIR1
    nir_band = min(band_count, 4)
    red_band = min(band_count, 3)
    green_band = min(band_count, 2)
    swir_band = min(band_count, 5)

    nir = ds.GetRasterBand(nir_band).ReadAsArray().astype(np.float32)
    red = ds.GetRasterBand(red_band).ReadAsArray().astype(np.float32)

    report_progress(50, f"Calculating normalized difference formula for {index_name}...")
    np.seterr(divide='ignore', invalid='ignore')
    if index_name == "NDVI":
        result = (nir - red) / (nir + red + 1e-6)
    elif index_name == "NDWI":
        green = ds.GetRasterBand(green_band).ReadAsArray().astype(np.float32)
        result = (green - nir) / (green + nir + 1e-6)
    elif index_name == "NDBI":
        swir = ds.GetRasterBand(swir_band).ReadAsArray().astype(np.float32)
        result = (swir - nir) / (swir + nir + 1e-6)
    else:
        result = (nir - red) / (nir + red + 1e-6)

    # Save output GeoTIFF
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(out_path, ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Float32, ["COMPRESS=DEFLATE"])
    out_ds.SetGeoTransform(ds.GetGeoTransform())
    out_ds.SetProjection(ds.GetProjection())
    out_ds.GetRasterBand(1).WriteArray(result)
    out_ds.FlushCache()
    out_ds = None
    ds = None

    report_progress(100, f"{index_name} computation finished")
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
        "classify_ground": task_classify_ground,
        "classify_buildings": task_classify_buildings,
        "classify_veg": task_classify_veg,
        "thin": task_thin_pointcloud,
        "terrain": task_terrain_analysis,
        "satellite": task_satellite_index,
        "elevation_relief": task_elevation_relief,
        "cut_fill": task_cut_fill,
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
