# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - Hydrology & Watershed Modeling Tasks
Executes Garbrecht & Martz depression filling, D8 flow direction routing,
topological flow accumulation, Strahler stream networks, and catchment basin delineation
using WhiteboxTools / QGIS hydrology algorithms.
"""

import os
import sys
import json
import time
import numpy as np

# Ensure QGIS PROJ definitions take priority over any system or PostgreSQL installations
QGIS_PROJ_DIR = r"C:\Program Files\QGIS 3.40.14\share\proj"
if os.path.exists(QGIS_PROJ_DIR):
    os.environ["PROJ_LIB"] = QGIS_PROJ_DIR
    os.environ["PROJ_DATA"] = QGIS_PROJ_DIR
    try:
        from osgeo import osr
        osr.SetPROJSearchPaths([QGIS_PROJ_DIR])
    except Exception:
        pass
    try:
        import pyproj
        pyproj.datadir.set_data_dir(QGIS_PROJ_DIR)
    except Exception:
        pass

from common import report_progress, report_result

HEX_PALETTE = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4",
    "#ec4899", "#84cc16", "#f97316", "#14b8a6", "#6366f1", "#a855f7",
    "#e11d48", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777",
    "#65a30d", "#ea580c", "#0d9488", "#4f46e5", "#9333ea", "#be123c",
    "#047857", "#b45309", "#6d28d9", "#0e7490", "#be185d", "#4d7c0f",
    "#c2410c", "#0f766e", "#4338ca", "#7e22ce", "#9f1239", "#065f46",
    "#92400e", "#5b21b6", "#155e75", "#9d174d", "#3f6212", "#9a3412",
    "#115e59", "#3730a3", "#6b21a8", "#881337", "#064e3b", "#78350f",
    "#4c1d95", "#164e63", "#831843", "#365314", "#7c2d12", "#134e4a",
    "#312e81", "#581c87", "#701a75", "#0284c7", "#22c55e", "#eab308",
    "#e879f9", "#38bdf8", "#4ade80", "#facc15"
]

STREAM_PALETTE = {
    1: "#60a5fa",
    2: "#3b82f6",
    3: "#2563eb",
    4: "#1d4ed8",
    5: "#1e40af",
    6: "#001a99",
    7: "#000066"
}


def task_watershed(args):
    """
    GeoStudio Hydrological Modeling & Drainage Basin Analysis Engine.
    Executes Garbrecht-Martz depression filling, D8 flow direction,
    topological flow accumulation, Strahler stream networks, and
    solid catchment basin delineation matching QGIS and Global Mapper.
    """
    report_progress(5, "Initializing Hydrological Analysis Engine...")
    from osgeo import gdal
    gdal.UseExceptions()

    dem_path = args.input
    if not dem_path or not os.path.exists(dem_path):
        raise FileNotFoundError(f"Input DEM surface not found: {dem_path}")

    mode = (args.mode or "watershed").lower().replace("hydrology:", "")
    if mode not in ("watershed", "stream_network", "flowdir", "flowaccum", "fillsinks"):
        mode = "watershed"

    threshold = 2000
    if args.param1:
        try:
            threshold = int(float(args.param1))
            if threshold <= 0:
                threshold = 2000
        except Exception:
            threshold = 2000

    auto_fill = True
    smooth_surface = False
    vectorize = True
    output_format = "both"
    min_stream_len = 0.0
    smooth_streams = True
    generate_streams = True

    if args.param2:
        try:
            opts = json.loads(args.param2)
            if isinstance(opts, dict):
                auto_fill = bool(opts.get("auto_fill", True))
                smooth_surface = bool(opts.get("smooth_surface", False))
                vectorize = bool(opts.get("vectorize", True))
                output_format = str(opts.get("format", "both")).lower()
                min_stream_len = float(opts.get("min_stream_len", 0.0))
                smooth_streams = bool(opts.get("smooth_streams", True))
                generate_streams = bool(opts.get("generate_streams", True))
        except Exception:
            pass

    base, ext = os.path.splitext(dem_path)
    out_target = args.output
    if not out_target:
        if mode == "watershed":
            out_target = f"{base}_watershed.geojson" if vectorize else f"{base}_watershed.tif"
        elif mode == "stream_network":
            out_target = f"{base}_streams.tif"
        elif mode == "flowdir":
            out_target = f"{base}_flowdir.tif"
        elif mode == "flowaccum":
            out_target = f"{base}_flowaccum.tif"
        elif mode == "fillsinks":
            out_target = f"{base}_filled.tif"
        else:
            out_target = f"{base}_hydro.tif"

    tif_path = out_target if out_target.lower().endswith(".tif") else f"{base}_{mode}.tif"
    geojson_path = out_target if out_target.lower().endswith(".geojson") else f"{base}_{mode}.geojson"
    streams_path = f"{base}_drainage_network.geojson"

    os.makedirs(os.path.dirname(os.path.abspath(tif_path)), exist_ok=True)

    use_wbw = False
    try:
        import whitebox_workflows as wbw
        use_wbw = True
    except ImportError:
        use_wbw = False

    if use_wbw:
        _execute_whitebox_hydrology(
            dem_path=dem_path,
            tif_path=tif_path,
            geojson_path=geojson_path,
            streams_path=streams_path,
            mode=mode,
            threshold=threshold,
            min_stream_len=min_stream_len,
            smooth_streams=smooth_streams,
            generate_streams=generate_streams,
            vectorize=vectorize,
            output_format=output_format
        )
    else:
        _execute_native_hydrology(
            dem_path=dem_path,
            tif_path=tif_path,
            geojson_path=geojson_path,
            streams_path=streams_path,
            mode=mode,
            threshold=threshold,
            min_stream_len=min_stream_len,
            smooth_streams=smooth_streams,
            generate_streams=generate_streams,
            vectorize=vectorize,
            output_format=output_format,
            auto_fill=auto_fill,
            smooth_surface=smooth_surface
        )


def _execute_whitebox_hydrology(
    dem_path: str,
    tif_path: str,
    geojson_path: str,
    streams_path: str,
    mode: str,
    threshold: int,
    min_stream_len: float,
    smooth_streams: bool,
    generate_streams: bool,
    vectorize: bool,
    output_format: str
):
    import whitebox_workflows as wbw
    from osgeo import gdal, osr, ogr
    from shapely.geometry import Polygon, mapping
    from shapely.ops import unary_union, transform
    from shapely import wkt as shp_wkt
    import pyproj

    report_progress(10, f"Analyzing DEM elevation surface: {os.path.basename(dem_path)}...")

    tmp_dir = os.path.dirname(dem_path)
    pid = os.getpid()
    tmp_dem = os.path.join(tmp_dir, f"_wb_{pid}_dem.tif")
    tmp_fill = os.path.join(tmp_dir, f"_wb_{pid}_fill.tif")
    tmp_pntr = os.path.join(tmp_dir, f"_wb_{pid}_pntr.tif")
    tmp_accum = os.path.join(tmp_dir, f"_wb_{pid}_accum.tif")
    tmp_streams = os.path.join(tmp_dir, f"_wb_{pid}_streams.tif")
    tmp_strahler = os.path.join(tmp_dir, f"_wb_{pid}_strahler.tif")
    tmp_basins = os.path.join(tmp_dir, f"_wb_{pid}_basins.tif")
    raw_streams_geo = os.path.join(tmp_dir, f"_wb_{pid}_raw_streams.geojson")
    raw_basins_geo = os.path.join(tmp_dir, f"_wb_{pid}_raw_basins.geojson")

    temp_files = [tmp_dem, tmp_fill, tmp_pntr, tmp_accum, tmp_streams, tmp_strahler, tmp_basins, raw_streams_geo, raw_basins_geo]

    try:
        ds_dem = gdal.Open(dem_path)
        gt = ds_dem.GetGeoTransform()
        srs_wkt = ds_dem.GetProjection()

        # Step 1: Ensure uncompressed TIFF for Whitebox
        report_progress(15, "Reading DEM terrain surface...")
        gdal.Translate(tmp_dem, ds_dem, creationOptions=["COMPRESS=NONE"])

        # Step 2: Fill Depressions with Garbrecht & Martz Flat Resolution
        report_progress(25, "Resolving depressions & flats (Garbrecht & Martz)...")
        wbw.run_tool("fill_depressions", {
            "dem": tmp_dem,
            "output": tmp_fill,
            "fix_flats": True,
            "flat_resolution": "garbrecht_martz"
        })

        if mode == "fillsinks":
            gdal.Translate(tif_path, tmp_fill, creationOptions=["COMPRESS=LZW", "TILED=YES"])
            report_progress(100, "Depression filling complete.")
            report_result(True, {"output_file": tif_path, "mode": mode})
            return

        # Step 3: D8 Pointer & Flow Accumulation
        report_progress(40, "Calculating D8 flow direction pointer...")
        wbw.run_tool("d8_pointer", {"dem": tmp_fill, "output": tmp_pntr})

        if mode == "flowdir":
            gdal.Translate(tif_path, tmp_pntr, creationOptions=["COMPRESS=LZW", "TILED=YES"])
            report_progress(100, "Flow direction complete.")
            report_result(True, {"output_file": tif_path, "mode": mode})
            return

        report_progress(55, "Calculating topological flow accumulation...")
        wbw.run_tool("d8_flow_accum", {"input": tmp_fill, "output": tmp_accum, "out_type": "cells"})

        if mode == "flowaccum":
            gdal.Translate(tif_path, tmp_accum, creationOptions=["COMPRESS=LZW", "TILED=YES"])
            report_progress(100, "Flow accumulation complete.")
            report_result(True, {"output_file": tif_path, "mode": mode})
            return

        # Step 4: Extract Streams & Hierarchical Strahler Orders
        eff_threshold = float(threshold)
        report_progress(65, f"Extracting stream network (Threshold: {int(eff_threshold)} cells)...")
        wbw.run_tool("extract_streams", {
            "flow_accum": tmp_accum,
            "output": tmp_streams,
            "threshold": eff_threshold
        })

        wbw.run_tool("strahler_stream_order", {
            "d8_pntr": tmp_pntr,
            "streams": tmp_streams,
            "output": tmp_strahler
        })

        # Step 5: Delineate Catchment Basins
        report_progress(75, "Delineating catchment basins...")
        wbw.run_tool("subbasins", {
            "d8_pntr": tmp_pntr,
            "streams": tmp_streams,
            "output": tmp_basins
        })

        # Step 5b: Ensure 100% Zero-Gap Terrain Coverage (allocate unassigned hillslope/edge cells)
        report_progress(78, "Resolving hillslope voids for 100% seamless zero-gap coverage...")
        try:
            from scipy import ndimage
            subb_ds = gdal.Open(tmp_basins, gdal.GA_Update)
            band = subb_ds.GetRasterBand(1)
            subb_arr = band.ReadAsArray()
            nodata_val = band.GetNoDataValue()

            dem_arr = ds_dem.GetRasterBand(1).ReadAsArray()
            dem_nodata = ds_dem.GetRasterBand(1).GetNoDataValue()
            mask_valid = (dem_arr != dem_nodata) & (~np.isnan(dem_arr)) if dem_nodata is not None else (~np.isnan(dem_arr))

            mask_assigned = (subb_arr > 0)
            if nodata_val is not None:
                mask_assigned &= (subb_arr != nodata_val)

            unassigned_valid = ~mask_assigned & mask_valid
            if np.count_nonzero(unassigned_valid) > 0 and np.count_nonzero(mask_assigned) > 0:
                indices = ndimage.distance_transform_edt(~mask_assigned, return_distances=False, return_indices=True)
                filled_subb = subb_arr[tuple(indices)]
                filled_subb[~mask_valid] = 0
                band.WriteArray(filled_subb)
                band.SetNoDataValue(0)
                band.FlushCache()
            subb_ds = None
        except Exception as e:
            print(f"Warning: zero-gap gap fill encountered: {e}", file=sys.stderr)

        # Save raster output if requested
        if output_format in ("raster", "both"):
            gdal.Translate(tif_path, tmp_basins if mode == "watershed" else tmp_strahler, creationOptions=["COMPRESS=LZW", "TILED=YES"])

        # Setup coordinate transformer to WGS84 EPSG:4326 via pyproj
        transformer = None
        try:
            pyproj.datadir.set_data_dir(QGIS_PROJ_DIR)
            if srs_wkt:
                src_srs = osr.SpatialReference(srs_wkt)
                proj_cs = src_srs.GetAuthorityCode(None) or src_srs.GetAttrValue("AUTHORITY", 1)
                crs_input = f"EPSG:{proj_cs}" if proj_cs else srs_wkt
            else:
                crs_input = "EPSG:32643"
            transformer = pyproj.Transformer.from_crs(crs_input, "EPSG:4326", always_xy=True)
        except Exception:
            try:
                pyproj.datadir.set_data_dir(QGIS_PROJ_DIR)
                transformer = pyproj.Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
            except Exception:
                transformer = None

        # Step 6: Vectorize Streams to Lines
        stream_count = 0
        if generate_streams or mode == "stream_network":
            report_progress(82, "Vectorizing dendritic stream network...")
            wbw.run_tool("raster_streams_to_vector", {
                "d8_pntr": tmp_pntr,
                "streams_raster": tmp_strahler,
                "output": raw_streams_geo
            })

            if os.path.exists(raw_streams_geo):
                with open(raw_streams_geo, "r", encoding="utf-8") as f:
                    s_raw = json.load(f)

                s_out_features = []
                for feat in s_raw.get("features", []):
                    geom = feat.get("geometry")
                    if not geom or geom.get("type") != "LineString":
                        continue
                    coords = geom.get("coordinates", [])
                    if len(coords) < 2:
                        continue

                    # Check if coordinates are already in WGS84 degrees or need UTM reprojection
                    p_sample = coords[0]
                    is_already_wgs = abs(p_sample[0]) <= 180.0 and abs(p_sample[1]) <= 90.0

                    # Calculate reach length in meters
                    length_m = 0.0
                    if is_already_wgs:
                        lat_rad = np.radians(p_sample[1])
                        m_lon = 111320.0 * np.cos(lat_rad)
                        m_lat = 110540.0
                        for j in range(1, len(coords)):
                            p0 = coords[j - 1]
                            p1 = coords[j]
                            dx = (p1[0] - p0[0]) * m_lon
                            dy = (p1[1] - p0[1]) * m_lat
                            length_m += float(np.hypot(dx, dy))
                        wgs_coords = [[round(p[0], 7), round(p[1], 7)] for p in coords]
                    else:
                        for j in range(1, len(coords)):
                            p0 = coords[j - 1]
                            p1 = coords[j]
                            length_m += float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))

                        if transformer:
                            try:
                                xs = [p[0] for p in coords]
                                ys = [p[1] for p in coords]
                                txs, tys = transformer.transform(xs, ys)
                                wgs_coords = [[round(txs[k], 7), round(tys[k], 7)] for k in range(len(txs))]
                            except Exception:
                                wgs_coords = coords
                        else:
                            wgs_coords = coords

                    order = int(feat.get("properties", {}).get("STRM_VAL", 1))
                    stroke_color = STREAM_PALETTE.get(order, "#001a99")
                    stroke_width = round(2.2 + min(4.0, (order - 1) * 0.8), 1)

                    s_out_features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": wgs_coords
                        },
                        "properties": {
                            "StreamId": len(s_out_features) + 1,
                            "Order": order,
                            "Length_m": round(length_m, 1),
                            "color": stroke_color,
                            "strokeColor": stroke_color,
                            "strokeWidth": stroke_width
                        }
                    })

                target_stream_file = streams_path if mode == "watershed" else geojson_path
                with open(target_stream_file, "w", encoding="utf-8") as f:
                    json.dump({"type": "FeatureCollection", "features": s_out_features}, f)

                stream_count = len(s_out_features)

        # Step 7: Vectorize Catchment Basins to Solid Polygons via GDAL Polygonize
        num_basins = 0
        total_area_ha = 0.0
        if mode == "watershed" and (vectorize or output_format in ("vector", "both")):
            report_progress(90, "Vectorizing catchment basins into solid polygons...")
            try:
                subb_ds = gdal.Open(tmp_basins)
                band = subb_ds.GetRasterBand(1)

                drv = ogr.GetDriverByName("MEM")
                out_ds = drv.CreateDataSource("mem")
                srs = osr.SpatialReference()
                if srs_wkt:
                    srs.ImportFromWkt(srs_wkt)
                layer = out_ds.CreateLayer("basins", srs, ogr.wkbPolygon)
                fd = ogr.FieldDefn("BasinId", ogr.OFTInteger)
                layer.CreateField(fd)
                gdal.Polygonize(band, None, layer, 0, [], callback=None)

                # Group polygons by BasinId
                by_id = {}
                for f in layer:
                    bid = f.GetField("BasinId")
                    if bid is None or bid <= 0:
                        continue
                    geom = f.GetGeometryRef()
                    if geom and geom.GetArea() >= 0.5:
                        wkt_geom = geom.ExportToWkt()
                        try:
                            sp = shp_wkt.loads(wkt_geom)
                            if not sp.is_empty:
                                if bid not in by_id:
                                    by_id[bid] = []
                                by_id[bid].append(sp)
                        except Exception:
                            pass

                b_out_features = []
                for bid, geoms in by_id.items():
                    try:
                        u = unary_union(geoms) if len(geoms) > 1 else geoms[0]
                        area_m2 = float(u.area)
                        if area_m2 < 0.5:
                            continue

                        perim_m = float(u.length)

                        if transformer:
                            try:
                                u_wgs = transform(transformer.transform, u)
                            except Exception:
                                u_wgs = u
                        else:
                            u_wgs = u

                        b_idx = len(b_out_features)
                        hex_color = HEX_PALETTE[b_idx % len(HEX_PALETTE)]

                        b_out_features.append({
                            "type": "Feature",
                            "geometry": mapping(u_wgs),
                            "properties": {
                                "BasinId": b_idx + 1,
                                "Name": f"Catchment #{b_idx + 1}",
                                "Area_ha": round(area_m2 / 10000.0, 3),
                                "Area_km2": round(area_m2 / 1e6, 4),
                                "Area_m2": round(area_m2, 1),
                                "Perimeter_m": round(perim_m, 1),
                                "color": hex_color,
                                "fillColor": hex_color,
                                "strokeColor": "#0f172a",
                                "strokeWidth": 1.2,
                                "opacity": 1.0,
                                "fillOpacity": 1.0
                            }
                        })
                        total_area_ha += (area_m2 / 10000.0)
                    except Exception as ex:
                        continue

                with open(geojson_path, "w", encoding="utf-8") as f:
                    json.dump({"type": "FeatureCollection", "features": b_out_features}, f)

                num_basins = len(b_out_features)
            except Exception as e:
                print(f"ERROR in catchment basin vectorization: {e}", file=sys.stderr)

        primary_out = geojson_path if (vectorize and output_format != "raster" and os.path.exists(geojson_path)) else tif_path

        report_progress(100, f"Watershed delineation complete: {num_basins} catchments ({total_area_ha:,.1f} ha, {stream_count} streams)")
        report_result(True, {
            "output_file": primary_out,
            "raster_file": tif_path if os.path.exists(tif_path) else None,
            "vector_file": geojson_path if os.path.exists(geojson_path) else None,
            "streams_file": streams_path if (os.path.exists(streams_path) and generate_streams) else None,
            "mode": mode,
            "threshold": threshold,
            "num_basins": num_basins,
            "total_area_ha": round(total_area_ha, 2),
            "feature_count": num_basins
        })

    finally:
        for p in temp_files:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def _execute_native_hydrology(
    dem_path: str,
    tif_path: str,
    geojson_path: str,
    streams_path: str,
    mode: str,
    threshold: int,
    min_stream_len: float,
    smooth_streams: bool,
    generate_streams: bool,
    vectorize: bool,
    output_format: str,
    auto_fill: bool,
    smooth_surface: bool
):
    from core.hydrology.hydrology_engine import HydrologyEngine
    report_progress(10, f"Analyzing DEM elevation surface: {os.path.basename(dem_path)}...")

    def _hydro_prog(pct, msg):
        scaled = int(10 + (pct / 100.0) * 65.0)
        report_progress(min(75, scaled), msg)

    algo_id = f"hydrology:{mode}"
    params = {
        "threshold": threshold,
        "auto_fill_sinks": auto_fill,
        "smooth_surface": smooth_surface,
        "min_stream_len": min_stream_len,
        "smooth_streams": smooth_streams,
        "streams_geojson_path": streams_path if (generate_streams and (mode in ("watershed", "stream_network"))) else None
    }

    success = HydrologyEngine.execute_hydrology_algorithm(
        input_raster_path=dem_path,
        output_raster_path=tif_path,
        algo_id=algo_id,
        params=params,
        progress_callback=_hydro_prog
    )

    if not success or not os.path.exists(tif_path):
        raise RuntimeError("Hydrology analysis computation failed.")

    report_progress(100, "Watershed analysis complete.")
    report_result(True, {
        "output_file": geojson_path if os.path.exists(geojson_path) else tif_path,
        "raster_file": tif_path if os.path.exists(tif_path) else None,
        "vector_file": geojson_path if os.path.exists(geojson_path) else None,
        "streams_file": streams_path if os.path.exists(streams_path) else None,
        "mode": mode,
        "threshold": threshold
    })
