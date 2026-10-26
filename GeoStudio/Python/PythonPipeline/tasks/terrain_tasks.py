# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - Terrain & Earthwork Tasks
Handles contour isoline extraction, slope/aspect/hillshade DEM processing,
3D shaded relief generation, and Cut & Fill volumetric calculations.
"""

import os
import sys

from common import report_progress, report_result


def task_terrain_analysis(args):
    """Computes slope, aspect, hillshade, TRI, TPI, or contours from DEM."""
    from osgeo import gdal, ogr, osr
    gdal.UseExceptions()

    dem_path = args.input
    if not dem_path or not os.path.exists(dem_path):
        raise FileNotFoundError(f"Input DEM raster does not exist: {dem_path}")

    mode = (args.mode or "hillshade").lower()
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

        # Setup standard WGS84 (EPSG:4326) target SRS for web GIS compatibility
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
