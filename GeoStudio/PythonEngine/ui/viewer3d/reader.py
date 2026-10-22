# -*- coding: utf-8 -*-
"""
GeoStudio - 3D Point Cloud & DEM Reader
Ultra-fast reader to extract 3D points from LAS/LAZ point clouds and DEMs into numpy arrays.
"""

import os
import math
import numpy as np

from .colormaps import (
    apply_turbo_colormap, apply_viridis_colormap, apply_spectral_colormap,
    apply_plasma_colormap, apply_rdylgn_colormap, apply_blues_colormap,
    apply_ylorrd_colormap, apply_categorical_colormap,
    apply_return_number_colormap, apply_las_classification
)
from .las_reader import load_las_points_data


class PointCloudReader:
    """Ultra-fast reader to extract 3D points from LAS/LAZ point clouds and DEMs."""

    # Re-export colormap methods for backward compatibility
    apply_turbo_colormap = staticmethod(apply_turbo_colormap)
    apply_viridis_colormap = staticmethod(apply_viridis_colormap)
    apply_spectral_colormap = staticmethod(apply_spectral_colormap)
    apply_plasma_colormap = staticmethod(apply_plasma_colormap)
    apply_rdylgn_colormap = staticmethod(apply_rdylgn_colormap)
    apply_blues_colormap = staticmethod(apply_blues_colormap)
    apply_ylorrd_colormap = staticmethod(apply_ylorrd_colormap)
    apply_categorical_colormap = staticmethod(apply_categorical_colormap)
    apply_return_number_colormap = staticmethod(apply_return_number_colormap)
    apply_las_classification = staticmethod(apply_las_classification)

    @staticmethod
    def load_dem_points(file_path: str, max_points: int = 8000000):
        """
        Extracts high-resolution 3D terrain mesh points directly from any DEM/DSM/DTM GeoTIFF raster,
        or handles multi-band 3D relief / RGB rasters seamlessly with true elevation and color draping.
        """
        from osgeo import gdal
        ds = gdal.Open(file_path, gdal.GA_ReadOnly)
        if not ds:
            raise ValueError(f"Could not open raster file: {file_path}")

        raster_count = ds.RasterCount
        first_band = ds.GetRasterBand(1)
        data_type = first_band.DataType

        # Check if this is an RGB/RGBA textured relief or orthophoto raster (e.g. 3 or 4 bands of Byte data)
        is_rgb_or_relief = (raster_count >= 3 and data_type == gdal.GDT_Byte) or ("_3d_relief.tif" in file_path.lower())

        # 1. Resolve raw DEM source if this is a shaded relief or RGB textured raster
        raw_dem_path = None
        if is_rgb_or_relief:
            # Check embedded metadata in the GeoTIFF
            meta_raw = ds.GetMetadataItem("RAW_DEM_SOURCE")
            if meta_raw and os.path.exists(meta_raw):
                raw_dem_path = meta_raw

            # Check active QGIS project layers
            if not raw_dem_path:
                try:
                    from qgis.core import QgsProject
                    for lyr in QgsProject.instance().mapLayers().values():
                        p = lyr.customProperty("raw_dem_source") or getattr(lyr, "_raw_dem_source", None)
                        if p and os.path.exists(p):
                            if os.path.normpath(lyr.source()) == os.path.normpath(file_path) or os.path.basename(file_path).startswith(os.path.splitext(os.path.basename(p))[0]):
                                raw_dem_path = p
                                break
                    if not raw_dem_path:
                        base_stem = os.path.basename(file_path).split("_3d_relief")[0].split("_GLOBAL_MAPPER")[0].split("_MAGMA")[0].split("_VIRIDIS")[0]
                        for lyr in QgsProject.instance().mapLayers().values():
                            if lyr.source() and os.path.exists(lyr.source()) and lyr.source() != file_path:
                                if base_stem and base_stem.lower() in os.path.basename(lyr.source()).lower():
                                    raw_dem_path = lyr.source()
                                    break
                except Exception:
                    pass

            # Check if there is an unshaded file in the same directory or parent directory
            if not raw_dem_path:
                stem = os.path.splitext(file_path)[0]
                for sfx in ["_3d_relief", "_relief", "_hillshade"]:
                    if sfx in stem:
                        cand = stem.split(sfx)[0] + ".tif"
                        if os.path.exists(cand):
                            raw_dem_path = cand
                            break

        # 2. Determine elevation dataset vs color dataset
        dem_ds = ds
        dem_owns_ds = False
        if raw_dem_path and os.path.exists(raw_dem_path):
            raw_dem_ds = gdal.Open(raw_dem_path, gdal.GA_ReadOnly)
            if raw_dem_ds:
                dem_ds = raw_dem_ds
                dem_owns_ds = True

        elev_band = dem_ds.GetRasterBand(1)
        nodata = elev_band.GetNoDataValue()
        w = dem_ds.RasterXSize
        h = dem_ds.RasterYSize
        gt = dem_ds.GetGeoTransform(can_return_null=True) if hasattr(dem_ds, "GetGeoTransform") else dem_ds.GetGeoTransform()
        if gt is None:
            gt = (0.0, 1.0, 0.0, float(h), 0.0, -1.0)

        total_pts = w * h
        step = max(1, int(math.ceil(math.sqrt(total_pts / max_points))))

        out_w = w // step
        out_h = h // step

        # Read elevation data
        # If this is an RGB/Byte raster and NO raw DEM was found, do NOT use 0-255 brightness as false elevation!
        is_pure_rgb_no_dem = (is_rgb_or_relief and not dem_owns_ds and elev_band.DataType == gdal.GDT_Byte)

        if is_pure_rgb_no_dem:
            # Planar 3D textured drape so it doesn't create corrugated stripes
            elev = np.zeros((out_h, out_w), dtype=np.float32)
        else:
            elev = elev_band.ReadAsArray(0, 0, w, h, buf_xsize=out_w, buf_ysize=out_h).astype(np.float32)

        elev_band = None
        if dem_owns_ds:
            dem_ds = None

        # 3. Read RGB color texture if available (e.g. from 3D relief or RGB raster)
        rgb_tex = None
        alpha_mask = np.ones((out_h, out_w), dtype=bool)
        if is_rgb_or_relief or raster_count >= 3:
            try:
                b1 = ds.GetRasterBand(1).ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize, buf_xsize=out_w, buf_ysize=out_h).astype(np.float32)
                b2 = ds.GetRasterBand(2).ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize, buf_xsize=out_w, buf_ysize=out_h).astype(np.float32)
                b3 = ds.GetRasterBand(3).ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize, buf_xsize=out_w, buf_ysize=out_h).astype(np.float32)
                
                if raster_count >= 4:
                    b4 = ds.GetRasterBand(4).ReadAsArray(0, 0, ds.RasterXSize, ds.RasterYSize, buf_xsize=out_w, buf_ysize=out_h)
                    alpha_mask = (b4 > 10)

                r_norm = np.clip(b1 / 255.0, 0.0, 1.0)
                g_norm = np.clip(b2 / 255.0, 0.0, 1.0)
                b_norm = np.clip(b3 / 255.0, 0.0, 1.0)
                rgb_tex = np.dstack((r_norm, g_norm, b_norm))
            except Exception:
                rgb_tex = None
                alpha_mask = np.ones((out_h, out_w), dtype=bool)

        ds = None

        cols = np.arange(out_w)
        rows = np.arange(out_h)
        grid_c, grid_r = np.meshgrid(cols, rows)

        res_x = gt[1] * step
        res_y = gt[5] * step
        x_arr = gt[0] + grid_c * res_x
        y_arr = gt[3] + grid_r * res_y

        valid = np.isfinite(elev) & (elev > -10000) & (elev < 50000) & alpha_mask
        if nodata is not None:
            valid &= (elev != nodata)

        if not np.any(valid):
            raise ValueError("No valid elevation pixels found in raster.")

        x_v = x_arr[valid].astype(np.float64)
        y_v = y_arr[valid].astype(np.float64)
        z_v = elev[valid].astype(np.float32)

        z_min = float(np.min(z_v))
        z_max = float(np.max(z_v))
        z_range = max(0.001, z_max - z_min)

        cx = float((np.min(x_v) + np.max(x_v)) / 2.0)
        cy = float((np.min(y_v) + np.max(y_v)) / 2.0)
        cz = float((z_min + z_max) / 2.0)

        x_centered = (x_v - cx).astype(np.float32)
        y_centered = (y_v - cy).astype(np.float32)
        z_centered = (z_v - cz).astype(np.float32)

        if abs(cx) <= 180 and abs(cy) <= 90:
            meters_per_deg_lat = 111320.0
            meters_per_deg_lon = 111320.0 * math.cos(math.radians(cy))
            x_centered = (x_centered * meters_per_deg_lon).astype(np.float32)
            y_centered = (y_centered * meters_per_deg_lat).astype(np.float32)

        pts_xyz = np.column_stack((x_centered, y_centered, z_centered)).astype(np.float32)

        z_norm = np.clip((z_v - z_min) / z_range, 0.0, 1.0)
        z_colors = apply_turbo_colormap(z_norm)

        # Extract RGB draped colors for the valid points
        if rgb_tex is not None:
            rgb_valid = rgb_tex[valid]
            rgb_colors = np.ascontiguousarray(rgb_valid, dtype=np.float32)
        else:
            rgb_colors = None

        color_dict = {
            "Elevation": z_colors,
        }
        if rgb_colors is not None:
            color_dict["RGB"] = rgb_colors

        return (pts_xyz, rgb_colors, z_colors, None, None, (cx, cy, cz), z_min, z_max, total_pts, color_dict)

    @staticmethod
    def load_ascii_ply_points(file_path: str, max_points: int = 8000000):
        """Loads points from ASCII XYZ, PTS, CSV, TXT, or PLY point cloud files."""
        ext = os.path.splitext(file_path)[1].lower()
        xyz_list = []
        rgb_list = []

        if ext in [".xyz", ".txt", ".pts", ".csv"]:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = []
                    for i, line in enumerate(f):
                        line = line.strip()
                        if not line or line.startswith("#") or line.startswith("//"):
                            continue
                        lines.append(line)
                        if len(lines) >= max_points * 2:
                            break

                total_points = len(lines)
                step = max(1, total_points // max_points)
                sampled_lines = lines[::step]

                for line in sampled_lines:
                    parts = line.replace(",", " ").split()
                    if len(parts) >= 3:
                        try:
                            x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                            xyz_list.append((x, y, z))
                            if len(parts) >= 6:
                                r, g, b = float(parts[3]), float(parts[4]), float(parts[5])
                                if r > 1.0 or g > 1.0 or b > 1.0:
                                    r, g, b = r / 255.0, g / 255.0, b / 255.0
                                rgb_list.append((r, g, b))
                        except ValueError:
                            continue
            except Exception:
                pass

        if not xyz_list:
            raise ValueError(f"Could not parse point cloud data from: {file_path}")

        pts = np.array(xyz_list, dtype=np.float64)
        x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
        rgb_colors = np.array(rgb_list, dtype=np.float32) if len(rgb_list) == len(pts) else None
        return PointCloudReader._process_coordinates(x, y, z, rgb_colors, None, None, len(pts))

    @staticmethod
    def _process_coordinates(x, y, z, rgb_colors, class_colors, intensity_colors, total_points, extra_attrs=None):
        valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        valid &= ~((x == 0.0) & (y == 0.0))
        if not np.any(valid):
            raise ValueError("No valid 3D points found in dataset.")

        x = x[valid]
        y = y[valid]
        z = z[valid]

        if rgb_colors is not None and len(rgb_colors) == len(valid):
            rgb_colors = rgb_colors[valid]
        if class_colors is not None and len(class_colors) == len(valid):
            class_colors = class_colors[valid]
        if intensity_colors is not None and len(intensity_colors) == len(valid):
            intensity_colors = intensity_colors[valid]

        # Filter extreme spatial outliers (e.g. 0,0 or telemetry errors)
        p_x0, p_x1 = np.percentile(x, [0.1, 99.9])
        p_y0, p_y1 = np.percentile(y, [0.1, 99.9])
        p_z0, p_z1 = np.percentile(z, [0.1, 99.9])

        span_x = max(10.0, p_x1 - p_x0)
        span_y = max(10.0, p_y1 - p_y0)
        span_z = max(5.0, p_z1 - p_z0)

        inliers = (x >= p_x0 - span_x * 0.5) & (x <= p_x1 + span_x * 0.5) & \
                  (y >= p_y0 - span_y * 0.5) & (y <= p_y1 + span_y * 0.5) & \
                  (z >= p_z0 - span_z * 2.0) & (z <= p_z1 + span_z * 2.0)

        if np.any(inliers):
            x = x[inliers]
            y = y[inliers]
            z = z[inliers]
            if rgb_colors is not None and len(rgb_colors) == len(inliers):
                rgb_colors = rgb_colors[inliers]
            if class_colors is not None and len(class_colors) == len(inliers):
                class_colors = class_colors[inliers]
            if intensity_colors is not None and len(intensity_colors) == len(inliers):
                intensity_colors = intensity_colors[inliers]

        z_min = float(np.min(z))
        z_max = float(np.max(z))
        z_range = max(0.001, z_max - z_min)

        cx = float((np.min(x) + np.max(x)) / 2.0)
        cy = float((np.min(y) + np.max(y)) / 2.0)
        cz = float((z_min + z_max) / 2.0)

        x_centered = (x - cx).astype(np.float32)
        y_centered = (y - cy).astype(np.float32)
        z_centered = (z - cz).astype(np.float32)

        if abs(cx) <= 180 and abs(cy) <= 90:
            meters_per_deg_lat = 111320.0
            meters_per_deg_lon = 111320.0 * math.cos(math.radians(cy))
            x_centered = (x_centered * meters_per_deg_lon).astype(np.float32)
            y_centered = (y_centered * meters_per_deg_lat).astype(np.float32)

        pts_xyz = np.column_stack((x_centered, y_centered, z_centered)).astype(np.float32)

        z_norm = np.clip((z - z_min) / z_range, 0.0, 1.0)
        z_colors = apply_turbo_colormap(z_norm)

        color_dict = {}
        if extra_attrs:
            for k, arr in extra_attrs.items():
                if len(arr) == len(valid):
                    arr_valid = arr[valid]
                    if k == 'return_number':
                        color_dict[k] = apply_return_number_colormap(arr_valid)
                    elif k == 'scan_angle':
                        s_norm = np.clip((arr_valid + 35.0) / 70.0, 0.0, 1.0)
                        color_dict[k] = apply_spectral_colormap(s_norm)
                    elif k == 'point_source_id':
                        color_dict[k] = apply_categorical_colormap(arr_valid)
                    elif k in ['nir', 'intensity']:
                        i_min, i_max = np.percentile(arr_valid, [2, 98]) if len(arr_valid) > 0 else (0, 1)
                        i_norm = np.clip((arr_valid - i_min) / max(1.0, i_max - i_min), 0.0, 1.0)
                        color_dict[k] = apply_plasma_colormap(i_norm)

        return (
            pts_xyz, rgb_colors, z_colors, class_colors,
            intensity_colors, (cx, cy, cz), z_min, z_max, total_points, color_dict
        )

    @staticmethod
    def load_vector_3d_points(file_path: str, max_points: int = 8000000):
        """
        Extracts 3D geometries and surfaces from any GIS Vector dataset (GPKG, SHP, GeoJSON, KML):
        Supports 3D polygons (planar roof facets, building footprints), 3D lines, and 3D points.
        """
        from osgeo import ogr
        ds = ogr.Open(file_path, 0)
        if not ds:
            raise ValueError(f"Could not open vector dataset: {file_path}")

        lyr = ds.GetLayer(0)
        pts_list = []
        rgb_list = []
        feat_count = lyr.GetFeatureCount()
        max_sample_pts = min(max_points, 500000)

        for feat in lyr:
            geom = feat.GetGeometryRef()
            if not geom:
                continue

            # Attribute-based elevation fallback
            elev = 0.0
            for elev_fld in ("Elevation_m", "Height_m", "Apex_Z_m", "Base_Z_m", "Z", "ELEV", "HEIGHT"):
                if feat.GetFieldIndex(elev_fld) >= 0 and feat.GetField(elev_fld) is not None:
                    try:
                        elev = float(feat.GetField(elev_fld))
                        break
                    except Exception:
                        pass

            pitch_deg = float(feat.GetField("Pitch_deg") or 0.0) if feat.GetFieldIndex("Pitch_deg") >= 0 else 0.0
            az_deg = float(feat.GetField("Azimuth_deg") or 0.0) if feat.GetFieldIndex("Azimuth_deg") >= 0 else 0.0
            pitch = math.radians(pitch_deg)
            az = math.radians(az_deg)

            rating = feat.GetField("Solar_Rating") if feat.GetFieldIndex("Solar_Rating") >= 0 else None
            if rating == "OPTIMAL":
                col = [0.1, 0.85, 0.25]
            elif rating == "GOOD":
                col = [0.95, 0.8, 0.1]
            elif rating == "FAIR":
                col = [0.95, 0.5, 0.1]
            elif rating == "POOR":
                col = [0.85, 0.2, 0.2]
            else:
                col = [0.2, 0.6, 0.95]

            g_name = geom.GetGeometryName().upper()

            # 1. Polygon / MultiPolygon (e.g. planar roof facets, buildings)
            if "POLYGON" in g_name:
                polys = [geom] if g_name == "POLYGON" else [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
                for p_geom in polys:
                    env = p_geom.GetEnvelope()
                    cx = (env[0] + env[1]) / 2.0
                    cy = (env[2] + env[3]) / 2.0
                    slope_x = -math.sin(az) * math.tan(pitch)
                    slope_y = -math.cos(az) * math.tan(pitch)

                    # Boundary ring points
                    for r_idx in range(p_geom.GetGeometryCount()):
                        ring = p_geom.GetGeometryRef(r_idx)
                        for i in range(ring.GetPointCount()):
                            p = ring.GetPoint(i)
                            pz = p[2] if len(p) > 2 and abs(p[2]) > 1e-4 else (elev + (p[0] - cx) * slope_x + (p[1] - cy) * slope_y)
                            pts_list.append((p[0], p[1], pz))
                            rgb_list.append([0.15, 0.2, 0.25])

                    # Surface interior points
                    dx = max(0.1, env[1] - env[0])
                    dy = max(0.1, env[3] - env[2])
                    step = max(0.4, min(dx, dy) / 25.0)

                    xs = np.arange(env[0], env[1], step)
                    ys = np.arange(env[2], env[3], step)
                    if len(xs) * len(ys) <= 4000:
                        gx, gy = np.meshgrid(xs, ys)

                        for x_val, y_val in zip(gx.flatten(), gy.flatten()):
                            pt = ogr.Geometry(ogr.wkbPoint)
                            pt.AddPoint_2D(x_val, y_val)
                            if p_geom.Contains(pt):
                                z_val = elev + (x_val - cx) * slope_x + (y_val - cy) * slope_y
                                pts_list.append((x_val, y_val, z_val))
                                rgb_list.append(col)

            # 2. LineString (e.g. 3D powerlines, contours)
            elif "LINESTRING" in g_name:
                pts = geom.GetPoints()
                if pts:
                    for idx in range(len(pts) - 1):
                        p1 = np.array(pts[idx], dtype=np.float64)
                        p2 = np.array(pts[idx + 1], dtype=np.float64)
                        seg_dist = float(np.linalg.norm(p2[:2] - p1[:2]))
                        num_steps = max(2, int(seg_dist / 1.0))
                        for step_frac in np.linspace(0.0, 1.0, num_steps, endpoint=(idx == len(pts) - 2)):
                            interp_pt = p1 + step_frac * (p2 - p1)
                            z_val = float(interp_pt[2]) if len(interp_pt) > 2 and abs(interp_pt[2]) > 1e-4 else elev
                            pts_list.append((interp_pt[0], interp_pt[1], z_val))
                            rgb_list.append([0.9, 0.7, 0.1])

            # 3. Point / MultiPoint (e.g. towers, trees)
            elif "POINT" in g_name:
                pz = geom.GetZ() if geom.GetCoordinateDimension() == 3 and abs(geom.GetZ()) > 1e-4 else elev
                pts_list.append((geom.GetX(), geom.GetY(), pz))
                rgb_list.append(col)

            if len(pts_list) >= max_sample_pts:
                break

        if not pts_list:
            raise ValueError(f"No 3D geometries or coordinates could be extracted from: {file_path}")

        pts_arr = np.array(pts_list, dtype=np.float64)
        rgb_arr = np.array(rgb_list, dtype=np.float32) if len(rgb_list) == len(pts_arr) else None
        return PointCloudReader._process_coordinates(
            pts_arr[:, 0], pts_arr[:, 1], pts_arr[:, 2],
            rgb_arr, None, None, len(pts_arr)
        )

    @staticmethod
    def load_las_points(file_path: str, max_points: int = 8000000):
        """
        Extracts 3D points from ANY LAS, LAZ, COPC, DEM, GPKG, SHP, XYZ, PTS, CSV file:
        Returns: (xyz_centered, rgb_colors, z_colors, class_colors,
                  intensity_colors, center_orig, z_min, z_max, total_points, color_dict)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Point cloud file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".tif", ".tiff", ".dem", ".dtm", ".dsm", ".hgt", ".asc", ".img"]:
            for las_ext in [".las", ".laz", ".copc.laz"]:
                cand = file_path.replace(ext, las_ext)
                if os.path.exists(cand):
                    file_path = cand
                    ext = las_ext
                    break
            else:
                return PointCloudReader.load_dem_points(file_path, max_points)

        if ext in [".xyz", ".pts", ".csv", ".txt", ".ply"]:
            return PointCloudReader.load_ascii_ply_points(file_path, max_points)

        if ext in [".gpkg", ".shp", ".geojson", ".json", ".kml"]:
            try:
                return PointCloudReader.load_vector_3d_points(file_path, max_points)
            except Exception as e:
                # Fallback to parent point cloud if vector 3D extraction fails
                base_cand = file_path
                for sfx in ["_roof_facets", "_conductors", "_towers", "_danger_trees", "_clearance"]:
                    if sfx in base_cand:
                        base_cand = base_cand.replace(sfx, "")
                        break
                base_stem, _ = os.path.splitext(base_cand)
                for cand_ext in [".copc.laz", ".laz", ".las"]:
                    cand_file = base_stem + cand_ext
                    if os.path.exists(cand_file):
                        return PointCloudReader.load_las_points(cand_file, max_points)
                raise e

        if file_path.endswith("_surface.tif"):
            for cand_ext in [".las", ".laz", ".copc.laz", ".e57"]:
                cand = file_path.replace("_surface.tif", cand_ext)
                if os.path.exists(cand):
                    file_path = cand
                    break

        x, y, z, rgb_colors, class_colors, intensity_colors, total_points, extra_attrs = load_las_points_data(
            file_path, max_points=max_points
        )

        return PointCloudReader._process_coordinates(
            x, y, z, rgb_colors, class_colors, intensity_colors, total_points, extra_attrs
        )

