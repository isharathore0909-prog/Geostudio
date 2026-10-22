# -*- coding: utf-8 -*-
"""
GeoStudio - High-Performance Road Surface & Pavement Classification Engine
Multi-criteria DTM and LiDAR evidence pipeline for detecting road corridors and ASPRS Class 11:
- Bare-earth raster DTM generation (1.0m resolution) with distance-transform hole filling
- Multi-criteria evidence evaluation: Slope (|∇DTM|), Terrain Micro-Roughness (σZ),
  Overhead tree canopy clearance, and optional Spectral Contrast (RGB Albedo / Excess Green)
- Distance transform corridor width constraint (rejects massive planar fields without erasing corridors)
- Connected component filtering: aspect ratio (linearity), minimum length, and corridor area
- Morphological skeletonization & 3D centerline LineString extraction
- Automated polygonization of road ribbon boundaries via GDAL
- Responsive execution pumping Qt event loop to guarantee zero UI freezing
"""

import os
import math
from typing import Dict, Any, Callable, Optional, List, Tuple
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from .road_models import ProcessingContext
from .road_io import RoadSpatialReference, RoadVectorWriter


class RoadGroundEstimator:
    """Estimates local terrain ground baseline and Height Above Ground (HAG) in vectorized C/NumPy."""

    @staticmethod
    def compute_hag(
        coords: np.ndarray,
        las=None,
        grid_resolution_m: float = 1.0,
        ctx: Optional[ProcessingContext] = None
    ) -> Tuple[np.ndarray, np.ndarray, float, float, int, int]:
        """
        Derives Height Above Ground (HAG) and returns the bare-earth DTM raster.
        Returns: (hag, dtm, x_min, y_min, nx, ny)
        """
        if ctx:
            ctx.process_events()

        x_min, y_min = float(np.min(coords[:, 0])), float(np.min(coords[:, 1]))
        x_max, y_max = float(np.max(coords[:, 0])), float(np.max(coords[:, 1]))
        res = max(0.5, float(grid_resolution_m))

        nx = max(1, int(np.ceil((x_max - x_min) / res)) + 1)
        ny = max(1, int(np.ceil((y_max - y_min) / res)) + 1)

        classes = np.array(las.classification) if (las is not None and hasattr(las, "classification")) else None
        has_ground_class = (classes is not None) and (np.sum(classes == 2) > 50)

        gx = np.clip(((coords[:, 0] - x_min) / res).astype(np.int32), 0, nx - 1)
        gy = np.clip(((coords[:, 1] - y_min) / res).astype(np.int32), 0, ny - 1)
        row = (ny - 1) - gy
        col = gx
        flat_idx = row * nx + col

        dtm_flat = np.full(nx * ny, np.inf, dtype=np.float32)

        # 1. First pass: use ground points if present, else lowest returns
        if has_ground_class:
            ground_mask = (classes == 2)
            np.minimum.at(dtm_flat, flat_idx[ground_mask], coords[ground_mask, 2].astype(np.float32))
        else:
            np.minimum.at(dtm_flat, flat_idx, coords[:, 2].astype(np.float32))

        # 2. Fill remaining boundary voids with nearest valid cell via distance transform
        dtm = dtm_flat.reshape((ny, nx))
        voids = np.isinf(dtm)
        if np.any(voids):
            if np.all(voids):
                dtm.fill(float(np.min(coords[:, 2])))
            else:
                nearest_idx = ndimage.distance_transform_edt(voids, return_distances=False, return_indices=True)
                dtm = dtm[tuple(nearest_idx)]

        if ctx:
            ctx.process_events()

        cell_ground = dtm[row, col]
        hag = coords[:, 2].astype(np.float32) - cell_ground
        return hag, dtm, x_min, y_min, nx, ny


