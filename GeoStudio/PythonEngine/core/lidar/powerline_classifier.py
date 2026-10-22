# -*- coding: utf-8 -*-
"""
GeoStudio - Powerline and Transmission Tower Classification Engine
Detects, segments, and classifies utility corridor assets from LiDAR point clouds:
1. Conductor Wires (ASPRS Class 14 - Wire Conductor) via 3D linearity tensor and catenary continuity
2. Transmission Towers / Pylons (ASPRS Class 15 - Transmission Structure) via verticality and structural clustering
3. Vector extraction of 3D wire strings and tower footprint/apex locations (GPKG / SHP)
"""

import os
import json
import time
import math
from typing import Dict, Any, Callable, Optional, List, Tuple
import numpy as np
from scipy.spatial import cKDTree
from osgeo import ogr, osr


class PowerlineClassifier:
    """Classifies conductor wires and transmission towers in LiDAR point clouds (LAS/LAZ/COPC)."""

    @classmethod
    def classify_corridor(
        cls,
        input_las_path: str,
        output_las_path: Optional[str] = None,
        output_vectors_path: Optional[str] = None,
        min_wire_height_m: float = 4.0,
        max_wire_height_m: float = 65.0,
        min_linearity: float = 0.70,
        max_scattering: float = 0.15,
        search_radius_m: float = 2.0,
        min_span_length_m: float = 20.0,
        min_tower_height_m: float = 12.0,
        tower_radius_m: float = 8.0,
        exclude_vegetation_classes: bool = True,
        require_tower_wire_connection: bool = True,
        export_vectors: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Processes LiDAR point cloud, classifies conductor wires (14) and transmission towers (15),
        and exports 3D vector conductors & tower centroids.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        import laspy

        progress(5, f"Reading LiDAR point cloud: {os.path.basename(input_las_path)}...")
        log(f"Reading LiDAR file: <code>{input_las_path}</code>")

        las = laspy.read(input_las_path)
        point_count = len(las.x)
        log(f"Total points loaded: <b>{point_count:,}</b>")

        coords = np.vstack((las.x, las.y, las.z)).T

        # Derive approximate Height Above Ground (HAG) if not explicitly present
        progress(15, "Estimating ground elevation baseline and Height Above Ground (HAG)...")
        has_hag = hasattr(las, "HeightAboveGround")
        if has_hag:
            hag = np.array(las.HeightAboveGround, dtype=np.float32)
        else:
            # Grid-based minimum Z approximation
            grid_res = 10.0
            x_min, y_min = np.min(coords[:, 0]), np.min(coords[:, 1])
            gx = ((coords[:, 0] - x_min) / grid_res).astype(np.int32)
            gy = ((coords[:, 1] - y_min) / grid_res).astype(np.int32)
            cell_keys = (gx.astype(np.int64) << 32) | gy.astype(np.int64)

            # Fast minimum per cell
            order = np.argsort(cell_keys)
            sorted_keys = cell_keys[order]
            sorted_z = coords[order, 2]

            unique_keys, idx_start = np.unique(sorted_keys, return_index=True)
            min_z_map = {}
            for i, u_k in enumerate(unique_keys):
                end = idx_start[i + 1] if (i + 1) < len(idx_start) else len(sorted_z)
                min_z_map[u_k] = np.min(sorted_z[idx_start[i]:end])

            cell_ground = np.array([min_z_map.get(k, coords[i, 2]) for i, k in enumerate(cell_keys)], dtype=np.float32)
            hag = coords[:, 2] - cell_ground

        # Check existing classifications
        classes_raw = np.array(las.classification)
        unique_classes = set(np.unique(classes_raw))
        has_veg = any(c in unique_classes for c in [3, 4, 5])

        # Base candidate corridor points above min_wire_height_m
        candidate_mask = (hag >= min_wire_height_m) & (hag <= max_wire_height_m)

        if exclude_vegetation_classes and has_veg:
            # Exclude pre-classified Ground (2), Vegetation (3, 4, 5), Building (6), etc.
            # Focus on unclassified (0, 1) or existing corridor assets (14, 15)
            corridor_cand_mask = np.isin(classes_raw, [0, 1, 14, 15])
            candidate_mask = candidate_mask & corridor_cand_mask
            log("Excluding pre-classified Vegetation (ASPRS 3, 4, 5), Ground, and Buildings from candidate search.")

        cand_indices = np.where(candidate_mask)[0]
        num_candidates = len(cand_indices)
        log(f"Candidate corridor points (HAG {min_wire_height_m}m - {max_wire_height_m}m): <b>{num_candidates:,}</b>")

        conductor_spans = []
        towers_list = []
        wire_indices = np.array([], dtype=np.int64)
        tower_indices = np.array([], dtype=np.int64)

        if num_candidates < 15:
            log("<span style='color:#eab308;'>No elevated utility corridor points detected.</span>")
        else:
            cand_pts = coords[cand_indices]
            progress(25, "Building 3D spatial index for geometric covariance analysis...")
            tree = cKDTree(cand_pts)

            progress(35, "Computing 3D linearity, planarity, and verticality tensors...")
            # Query neighbors within search radius
            k_neighbors = min(24, num_candidates)
            dists, idxs = tree.query(cand_pts, k=k_neighbors)

            linearities = np.zeros(num_candidates, dtype=np.float32)
            verticalities = np.zeros(num_candidates, dtype=np.float32)
            scatterings = np.zeros(num_candidates, dtype=np.float32)
            horiz_dir = np.zeros(num_candidates, dtype=np.float32)

            batch_size = 50000
            for start in range(0, num_candidates, batch_size):
                end = min(start + batch_size, num_candidates)
                batch_neighbors = cand_pts[idxs[start:end]] # shape: (B, K, 3)
                means = np.mean(batch_neighbors, axis=1, keepdims=True)
                diffs = batch_neighbors - means
                covs = np.einsum('bki,bkj->bij', diffs, diffs) / (k_neighbors - 1)

                evals, evecs = np.linalg.eigh(covs) # ascending order: evals[:, 0] <= evals[:, 1] <= evals[:, 2]
                l1 = evals[:, 2] # primary eigenvalue
                l2 = evals[:, 1]
                l3 = np.maximum(0.0, evals[:, 0])

                norm = np.maximum(l1, 1e-6)
                lin = (l1 - l2) / norm
                scat = l3 / norm

                # Primary direction vector evecs[:, :, 2]
                ez = np.abs(evecs[:, 2, 2])
                # Normal vector of minor axis evecs[:, :, 0]
                vert = 1.0 - np.abs(evecs[:, 2, 0])

                linearities[start:end] = lin
                scatterings[start:end] = scat
                verticalities[start:end] = vert
                horiz_dir[start:end] = ez

                pct = 35 + int((start / max(1, num_candidates)) * 25)
                progress(pct, f"Calculating 3D geometric eigenvalues ({end:,} / {num_candidates:,})...")

            # 1. Conductor Wires: high linearity, low scattering, predominantly horizontal (ez <= 0.60)
            wire_cand_mask = (linearities >= min_linearity) & (scatterings <= max_scattering) & (horiz_dir <= 0.60)
            raw_wire_local_idx = np.where(wire_cand_mask)[0]
            raw_wire_indices = cand_indices[raw_wire_local_idx]

            # Cluster wire points into continuous spans and filter out short twig/branch fragments
            progress(60, "Clustering and validating continuous conductor wire spans...")
            valid_wire_indices_list = []
            if len(raw_wire_indices) >= 15:
                wire_coords = coords[raw_wire_indices]
                w_tree = cKDTree(wire_coords)
                visited = np.zeros(len(wire_coords), dtype=bool)
                span_id = 1

                for i in range(len(wire_coords)):
                    if visited[i]:
                        continue
                    # BFS component
                    comp = []
                    queue = [i]
                    visited[i] = True
                    while queue and len(comp) < 30000:
                        curr = queue.pop(0)
                        comp.append(curr)
                        neighs = w_tree.query_ball_point(wire_coords[curr], r=3.5)
                        for n in neighs:
                            if 0 <= n < len(wire_coords) and not visited[n]:
                                visited[n] = True
                                queue.append(n)

                    if len(comp) >= 15:
                        comp_arr = np.array(comp, dtype=np.int64)
                        span_pts = wire_coords[comp_arr]

                        # PCA along principal horizontal axis
                        xy_centered = span_pts[:, :2] - np.mean(span_pts[:, :2], axis=0)
                        u, s, vt = np.linalg.svd(xy_centered, full_matrices=False)
                        pca_vec = vt[0]
                        proj = np.dot(span_pts[:, :2], pca_vec)
                        sort_idx = np.argsort(proj)
                        sorted_span = span_pts[sort_idx]

                        # Calculate 3D and horizontal extent
                        diffs = np.diff(sorted_span, axis=0)
                        length_3d = float(np.sum(np.sqrt(np.sum(diffs ** 2, axis=1))))
                        span_extent = float(proj[sort_idx[-1]] - proj[sort_idx[0]])

                        # Straightness check: lateral RMSE in horizontal plane
                        lateral_rmse = float(np.sqrt(np.mean(np.dot(xy_centered, vt[1]) ** 2))) if len(vt) > 1 else 0.0

                        # Accept only continuous spans with adequate length and low lateral deviation
                        if (span_extent >= min_span_length_m or length_3d >= min_span_length_m) and lateral_rmse <= 0.85:
                            sag = float(np.max(sorted_span[:, 2]) - np.min(sorted_span[:, 2]))
                            avg_h = float(np.mean(sorted_span[:, 2]))

                            conductor_spans.append({
                                "span_id": span_id,
                                "points": sorted_span,
                                "length_m": round(length_3d, 2),
                                "span_extent_m": round(span_extent, 2),
                                "sag_m": round(sag, 2),
                                "avg_height_m": round(avg_h, 2),
                                "point_count": len(sorted_span)
                            })
                            valid_wire_indices_list.append(raw_wire_indices[comp_arr])
                            span_id += 1

            if valid_wire_indices_list:
                wire_indices = np.concatenate(valid_wire_indices_list)

            # 2. Transmission Towers: high verticality, spatial grid clustering with large height range
            progress(70, "Extracting transmission tower lattice structures...")
            vert_mask = (verticalities >= 0.70) & (~wire_cand_mask)
            vert_local_idx = np.where(vert_mask)[0]

            tower_indices_list = []
            if len(vert_local_idx) > 20:
                vert_pts = cand_pts[vert_local_idx]
                grid_res = max(5.0, float(tower_radius_m))
                vx_min = float(np.min(vert_pts[:, 0]))
                vy_min = float(np.min(vert_pts[:, 1]))
                gx = np.floor((vert_pts[:, 0] - vx_min) / grid_res).astype(np.int64)
                gy = np.floor((vert_pts[:, 1] - vy_min) / grid_res).astype(np.int64)
                cell_keys = (gx << 32) | (gy & 0xFFFFFFFF)

                order = np.argsort(cell_keys)
                sorted_keys = cell_keys[order]
                sorted_z = vert_pts[order, 2]

                unique_keys, idx_starts = np.unique(sorted_keys, return_index=True)
                idx_ends = np.append(idx_starts[1:], len(sorted_z))

                wire_xy_tree = cKDTree(coords[wire_indices, :2]) if len(wire_indices) > 0 else None
                t_id = 1

                for s, e in zip(idx_starts, idx_ends):
                    if (e - s) >= 30: # Substantial structural returns
                        z_sub = sorted_z[s:e]
                        h_span = float(np.max(z_sub) - np.min(z_sub))
                        if h_span >= (min_tower_height_m * 0.75):
                            cell_idx = order[s:e]
                            t_pts = vert_pts[cell_idx]
                            bx, by = float(np.mean(t_pts[:, 0])), float(np.mean(t_pts[:, 1]))
                            base_z = float(np.min(t_pts[:, 2]))
                            apex_z = float(np.max(t_pts[:, 2]))
                            height = apex_z - base_z
                            spread_x = np.max(t_pts[:, 0]) - np.min(t_pts[:, 0])
                            spread_y = np.max(t_pts[:, 1]) - np.min(t_pts[:, 1])
                            footprint_area = spread_x * spread_y

                            # Topological connection check: Tower must connect to/be near conductor wires
                            is_connected = True
                            if require_tower_wire_connection:
                                if wire_xy_tree is not None:
                                    d_near, _ = wire_xy_tree.query([bx, by])
                                    if d_near > (tower_radius_m * 2.5):
                                        is_connected = False
                                else:
                                    # No wires detected anywhere -> isolated columns in forest are tree trunks
                                    is_connected = False

                            if is_connected:
                                towers_list.append({
                                    "tower_id": t_id,
                                    "x": bx,
                                    "y": by,
                                    "base_z": round(base_z, 2),
                                    "apex_z": round(apex_z, 2),
                                    "height_m": round(height, 2),
                                    "footprint_area_m2": round(footprint_area, 2),
                                    "point_count": len(t_pts)
                                })
                                tower_indices_list.append(cand_indices[vert_local_idx[cell_idx]])
                                t_id += 1

            if tower_indices_list:
                tower_indices = np.concatenate(tower_indices_list)

        log(f"<b>Conductor Wire Points (Class 14):</b> {len(wire_indices):,} points ({len(conductor_spans)} spans)")
        log(f"<b>Transmission Tower Points (Class 15):</b> {len(tower_indices):,} points ({len(towers_list)} towers)")

        # Update point classifications
        progress(78, "Updating ASPRS classifications in point cloud...")
        classes = np.array(las.classification)
        # Class 14: Wire Conductor, Class 15: Transmission Tower
        if len(wire_indices) > 0:
            classes[wire_indices] = 14
        if len(tower_indices) > 0:
            classes[tower_indices] = 15
        las.classification = classes

        if not output_las_path:
            base, ext = os.path.splitext(input_las_path)
            output_las_path = f"{base}_powerlines_classified{ext}"

        progress(85, f"Writing classified point cloud to {os.path.basename(output_las_path)}...")
        las.write(output_las_path)

        # Vector Extraction
        conductors_vector_path = None
        towers_vector_path = None

        if export_vectors and (len(conductor_spans) > 0 or len(towers_list) > 0):
            progress(90, "Extracting 3D conductor spans and tower positions...")
            base_vec, _ = os.path.splitext(output_las_path)
            conductors_vector_path = f"{base_vec}_conductors.gpkg"
            towers_vector_path = f"{base_vec}_towers.gpkg"

            # Write vectors via OGR
            cls._write_vectors(conductors_vector_path, towers_vector_path, conductor_spans, towers_list)

        progress(98, "Writing powerline corridor report...")
        report_path = f"{os.path.splitext(output_las_path)[0]}_report.json"
        total_wire_len = sum(s["length_m"] for s in conductor_spans)

        results = {
            "status": "SUCCESS",
            "total_points": point_count,
            "wire_points_class_14": len(wire_indices),
            "tower_points_class_15": len(tower_indices),
            "conductor_spans_count": len(conductor_spans),
            "total_conductor_length_m": round(total_wire_len, 2),
            "transmission_towers_count": len(towers_list),
            "max_tower_height_m": round(max([t["height_m"] for t in towers_list], default=0.0), 2),
            "output_las": output_las_path,
            "conductors_vector": conductors_vector_path,
            "towers_vector": towers_vector_path,
            "report_path": report_path
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        progress(100, f"Classified {len(wire_indices):,} wire points & {len(towers_list)} towers!")
        return results

    @classmethod
    def _write_vectors(
        cls,
        conductors_path: str,
        towers_path: str,
        conductor_spans: List[Dict[str, Any]],
        towers_list: List[Dict[str, Any]]
    ):
        """Writes 3D conductor linestrings and tower point vectors to GeoPackage."""
        driver = ogr.GetDriverByName("GPKG")
        srs = osr.SpatialReference()

        # 1. Conductors 3D LineStrings
        if os.path.exists(conductors_path):
            driver.DeleteDataSource(conductors_path)
        ds_c = driver.CreateDataSource(conductors_path)
        lyr_c = ds_c.CreateLayer("conductor_wires_3d", srs, ogr.wkbLineString25D)

        lyr_c.CreateField(ogr.FieldDefn("Span_ID", ogr.OFTInteger))
        lyr_c.CreateField(ogr.FieldDefn("Length_m", ogr.OFTReal))
        lyr_c.CreateField(ogr.FieldDefn("Sag_m", ogr.OFTReal))
        lyr_c.CreateField(ogr.FieldDefn("Avg_Height_m", ogr.OFTReal))
        lyr_c.CreateField(ogr.FieldDefn("Point_Count", ogr.OFTInteger))

        for span in conductor_spans:
            pts = span["points"]
            line = ogr.Geometry(ogr.wkbLineString25D)
            # Sample smooth line every few points if very dense
            step = max(1, len(pts) // 100)
            sampled = pts[::step]
            for p in sampled:
                line.AddPoint(float(p[0]), float(p[1]), float(p[2]))

            feat = ogr.Feature(lyr_c.GetLayerDefn())
            feat.SetField("Span_ID", int(span["span_id"]))
            feat.SetField("Length_m", float(span["length_m"]))
            feat.SetField("Sag_m", float(span["sag_m"]))
            feat.SetField("Avg_Height_m", float(span["avg_height_m"]))
            feat.SetField("Point_Count", int(span["point_count"]))
            feat.SetGeometry(line)
            lyr_c.CreateFeature(feat)
            feat = None
        ds_c.FlushCache()
        ds_c = None

        # 2. Towers Points
        if os.path.exists(towers_path):
            driver.DeleteDataSource(towers_path)
        ds_t = driver.CreateDataSource(towers_path)
        lyr_t = ds_t.CreateLayer("transmission_towers", srs, ogr.wkbPoint25D)

        lyr_t.CreateField(ogr.FieldDefn("Tower_ID", ogr.OFTInteger))
        lyr_t.CreateField(ogr.FieldDefn("Height_m", ogr.OFTReal))
        lyr_t.CreateField(ogr.FieldDefn("Base_Z_m", ogr.OFTReal))
        lyr_t.CreateField(ogr.FieldDefn("Apex_Z_m", ogr.OFTReal))
        lyr_t.CreateField(ogr.FieldDefn("Footprint_m2", ogr.OFTReal))
        lyr_t.CreateField(ogr.FieldDefn("Point_Count", ogr.OFTInteger))

        for t in towers_list:
            pt = ogr.Geometry(ogr.wkbPoint25D)
            pt.AddPoint(float(t["x"]), float(t["y"]), float(t["apex_z"]))

            feat = ogr.Feature(lyr_t.GetLayerDefn())
            feat.SetField("Tower_ID", int(t["tower_id"]))
            feat.SetField("Height_m", float(t["height_m"]))
            feat.SetField("Base_Z_m", float(t["base_z"]))
            feat.SetField("Apex_Z_m", float(t["apex_z"]))
            feat.SetField("Footprint_m2", float(t["footprint_area_m2"]))
            feat.SetField("Point_Count", int(t["point_count"]))
            feat.SetGeometry(pt)
            lyr_t.CreateFeature(feat)
            feat = None
        ds_t.FlushCache()
        ds_t = None
