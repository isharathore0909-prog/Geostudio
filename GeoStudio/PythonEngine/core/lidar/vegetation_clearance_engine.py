# -*- coding: utf-8 -*-
"""
GeoStudio - Vegetation Clearance & Danger Tree Buffer Engine
Analyzes utility transmission corridor encroachment and tree fall-in hazards:
1. 3D Radial Clearance & Encroachment Detection (Critical <3m, Warning 3-5m, Advisory 5-8m)
2. Danger Tree / Fall-in Hazard Analysis (H >= 2D Distance + Safety Buffer)
3. Corridor Buffer Hazard Polygons (GPKG/SHP)
4. Comprehensive Utility Risk Audit & Priority Tree Maintenance Action List
"""

import os
import json
import math
import time
from typing import Dict, Any, Callable, Optional, List, Tuple
import numpy as np
from scipy.spatial import cKDTree
from osgeo import ogr, osr, gdal


class VegetationClearanceEngine:
    """Rigorous 3D powerline clearance encroachment and danger tree hazard assessment."""

    @classmethod
    def analyze_corridor(
        cls,
        conductors_source: str,
        vegetation_source: str,
        output_vector_path: str,
        critical_dist_m: float = 3.0,
        warning_dist_m: float = 5.0,
        advisory_dist_m: float = 8.0,
        fall_buffer_m: float = 1.5,
        default_tree_height_m: float = 15.0,
        generate_corridor_buffers: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Calculates 3D clearance distance between powerlines and trees.
        Identifies danger trees whose height can strike the lines if felled.
        Outputs enriched vector layer, buffer polygons, and JSON audit report.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        progress(5, "Loading powerline conductors...")
        log(f"Loading conductors: <code>{os.path.basename(conductors_source)}</code>")
        wire_points, srs_wkt = cls._load_conductor_points(conductors_source)
        if len(wire_points) == 0:
            raise ValueError("No 3D conductor wire points or vertices could be extracted from conductors source.")
        log(f"Extracted <b>{len(wire_points):,}</b> 3D conductor sample points.")

        progress(15, "Loading vegetation / tree inventory layer...")
        log(f"Loading vegetation source: <code>{os.path.basename(vegetation_source)}</code>")
        tree_records = cls._load_vegetation(vegetation_source, default_tree_height_m)
        if len(tree_records) == 0:
            raise ValueError("No trees or vegetation features found in the input vegetation source.")
        log(f"Loaded <b>{len(tree_records):,}</b> trees/canopy points for corridor inspection.")

        # Build 3D spatial index of wire points
        progress(25, "Building spatial tree for 3D clearance queries...")
        wire_tree_3d = cKDTree(wire_points)
        wire_tree_2d = cKDTree(wire_points[:, :2])

        tree_pts_2d = np.array([[t["x"], t["y"]] for t in tree_records], dtype=np.float32)
        tree_heights = np.array([t["height"] for t in tree_records], dtype=np.float32)

        progress(35, "Evaluating 3D radial clearance and fall-in hazard reach...")

        # 1. 2D horizontal distance to nearest wire
        dists_2d, nearest_2d_idx = wire_tree_2d.query(tree_pts_2d)

        # 2. 3D distance between tree apex and nearest wire
        # Apex 3D position = (x, y, ground_z + height) or (x, y, z_wire_level)
        apex_z = []
        for i, t in enumerate(tree_records):
            base_z = wire_points[nearest_2d_idx[i], 2] - 5.0 # approximate ground base
            apex_z.append(t.get("z", base_z + t["height"]))
        apex_z = np.array(apex_z, dtype=np.float32)

        tree_apexes = np.column_stack((tree_pts_2d, apex_z))
        dists_3d, nearest_3d_idx = wire_tree_3d.query(tree_apexes)

        # Classify hazard levels
        progress(65, "Classifying encroachment risk levels and danger tree criteria...")
        analyzed_records = []
        critical_count = 0
        warning_count = 0
        advisory_count = 0
        danger_tree_count = 0

        for i, t in enumerate(tree_records):
            d3 = float(dists_3d[i])
            d2 = float(dists_2d[i])
            h = float(tree_heights[i])
            wire_z = float(wire_points[nearest_3d_idx[i], 2])

            # Clearance Level
            if d3 < critical_dist_m:
                clearance_zone = "CRITICAL"
                critical_count += 1
            elif d3 < warning_dist_m:
                clearance_zone = "WARNING"
                warning_count += 1
            elif d3 < advisory_dist_m:
                clearance_zone = "ADVISORY"
                advisory_count += 1
            else:
                clearance_zone = "SAFE"

            # Danger Tree (Fall-In Hazard):
            # If tree falls toward the wire, will it strike the wire?
            # Tree height >= 2D Distance + Safety Buffer
            fall_reach = h - d2
            is_danger_tree = (h + fall_buffer_m) >= d2
            fall_ratio = h / max(0.1, d2)

            if is_danger_tree and clearance_zone == "SAFE":
                danger_tree_count += 1
            elif is_danger_tree:
                danger_tree_count += 1

            # Determine Required Action
            if clearance_zone == "CRITICAL":
                action = "EMERGENCY_PRUNE"
                hazard_score = 95.0 + min(5.0, (critical_dist_m - d3) * 2.0)
            elif is_danger_tree and fall_ratio >= 1.2:
                action = "DANGER_TREE_REMOVAL"
                hazard_score = 80.0 + min(15.0, (fall_ratio - 1.0) * 10.0)
            elif clearance_zone == "WARNING":
                action = "SCHEDULED_PRUNE"
                hazard_score = 70.0 + (warning_dist_m - d3) * 5.0
            elif is_danger_tree:
                action = "MONITOR_FALL_RISK"
                hazard_score = 55.0
            elif clearance_zone == "ADVISORY":
                action = "CORRIDOR_INSPECTION"
                hazard_score = 35.0
            else:
                action = "CLEAR"
                hazard_score = 10.0

            analyzed_records.append({
                "id": t.get("id", i + 1),
                "x": t["x"],
                "y": t["y"],
                "z": float(apex_z[i]),
                "height_m": round(h, 2),
                "dist_3d_m": round(d3, 2),
                "dist_2d_m": round(d2, 2),
                "wire_elev_m": round(wire_z, 2),
                "clearance_zone": clearance_zone,
                "is_danger_tree": "YES" if is_danger_tree else "NO",
                "fall_ratio": round(fall_ratio, 2),
                "fall_reach_m": round(fall_reach, 2),
                "hazard_score": round(hazard_score, 1),
                "action_required": action,
                "geom": t.get("geom")
            })

        log(f"<b>Direct 3D Encroachments:</b> <span style='color:#dc2626;'>Critical (&lt;{critical_dist_m}m): <b>{critical_count:,}</b></span> | <span style='color:#f97316;'>Warning: <b>{warning_count:,}</b></span> | <span style='color:#eab308;'>Advisory: <b>{advisory_count:,}</b></span>")
        log(f"<b>Fall-In Danger Trees (Striking Hazard):</b> <span style='color:#dc2626;'><b>{danger_tree_count:,}</b> trees</span>")

        # Export Enriched Vector Layer
        progress(80, "Writing danger tree vector layer...")
        cls._write_danger_trees_vector(output_vector_path, analyzed_records, srs_wkt)

        buffer_vector_path = None
        if generate_corridor_buffers:
            progress(88, "Generating corridor buffer hazard polygons...")
            base_out, _ = os.path.splitext(output_vector_path)
            buffer_vector_path = f"{base_out}_corridor_buffers.gpkg"
            cls._write_buffer_polygons(buffer_vector_path, wire_points, [critical_dist_m, warning_dist_m, advisory_dist_m], srs_wkt)

        progress(95, "Compiling Vegetation Clearance Audit Report...")
        base_rep, _ = os.path.splitext(output_vector_path)
        report_path = f"{base_rep}_clearance_report.json"

        results = {
            "status": "SUCCESS",
            "total_trees_inspected": len(analyzed_records),
            "critical_encroachments_count": critical_count,
            "warning_encroachments_count": warning_count,
            "advisory_encroachments_count": advisory_count,
            "total_danger_trees_count": danger_tree_count,
            "emergency_prune_required": sum(1 for r in analyzed_records if r["action_required"] == "EMERGENCY_PRUNE"),
            "tree_removal_required": sum(1 for r in analyzed_records if r["action_required"] == "DANGER_TREE_REMOVAL"),
            "min_recorded_clearance_m": round(min([r["dist_3d_m"] for r in analyzed_records], default=999.0), 2),
            "output_vector": output_vector_path,
            "buffer_vector": buffer_vector_path,
            "report_path": report_path
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        progress(100, f"Analysis complete: {critical_count} critical violations, {danger_tree_count} danger trees identified!")
        return results

    @classmethod
    def _load_conductor_points(cls, source_path: str) -> Tuple[np.ndarray, str]:
        """Extracts 3D wire points from vector LineString or LAS point cloud."""
        ext = os.path.splitext(source_path)[1].lower()
        wire_pts = []
        wkt = ""

        if ext in [".las", ".laz"]:
            import laspy
            las = laspy.read(source_path)
            cls_vals = np.array(las.classification)
            # Use Class 14 (Wire Conductor) if present; else use elevated points
            mask = (cls_vals == 14)
            if not np.any(mask):
                mask = (cls_vals != 2) & (las.z > np.min(las.z) + 6.0)
            wire_pts = np.vstack((las.x[mask], las.y[mask], las.z[mask])).T
        else:
            ds = ogr.Open(source_path, 0)
            if not ds:
                raise RuntimeError(f"Could not open conductor vector: {source_path}")
            lyr = ds.GetLayer(0)
            srs = lyr.GetSpatialRef()
            if srs:
                wkt = srs.ExportToWkt()

            for feat in lyr:
                geom = feat.GetGeometryRef()
                if not geom:
                    continue
                g_type = geom.GetGeometryType()
                def _add_line_points(g):
                    pts = g.GetPoints()
                    if not pts:
                        return
                    for idx in range(len(pts) - 1):
                        p1 = np.array(pts[idx], dtype=np.float32)
                        p2 = np.array(pts[idx + 1], dtype=np.float32)
                        seg_dist = float(np.linalg.norm(p2[:2] - p1[:2]))
                        num_steps = max(2, int(seg_dist / 1.0)) # sample every 1 meter along span
                        for step_frac in np.linspace(0.0, 1.0, num_steps, endpoint=(idx == len(pts) - 2)):
                            interp_pt = p1 + step_frac * (p2 - p1)
                            z_val = float(interp_pt[2]) if len(interp_pt) > 2 else 20.0
                            wire_pts.append([float(interp_pt[0]), float(interp_pt[1]), z_val])

                g_name = geom.GetGeometryName().upper()
                if "LINESTRING" in g_name:
                    if geom.GetGeometryCount() > 0:
                        for part_idx in range(geom.GetGeometryCount()):
                            _add_line_points(geom.GetGeometryRef(part_idx))
                    else:
                        _add_line_points(geom)
                elif "POINT" in g_name:
                    z = geom.GetZ() if geom.GetCoordinateDimension() == 3 else 20.0
                    wire_pts.append([geom.GetX(), geom.GetY(), z])

        if len(wire_pts) == 0:
            return np.empty((0, 3), dtype=np.float32), wkt

        pts_arr = np.array(wire_pts, dtype=np.float32)
        return pts_arr, wkt

    @classmethod
    def _load_vegetation(cls, source_path: str, default_h: float) -> List[Dict[str, Any]]:
        """Extracts tree positions and heights from vector layer or raster CHM."""
        ext = os.path.splitext(source_path)[1].lower()
        records = []

        if ext in [".tif", ".tiff"]:
            ds = gdal.Open(source_path, gdal.GA_ReadOnly)
            band = ds.GetRasterBand(1)
            gt = ds.GetGeoTransform()
            arr = band.ReadAsArray()
            nodata = band.GetNoDataValue()
            step = max(1, min(arr.shape) // 150) # Sample grid

            for r in range(0, arr.shape[0], step):
                for c in range(0, arr.shape[1], step):
                    val = float(arr[r, c])
                    if val >= 2.5 and (nodata is None or val != nodata):
                        x = gt[0] + c * gt[1] + r * gt[2]
                        y = gt[3] + c * gt[4] + r * gt[5]
                        records.append({
                            "id": len(records) + 1,
                            "x": x,
                            "y": y,
                            "height": val,
                            "geom": None
                        })
        else:
            ds = ogr.Open(source_path, 0)
            if not ds:
                raise RuntimeError(f"Could not open vegetation vector: {source_path}")
            lyr = ds.GetLayer(0)

            for i, feat in enumerate(lyr):
                geom = feat.GetGeometryRef()
                if not geom:
                    continue
                h = float(feat.GetField("Height_m")) if feat.GetFieldIndex("Height_m") >= 0 else default_h
                h = max(1.5, h)

                if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D):
                    gx, gy = geom.GetX(), geom.GetY()
                else:
                    cent = geom.Centroid()
                    gx, gy = cent.GetX(), cent.GetY()

                z = geom.GetZ() if geom.GetCoordinateDimension() == 3 else None

                records.append({
                    "id": feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else (i + 1),
                    "x": gx,
                    "y": gy,
                    "z": z,
                    "height": h,
                    "geom": geom.Clone()
                })

        return records

    @classmethod
    def _write_danger_trees_vector(cls, path: str, records: List[Dict[str, Any]], wkt: str):
        """Serializes analyzed danger tree markers to GPKG or SHP."""
        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(path):
            driver.DeleteDataSource(path)

        ds = driver.CreateDataSource(path)
        srs = osr.SpatialReference()
        if wkt:
            srs.ImportFromWkt(wkt)

        lyr = ds.CreateLayer("danger_trees_hazard", srs, ogr.wkbPoint25D)

        fields = [
            ("Tree_ID", ogr.OFTInteger),
            ("Height_m", ogr.OFTReal),
            ("Dist_3D_m", ogr.OFTReal),
            ("Dist_2D_m", ogr.OFTReal),
            ("Clear_Zone", ogr.OFTString),
            ("DangerTree", ogr.OFTString),
            ("Fall_Ratio", ogr.OFTReal),
            ("FallReach_m", ogr.OFTReal),
            ("Hazard_Score", ogr.OFTReal),
            ("Action_Req", ogr.OFTString),
        ]
        for f_name, f_type in fields:
            lyr.CreateField(ogr.FieldDefn(f_name, f_type))

        for r in records:
            feat = ogr.Feature(lyr.GetLayerDefn())
            feat.SetField("Tree_ID", int(r["id"]))
            feat.SetField("Height_m", float(r["height_m"]))
            feat.SetField("Dist_3D_m", float(r["dist_3d_m"]))
            feat.SetField("Dist_2D_m", float(r["dist_2d_m"]))
            feat.SetField("Clear_Zone", str(r["clearance_zone"]))
            feat.SetField("DangerTree", str(r["is_danger_tree"]))
            feat.SetField("Fall_Ratio", float(r["fall_ratio"]))
            feat.SetField("FallReach_m", float(r["fall_reach_m"]))
            feat.SetField("Hazard_Score", float(r["hazard_score"]))
            feat.SetField("Action_Req", str(r["action_required"]))

            pt = ogr.Geometry(ogr.wkbPoint25D)
            pt.AddPoint(float(r["x"]), float(r["y"]), float(r["z"]))
            feat.SetGeometry(pt)

            lyr.CreateFeature(feat)
            feat = None

        ds.FlushCache()
        ds = None

    @classmethod
    def _write_buffer_polygons(cls, path: str, wire_points: np.ndarray, buffer_radii: List[float], wkt: str):
        """Creates 2D corridor buffer hazard zones around powerline conductors."""
        from shapely.geometry import MultiPoint

        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(path):
            driver.DeleteDataSource(path)

        ds = driver.CreateDataSource(path)
        srs = osr.SpatialReference()
        if wkt:
            srs.ImportFromWkt(wkt)

        lyr = ds.CreateLayer("corridor_hazard_buffers", srs, ogr.wkbMultiPolygon)
        lyr.CreateField(ogr.FieldDefn("Buffer_Name", ogr.OFTString))
        lyr.CreateField(ogr.FieldDefn("Radius_m", ogr.OFTReal))
        lyr.CreateField(ogr.FieldDefn("Risk_Level", ogr.OFTString))

        # Sample points to build continuous convex corridor
        pts_2d = wire_points[:, :2]
        step = max(1, len(pts_2d) // 500)
        sampled = pts_2d[::step]
        mp = MultiPoint(sampled)

        names = [("Critical Buffer (<3m)", "CRITICAL"), ("Warning Buffer (<5m)", "HIGH"), ("Advisory Buffer (<8m)", "MEDIUM")]
        for (radius, (b_name, r_level)) in zip(buffer_radii, names):
            buf = mp.buffer(radius)
            if buf.is_empty:
                continue

            feat = ogr.Feature(lyr.GetLayerDefn())
            feat.SetField("Buffer_Name", b_name)
            feat.SetField("Radius_m", float(radius))
            feat.SetField("Risk_Level", r_level)

            # Convert to OGR geometry
            poly_wkt = buf.wkt
            poly_ogr = ogr.CreateGeometryFromWkt(poly_wkt)
            if poly_ogr:
                poly_multi = ogr.ForceToMultiPolygon(poly_ogr)
                feat.SetGeometry(poly_multi)
                lyr.CreateFeature(feat)
                feat = None

        ds.FlushCache()
        ds = None