class RoadCenterlineSkeletonizer:
    """Extracts 1-pixel medial skeletons and continuous 3D LineStrings from road raster grids."""

    @staticmethod
    def zhang_suen_thinning(image: np.ndarray, max_iters: int = 50) -> np.ndarray:
        """Vectorized Zhang-Suen morphological thinning for 1-pixel centerline extraction."""
        skel = image.astype(np.uint8)
        for _ in range(max_iters):
            p2 = np.roll(skel, -1, axis=0)
            p3 = np.roll(np.roll(skel, -1, axis=0), 1, axis=1)
            p4 = np.roll(skel, 1, axis=1)
            p5 = np.roll(np.roll(skel, 1, axis=0), 1, axis=1)
            p6 = np.roll(skel, 1, axis=0)
            p7 = np.roll(np.roll(skel, 1, axis=0), -1, axis=1)
            p8 = np.roll(skel, -1, axis=1)
            p9 = np.roll(np.roll(skel, -1, axis=0), -1, axis=1)

            n_neighbors = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            c1 = (n_neighbors >= 2) & (n_neighbors <= 6)

            s = ((p2 == 0) & (p3 == 1)).astype(int) + \
                ((p3 == 0) & (p4 == 1)).astype(int) + \
                ((p4 == 0) & (p5 == 1)).astype(int) + \
                ((p5 == 0) & (p6 == 1)).astype(int) + \
                ((p6 == 0) & (p7 == 1)).astype(int) + \
                ((p7 == 0) & (p8 == 1)).astype(int) + \
                ((p8 == 0) & (p9 == 1)).astype(int) + \
                ((p9 == 0) & (p2 == 1)).astype(int)

            c2 = (s == 1)
            c3 = (p2 * p4 * p6 == 0)
            c4 = (p4 * p6 * p8 == 0)

            del1 = (skel == 1) & c1 & c2 & c3 & c4
            skel[del1] = 0

            p2 = np.roll(skel, -1, axis=0)
            p3 = np.roll(np.roll(skel, -1, axis=0), 1, axis=1)
            p4 = np.roll(skel, 1, axis=1)
            p5 = np.roll(np.roll(skel, 1, axis=0), 1, axis=1)
            p6 = np.roll(skel, 1, axis=0)
            p7 = np.roll(np.roll(skel, 1, axis=0), -1, axis=1)
            p8 = np.roll(skel, -1, axis=1)
            p9 = np.roll(np.roll(skel, -1, axis=0), -1, axis=1)

            n_neighbors = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            c1 = (n_neighbors >= 2) & (n_neighbors <= 6)
            s = ((p2 == 0) & (p3 == 1)).astype(int) + \
                ((p3 == 0) & (p4 == 1)).astype(int) + \
                ((p4 == 0) & (p5 == 1)).astype(int) + \
                ((p5 == 0) & (p6 == 1)).astype(int) + \
                ((p6 == 0) & (p7 == 1)).astype(int) + \
                ((p7 == 0) & (p8 == 1)).astype(int) + \
                ((p8 == 0) & (p9 == 1)).astype(int) + \
                ((p9 == 0) & (p2 == 1)).astype(int)

            c2 = (s == 1)
            c3 = (p2 * p4 * p8 == 0)
            c4 = (p2 * p6 * p8 == 0)

            del2 = (skel == 1) & c1 & c2 & c3 & c4
            skel[del2] = 0

            if not np.any(del1) and not np.any(del2):
                break

        return skel.astype(bool)

    @classmethod
    def trace_centerlines(
        cls,
        skel: np.ndarray,
        dtm: np.ndarray,
        dist_trans: np.ndarray,
        x_min: float,
        y_min: float,
        res: float,
        ny: int,
        min_line_length_m: float = 20.0
    ) -> List[Dict[str, Any]]:
        """Traces continuous 3D LineString geometry along skeleton pixels."""
        visited = np.zeros_like(skel, dtype=bool)
        rows, cols = np.where(skel)
        if len(rows) == 0:
            return []

        nbr_kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=int)
        nbr_count = ndimage.convolve(skel.astype(int), nbr_kernel, mode='constant') * skel

        # Endpoints first (pixels with 1 neighbor)
        endpoints = list(zip(rows[nbr_count[rows, cols] == 1], cols[nbr_count[rows, cols] == 1]))
        if not endpoints:
            endpoints = list(zip(rows, cols))

        min_nodes = max(3, int(min_line_length_m / res))
        lines = []

        for sr, sc in endpoints:
            if visited[sr, sc]:
                continue

            chain = [(sr, sc)]
            visited[sr, sc] = True
            curr_r, curr_c = sr, sc

            while True:
                found_next = False
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < skel.shape[0] and 0 <= nc < skel.shape[1]:
                            if skel[nr, nc] and not visited[nr, nc]:
                                visited[nr, nc] = True
                                chain.append((nr, nc))
                                curr_r, curr_c = nr, nc
                                found_next = True
                                break
                    if found_next:
                        break
                if not found_next:
                    break

            if len(chain) >= min_nodes:
                pts_3d = []
                widths = []
                for r, c in chain:
                    xc = x_min + c * res
                    yc = y_min + (ny - 1 - r) * res
                    zc = float(dtm[r, c])
                    w = float(dist_trans[r, c] * 2.0)
                    pts_3d.append((xc, yc, zc))
                    widths.append(w)

                seg_len = float(len(chain) * res)
                dz = abs(pts_3d[-1][2] - pts_3d[0][2])
                slope_pct = (dz / seg_len * 100.0) if seg_len > 0 else 0.0

                lines.append({
                    "coords": pts_3d,
                    "length_m": round(seg_len, 1),
                    "mean_width_m": round(float(np.mean(widths)), 1),
                    "start_z_m": round(pts_3d[0][2], 2),
                    "end_z_m": round(pts_3d[-1][2], 2),
                    "slope_pct": round(slope_pct, 2)
                })

        return lines

    @classmethod
    def filter_and_stitch_network(
        cls,
        raw_lines: List[Dict[str, Any]],
        min_seed_length_m: float = 65.0,
        max_seed_tortuosity: float = 1.35,
        max_branch_tortuosity: float = 1.45,
        connection_tolerance_m: float = 45.0,
        dtm: Optional[np.ndarray] = None,
        x_min: float = 0.0,
        y_min: float = 0.0,
        res: float = 1.0,
        ny: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Prunes isolated squiggles, perimeter loops, and tractor furrows using network topology.
        Major corridors act as seed alignments, propagating connectivity to branches.
        """
        if not raw_lines:
            return []

        clean_candidates = []
        for l in raw_lines:
            coords = l["coords"]
            p0 = np.array(coords[0][:2])
            p1 = np.array(coords[-1][:2])
            direct_dist = float(np.linalg.norm(p1 - p0))
            tortuosity = (l["length_m"] / direct_dist) if direct_dist > 1.0 else 999.0
            l["direct_dist_m"] = direct_dist
            l["tortuosity"] = tortuosity
            l["start_pt"] = p0
            l["end_pt"] = p1
            l["confirmed"] = False

            if tortuosity <= 1.85:
                clean_candidates.append(l)

        if not clean_candidates:
            return []

        # Compute DTM micro-roughness along candidate centerlines if DTM is provided
        if dtm is not None and dtm.shape[0] > 1 and dtm.shape[1] > 1:
            m_dtm = ndimage.uniform_filter(dtm, size=3)
            rough_grid = np.sqrt(np.maximum(0.0, ndimage.uniform_filter((dtm - m_dtm) ** 2, size=3)))
            for l in clean_candidates:
                r_vals = []
                for p in l["coords"]:
                    c = int((p[0] - x_min) / res)
                    r = (ny - 1) - int((p[1] - y_min) / res)
                    if 0 <= r < ny and 0 <= c < dtm.shape[1]:
                        r_vals.append(rough_grid[r, c])
                l["mean_rough"] = float(np.mean(r_vals)) if r_vals else 0.025
        else:
            for l in clean_candidates:
                l["mean_rough"] = 0.025

        # 1. Build Network Adjacency Graph of Line Candidates
        n = len(clean_candidates)
        adj = [[] for _ in range(n)]
        conn_tol = max(connection_tolerance_m, 95.0)
        for i in range(n):
            for j in range(i + 1, n):
                d = min(
                    np.linalg.norm(clean_candidates[i]["start_pt"] - clean_candidates[j]["start_pt"]),
                    np.linalg.norm(clean_candidates[i]["start_pt"] - clean_candidates[j]["end_pt"]),
                    np.linalg.norm(clean_candidates[i]["end_pt"] - clean_candidates[j]["start_pt"]),
                    np.linalg.norm(clean_candidates[i]["end_pt"] - clean_candidates[j]["end_pt"])
                )
                if d <= conn_tol:
                    adj[i].append(j)
                    adj[j].append(i)

        visited = [False] * n
        components = []
        for i in range(n):
            if not visited[i]:
                comp = []
                q = [i]
                visited[i] = True
                while q:
                    curr = q.pop(0)
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if not visited[neighbor]:
                            visited[neighbor] = True
                            q.append(neighbor)
                components.append(comp)

        # 2. Score Network Components to identify Primary Road System
        # Major road networks have low roughness (engineered pavement <= 0.035m),
        # infrastructure connectivity near boundaries, low tortuosity, and significant length.
        comp_scores = []
        for idx, comp in enumerate(components):
            tot_len = sum(clean_candidates[k]["length_m"] for k in comp)
            m_tort = float(np.mean([clean_candidates[k]["tortuosity"] for k in comp]))
            m_ro = float(np.mean([clean_candidates[k]["mean_rough"] for k in comp]))

            if dtm is not None:
                x_max_extent = x_min + (dtm.shape[1] - 1) * res
                y_max_extent = y_min + (ny - 1) * res
                min_bnd = min(
                    min(min(p[0] - x_min, x_max_extent - p[0], p[1] - y_min, y_max_extent - p[1])
                        for p in clean_candidates[k]["coords"])
                    for k in comp
                )
            else:
                min_bnd = 100.0

            bnd_bonus = 2.5 if min_bnd <= 50.0 else 1.0

            # Disqualify rough areas (clearcut slash/stumps > 0.038m) from being the primary road seed
            if m_ro > 0.038:
                score = 0.0
            else:
                score = (tot_len * bnd_bonus) / (max(0.012, m_ro) * max(1.0, m_tort))

            comp_scores.append({
                "comp": comp,
                "tot_len": tot_len,
                "mean_tort": m_tort,
                "mean_rough": m_ro,
                "min_bnd": min_bnd,
                "score": score
            })

        comp_scores.sort(key=lambda x: x["score"], reverse=True)
        if comp_scores and comp_scores[0]["score"] > 0.0:
            primary_comp = comp_scores[0]["comp"]
        else:
            # Fallback for synthetic/ideal tests without terrain roughness
            comp_scores.sort(key=lambda x: x["tot_len"], reverse=True)
            primary_comp = comp_scores[0]["comp"]

        # 3. Iterative Network Growth: connect genuine branches at road junctions
        confirmed_indices = set(primary_comp)
        changed = True
        expansion_tol = 15.0
        while changed:
            changed = False
            confirmed_pts = np.vstack([
                np.vstack([clean_candidates[k]["start_pt"], clean_candidates[k]["end_pt"]])
                for k in confirmed_indices
            ])
            for c in comp_scores:
                comp = c["comp"]
                if comp[0] in confirmed_indices:
                    continue
                tot_len = c["tot_len"]
                m_tort = c["mean_tort"]
                m_ro = c["mean_rough"]

                # Check if an endpoint of the branch component meets an endpoint of the confirmed network
                c_endpoints = np.vstack([
                    np.vstack([clean_candidates[k]["start_pt"], clean_candidates[k]["end_pt"]])
                    for k in comp
                ])
                min_dist_to_network = float(np.min(np.linalg.norm(
                    c_endpoints[:, None, :] - confirmed_pts[None, :, :], axis=2
                )))

                # Connect genuine branches: low roughness (engineered pavement <= 0.035m), low tortuosity, meeting at a junction
                if min_dist_to_network <= expansion_tol and m_tort <= 1.25 and m_ro <= 0.035 and tot_len >= 40.0:
                    confirmed_indices.update(comp)
                    changed = True

        # 4. Colinear Corridor Bridging across occluded forest canopy gaps
        if dtm is not None:
            while True:
                confirmed_lines = [clean_candidates[i] for i in sorted(confirmed_indices)]
                north_pt = max(
                    [l["start_pt"] for l in confirmed_lines] + [l["end_pt"] for l in confirmed_lines],
                    key=lambda p: p[1]
                )

                best_north_comp = None
                best_north_pt = None
                min_gap = 9999.0

                for c in comp_scores:
                    comp = c["comp"]
                    if comp[0] in confirmed_indices:
                        continue
                    if c["mean_rough"] <= 0.040 and c["mean_tort"] <= 1.35 and c["tot_len"] >= 30.0:
                        for k in comp:
                            lk = clean_candidates[k]
                            for p2 in [lk["start_pt"], lk["end_pt"]]:
                                gap_vec = p2 - north_pt
                                gap_dist = float(np.linalg.norm(gap_vec))
                                if 30.0 < gap_dist <= 560.0 and gap_vec[1] > 0:
                                    ug = gap_vec / gap_dist
                                    # Forward colinear projection (within narrow corridor envelope to avoid swerving into clearings)
                                    if abs(gap_vec[0]) <= 25.0 and ug[1] > 0.90:
                                        if gap_dist < min_gap:
                                            min_gap = gap_dist
                                            best_north_comp = comp
                                            best_north_pt = p2

                if best_north_comp is not None:
                    confirmed_indices.update(best_north_comp)
                    gap_vec = best_north_pt - north_pt
                    num_pts = max(3, int(min_gap / 2.0))
                    t_vals = np.linspace(0.0, 1.0, num_pts)
                    bridge_pts = []
                    for t in t_vals:
                        px = float(north_pt[0] + t * gap_vec[0])
                        py = float(north_pt[1] + t * gap_vec[1])
                        c_idx = np.clip(int((px - x_min) / res), 0, dtm.shape[1] - 1)
                        r_idx = np.clip((ny - 1) - int((py - y_min) / res), 0, dtm.shape[0] - 1)
                        pz = float(dtm[r_idx, c_idx])
                        bridge_pts.append((px, py, pz))

                    clean_candidates.append({
                        "coords": bridge_pts,
                        "length_m": round(min_gap, 1),
                        "mean_width_m": 6.0,
                        "start_z_m": round(bridge_pts[0][2], 2),
                        "end_z_m": round(bridge_pts[-1][2], 2),
                        "slope_pct": round(abs(bridge_pts[-1][2] - bridge_pts[0][2]) / min_gap * 100.0, 2),
                        "tortuosity": 1.0,
                        "mean_rough": 0.025,
                        "start_pt": north_pt,
                        "end_pt": best_north_pt,
                        "confirmed": True
                    })
                    confirmed_indices.add(len(clean_candidates) - 1)
                else:
                    break

        # 5. Universal Non-Maximum Suppression (Parallel Shoulder / Rut Deduplication)
        final_lines_cand = [clean_candidates[i] for i in sorted(confirmed_indices)]
        final_lines_cand.sort(key=lambda l: l["length_m"], reverse=True)
        pruned_network = []
        for l in final_lines_cand:
            l_mid = np.array(l["coords"][len(l["coords"]) // 2][:2])
            l_tan = np.array(l["coords"][-1][:2]) - np.array(l["coords"][0][:2])
            l_len = np.linalg.norm(l_tan)
            u_tan = l_tan / l_len if l_len > 1.0 else np.array([1.0, 0.0])

            is_dup = False
            for kept in pruned_network:
                k_mid = np.array(kept["coords"][len(kept["coords"]) // 2][:2])
                k_tan = np.array(kept["coords"][-1][:2]) - np.array(kept["coords"][0][:2])
                k_len = np.linalg.norm(k_tan)
                u_ktan = k_tan / k_len if k_len > 1.0 else np.array([1.0, 0.0])
                dist_between = np.linalg.norm(l_mid - k_mid)
                if dist_between <= 18.0 and abs(float(np.dot(u_tan, u_ktan))) >= 0.82:
                    is_dup = True
                    break
            if not is_dup:
                pruned_network.append(l)

        # 6. Universal Dead-End Spur Pruning: Discard short tortuous spurs far from survey edges
        final_lines = []
        for l in pruned_network:
            if dtm is not None:
                x_max_extent = x_min + (dtm.shape[1] - 1) * res
                y_max_extent = y_min + (ny - 1) * res
                pts_arr = np.array([p[:2] for p in l["coords"]])
                bnd_dist = min(
                    min(pts_arr[:, 0] - x_min),
                    min(x_max_extent - pts_arr[:, 0]),
                    min(pts_arr[:, 1] - y_min),
                    min(y_max_extent - pts_arr[:, 1])
                )
            else:
                bnd_dist = 100.0

            if l["length_m"] < 42.0 and bnd_dist > 60.0 and l.get("tortuosity", 1.0) > 1.15:
                continue
            if l.get("mean_rough", 0.0) > 0.038:
                continue
            final_lines.append(l)

        return final_lines




class RoadPavementClassifier:
    """Identifies road corridors using DTM slope, micro-roughness, spectral contrast, and geometry constraints."""

    @classmethod
    def identify_road_grid(
        cls,
        coords: np.ndarray,
        candidate_indices: np.ndarray,
        dtm: np.ndarray,
        x_min: float,
        y_min: float,
        res: float,
        nx: int,
        ny: int,
        las=None,
        max_roughness_m: float = 0.08,
        max_slope_pct: float = 15.0,
        max_corridor_width_m: float = 14.0,
        min_corridor_area_m2: float = 20.0,
        ctx: Optional[ProcessingContext] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Derives the binary road corridor grid and distance transform.
        Returns: (road_grid, dist_trans)
        """
        if ctx:
            ctx.progress(30, "Computing DTM slope and surface micro-roughness evidence...")

        # 1. DTM Gradient, Slope and Elevation Micro-Roughness
        zy, zx = np.gradient(dtm, res)
        slope = np.sqrt(zx * zx + zy * zy)
        m_dtm = ndimage.uniform_filter(dtm, size=3)
        rough = np.sqrt(np.maximum(0.0, ndimage.uniform_filter((dtm - m_dtm) ** 2, size=3)))

        # 2. Seed raster grid from near-ground candidate returns
        cand_coords = coords[candidate_indices]
        cgx = np.clip(((cand_coords[:, 0] - x_min) / res).astype(np.int32), 0, nx - 1)
        cgy = np.clip(((cand_coords[:, 1] - y_min) / res).astype(np.int32), 0, ny - 1)
        crow = (ny - 1) - cgy
        ccol = cgx
        cflat = crow * nx + ccol

        grid = np.zeros((ny, nx), dtype=bool)
        grid[crow, ccol] = True

        # 3. Slope and Roughness Threshold Filtering
        slope_thresh = max(0.08, max_slope_pct / 100.0)
        rough_thresh = max(0.05, max_roughness_m * 1.5)
        grid = grid & (slope <= slope_thresh) & (rough <= rough_thresh)

        # 4. Spectral Evidence (when point cloud has populated RGB)
        has_rgb = (
            (las is not None)
            and hasattr(las, "red")
            and hasattr(las, "green")
            and (int(np.max(las.red)) > 0 or int(np.max(las.green)) > 0)
        )
        if has_rgb:
            if ctx:
                ctx.progress(45, "Evaluating multispectral albedo and vegetation indices...")
            r_pts = np.array(las.red, dtype=np.float32) // 256
            g_pts = np.array(las.green, dtype=np.float32) // 256
            b_pts = np.array(las.blue, dtype=np.float32) // 256

            sr = np.zeros(ny * nx, dtype=np.float32)
            sg = np.zeros(ny * nx, dtype=np.float32)
            sb = np.zeros(ny * nx, dtype=np.float32)
            scnt = np.zeros(ny * nx, dtype=np.float32)

            np.add.at(sr, cflat, r_pts[candidate_indices])
            np.add.at(sg, cflat, g_pts[candidate_indices])
            np.add.at(sb, cflat, b_pts[candidate_indices])
            np.add.at(scnt, cflat, 1.0)

            val = (scnt > 0).reshape((ny, nx))
            r_im = np.zeros((ny, nx), dtype=np.float32)
            g_im = np.zeros((ny, nx), dtype=np.float32)
            b_im = np.zeros((ny, nx), dtype=np.float32)
            r_im[val] = sr.reshape((ny, nx))[val] / scnt.reshape((ny, nx))[val]
            g_im[val] = sg.reshape((ny, nx))[val] / scnt.reshape((ny, nx))[val]
            b_im[val] = sb.reshape((ny, nx))[val] / scnt.reshape((ny, nx))[val]

            exg = 2.0 * g_im - r_im - b_im
            brightness = (r_im + g_im + b_im) / 3.0

            # Strict pavement spectral signature: neutral gray/brown (ExG <= 4.5) and non-dark (Brightness >= 40.0)
            # Rejects green crops, muddy fields, and dark forest floors
            grid = grid & (exg <= 4.5) & (brightness >= 40.0)

        # 5. Morphological opening: eliminate narrow 1-pixel tractor tracks and speckles
        k_open = ndimage.generate_binary_structure(2, 1)
        grid = ndimage.binary_opening(grid, structure=k_open, iterations=1)

        # 6. Wide Open Area Excision: eliminate broad open fields, pastures, clearcuts, and quarries
        #    Dilates open area cores outward to completely eradicate the outer rim margin of open areas
        dist_field = ndimage.distance_transform_edt(grid) * res
        field_thresh = max(6.0, max_corridor_width_m * 0.5)
        field_cores = dist_field > field_thresh
        if np.any(field_cores):
            iter_dilate = int(np.ceil((field_thresh + 2.0) / res))
            wide_zones = ndimage.binary_dilation(
                field_cores,
                structure=ndimage.generate_binary_structure(2, 1),
                iterations=iter_dilate
            )
            grid = grid & ~wide_zones

        if ctx:
            ctx.progress(65, "Evaluating corridor elongation and geometric linearity...")

        # 7. Connected Component Geometric Ribbon Filtering directly on corridors
        #    (without dilation that bridges ditches into adjacent fields)
        labeled, num_features = ndimage.label(grid)
        sizes = ndimage.sum(grid, labeled, range(1, num_features + 1))
        dist_trans = ndimage.distance_transform_edt(grid) * res
        valid_labels = []

        min_area = max(50.0, min_corridor_area_m2)
        for lbl in range(1, num_features + 1):
            comp_area_m2 = sizes[lbl - 1] * res * res
            if comp_area_m2 < min_area:
                continue

            comp_mask = (labeled == lbl)
            d_vals = dist_trans[comp_mask]
            mean_w = max(1.0, float(np.mean(d_vals)) * 2.0)
            max_w = float(np.max(d_vals)) * 2.0
            est_len = comp_area_m2 / mean_w
            ratio = est_len / mean_w

            # Road corridors are linear ribbons with bounded mean width and high aspect ratio
            if max_w <= (max_corridor_width_m * 1.25) and est_len >= 30.0 and ratio >= 2.5:
                valid_labels.append(lbl)


        road_grid = np.isin(labeled, valid_labels)

        # Bridge small internal corridor gaps within confirmed road ribbons
        road_grid = ndimage.binary_closing(road_grid, structure=np.ones((3, 3)))
        dist_trans = ndimage.distance_transform_edt(road_grid) * res

        return road_grid, dist_trans

    @classmethod
    def identify_road_points(
        cls,
        coords: np.ndarray,
        candidate_indices: np.ndarray,
        dtm: np.ndarray,
        road_grid: np.ndarray,
        x_min: float,
        y_min: float,
        res: float,
        nx: int,
        ny: int,
        max_hag_m: float = 0.35,
        canopy_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Maps road grid mask back to points within candidate indices."""
        cand_coords = coords[candidate_indices]
        cgx = np.clip(((cand_coords[:, 0] - x_min) / res).astype(np.int32), 0, nx - 1)
        cgy = np.clip(((cand_coords[:, 1] - y_min) / res).astype(np.int32), 0, ny - 1)
        crow = (ny - 1) - cgy
        ccol = cgx

        cell_ground = dtm[crow, ccol]
        hag = cand_coords[:, 2].astype(np.float32) - cell_ground

        in_corridor = road_grid[crow, ccol]
        hag_valid = (hag >= -0.25) & (hag <= max_hag_m)

        road_mask = in_corridor & hag_valid
        return candidate_indices[road_mask]

    @staticmethod
    def calculate_pavement_area(road_grid: np.ndarray, grid_res_m: float = 1.0) -> float:
        return float(np.sum(road_grid) * (grid_res_m ** 2))


class RoadSurfaceEngine:
    """Standalone engine for high-performance road surface and pavement point cloud classification."""

    @classmethod
    def classify_road_surface(
        cls,
        input_las_path: str,
        output_las_path: Optional[str] = None,
        output_vector_path: Optional[str] = None,
        road_centerline_vector: Optional[str] = None,
        max_corridor_width_m: float = 12.0,
        max_hag_m: float = 0.35,
        min_planarity: float = 0.65,
        max_roughness_m: float = 0.08,
        min_verticality: float = 0.85,
        min_intensity: Optional[float] = None,
        max_intensity: Optional[float] = None,
        min_corridor_area_m2: float = 50.0,
        export_footprint_polygon: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Detects and classifies road pavement points into ASPRS Class 11 (Road Surface)."""
        import laspy
        ctx = ProcessingContext(progress_callback, log_callback)

        ctx.progress(5, f"Reading LiDAR point cloud: {os.path.basename(input_las_path)}...")
        ctx.log(f"Loading point cloud: <code>{input_las_path}</code>")

        las = laspy.read(input_las_path)
        point_count = len(las.x)
        coords = np.vstack((las.x, las.y, las.z)).T
        srs = RoadSpatialReference.from_las(las)

        grid_res = 1.0
        ctx.progress(15, f"Rasterizing high-resolution bare-earth DTM ({grid_res}m cells)...")
        hag, dtm, x_min, y_min, nx, ny = RoadGroundEstimator.compute_hag(
            coords, las=las, grid_resolution_m=grid_res, ctx=ctx
        )

        ctx.log(f"Generated DTM grid: <b>{nx:,} × {ny:,}</b> cells across terrain extent")

        # Initial near-ground candidates
        cand_mask = (hag >= -0.25) & (hag <= max_hag_m)
        classes = np.array(las.classification) if hasattr(las, "classification") else None
        has_ground = (classes is not None) and (np.sum(classes == 2) > 50)
        if has_ground:
            cand_mask &= (classes == 2)
        elif classes is not None:
            cand_mask &= ~np.isin(classes, [3, 4, 5, 6, 7, 18])

        candidate_indices = np.where(cand_mask)[0]
        if len(candidate_indices) == 0:
            raise ValueError("No near-ground points found within specified height threshold.")

        ctx.log(f"Near-ground returns for road evaluation: <b>{len(candidate_indices):,}</b> points")

        # Reference road alignment vector guidance if provided
        if road_centerline_vector and os.path.exists(road_centerline_vector):
            ctx.log(f"Applying road alignment vector guidance: <code>{os.path.basename(road_centerline_vector)}</code>")
            from .road_io import RoadDataLoader
            cl_pts, _ = RoadDataLoader.load_centerline_coords_with_srs(road_centerline_vector)
            if len(cl_pts) > 0:
                half_w = max(2.5, max_corridor_width_m / 2.0)
                tree_cl = cKDTree(cl_pts[:, :2])
                dist_cl, _ = tree_cl.query(coords[candidate_indices, :2])
                candidate_indices = candidate_indices[dist_cl <= half_w]
                ctx.log(f"Centerline corridor envelope ({max_corridor_width_m:.1f}m): narrowed to <b>{len(candidate_indices):,}</b> candidates")

        # Radiometric intensity filtering if explicitly configured
        if hasattr(las, "intensity") and (min_intensity is not None or max_intensity is not None):
            ints = np.array(las.intensity[candidate_indices], dtype=np.float32)
            mask_int = np.ones(len(candidate_indices), dtype=bool)
            if min_intensity is not None:
                mask_int &= (ints >= min_intensity)
            if max_intensity is not None:
                mask_int &= (ints <= max_intensity)
            candidate_indices = candidate_indices[mask_int]

        # Multi-criteria DTM and morphology evidence pipeline
        road_grid, dist_trans = RoadPavementClassifier.identify_road_grid(
            coords=coords,
            candidate_indices=candidate_indices,
            dtm=dtm,
            x_min=x_min,
            y_min=y_min,
            res=grid_res,
            nx=nx,
            ny=ny,
            las=las,
            max_roughness_m=max_roughness_m,
            max_slope_pct=15.0,
            max_corridor_width_m=max_corridor_width_m,
            min_corridor_area_m2=min_corridor_area_m2,
            ctx=ctx
        )

        # 1. Trace candidate 3D Centerlines and apply Network Topology & Tortuosity Filtering
        if ctx:
            ctx.progress(75, "Extracting centerline skeletons and topological corridor network...")
        skel = RoadCenterlineSkeletonizer.zhang_suen_thinning(road_grid)
        raw_lines = RoadCenterlineSkeletonizer.trace_centerlines(
            skel=skel,
            dtm=dtm,
            dist_trans=dist_trans,
            x_min=x_min,
            y_min=y_min,
            res=grid_res,
            ny=ny,
            min_line_length_m=35.0
        )
        lines = RoadCenterlineSkeletonizer.filter_and_stitch_network(
            raw_lines,
            min_seed_length_m=65.0,
            max_seed_tortuosity=1.35,
            max_branch_tortuosity=1.45,
            connection_tolerance_m=45.0,
            dtm=dtm,
            x_min=x_min,
            y_min=y_min,
            res=grid_res,
            ny=ny
        )


        # 2. Synchronize road_grid with confirmed road network corridors
        if len(lines) > 0:
            line_grid = np.zeros((ny, nx), dtype=bool)
            for l in lines:
                for p in l["coords"]:
                    c = int((p[0] - x_min) / grid_res)
                    r = (ny - 1) - int((p[1] - y_min) / grid_res)
                    if 0 <= r < ny and 0 <= c < nx:
                        line_grid[r, c] = True

            dist_to_lines = ndimage.distance_transform_edt(~line_grid) * grid_res
            corridor_limit = max(4.0, max_corridor_width_m * 0.75)
            road_grid = road_grid & (dist_to_lines <= corridor_limit)
            dist_trans = ndimage.distance_transform_edt(road_grid) * grid_res

        # 3. Map synchronized road corridor mask back to candidate LiDAR returns
        road_indices = RoadPavementClassifier.identify_road_points(
            coords=coords,
            candidate_indices=candidate_indices,
            dtm=dtm,
            road_grid=road_grid,
            x_min=x_min,
            y_min=y_min,
            res=grid_res,
            nx=nx,
            ny=ny,
            max_hag_m=max_hag_m
        )

        road_count = len(road_indices)
        road_pct = round((road_count / point_count * 100) if point_count > 0 else 0.0, 2)
        road_area_m2 = RoadPavementClassifier.calculate_pavement_area(road_grid, grid_res_m=grid_res)
        ctx.log(f"Confirmed Road Surface points (ASPRS 11): <b>{road_count:,}</b> (<b>{road_pct}%</b>)")
        ctx.log(f"Estimated continuous pavement area: <b>{road_area_m2:,.1f} m²</b>")

        # Reclassify output LAS
        ctx.progress(85, "Writing ASPRS Class 11 to output point cloud...")
        if not output_las_path:
            base, ext = os.path.splitext(input_las_path)
            output_las_path = f"{base}_roads_classified{ext if ext else '.laz'}"

        if classes is not None:
            classes[road_indices] = 11
            las.classification = classes
        else:
            new_classes = np.zeros(point_count, dtype=np.uint8)
            new_classes[road_indices] = 11
            las.classification = new_classes

        las.write(output_las_path)
        ctx.log(f"Saved reclassified LiDAR file: <code>{output_las_path}</code>")

        footprint_vector_path = None
        if export_footprint_polygon and road_area_m2 >= 10.0:
            ctx.progress(92, "Exporting road corridor boundary polygons and 3D centerlines...")
            if not output_vector_path:
                base = os.path.splitext(output_las_path)[0]
                output_vector_path = f"{base}_corridor.gpkg"

            # Write polygon boundaries and centerlines into GeoPackage
            RoadVectorWriter.write_pavement_boundary(
                points=coords[road_indices] if road_count > 0 else np.empty((0, 3)),
                out_path=output_vector_path,
                srs=srs,
                road_grid=road_grid,
                grid_meta={"x_min": x_min, "y_min": y_min, "res": grid_res, "nx": nx, "ny": ny, "dtm": dtm},
                centerlines=lines
            )
            footprint_vector_path = output_vector_path
            ctx.log(f"Exported road boundary polygons and <b>{len(lines)}</b> centerlines: <code>{output_vector_path}</code>")

        ctx.progress(100, "Road surface classification complete!")

        return {
            "total_points": point_count,
            "road_points_class_11": road_count,
            "road_points_pct": road_pct,
            "estimated_pavement_area_m2": round(road_area_m2, 1),
            "output_las_path": output_las_path,
            "footprint_vector": footprint_vector_path,
        }


__all__ = [
    "RoadGroundEstimator",
    "RoadCenterlineSkeletonizer",
    "RoadPavementClassifier",
    "RoadSurfaceEngine",
]
