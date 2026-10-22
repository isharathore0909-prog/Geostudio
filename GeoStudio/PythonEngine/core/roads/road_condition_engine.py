# -*- coding: utf-8 -*-
"""
GeoStudio - Road Condition, Roughness & Overhead Vehicle Clearance Engine
Conducts transportation engineering audits along road corridors:
- Longitudinal slope / gradient profile and design standard violation checks
- Pavement roughness (IRI proxy mm/m) and localized depression / pothole detection
- 3D overhead vehicle clearance envelope (4.8m - 5.0m standard) intrusion scanning
  (low-hanging tree branches, overhead wires, and structural obstructions)
- Vector hazard points (GPKG) and structured JSON audit report generation
"""

import os
import json
import time
from dataclasses import asdict
from typing import Dict, Any, Callable, Optional, List, Tuple
import numpy as np
from scipy.spatial import cKDTree

from .road_models import ProcessingContext, CorridorHazard
from .road_io import RoadSpatialReference, RoadVectorWriter, RoadDataLoader


class RoadCorridorAuditor:
    """Audits road gradient profiles, pavement roughness, depressions, and overhead clearance envelopes."""

    @classmethod
    def audit_corridor(
        cls,
        cl_pts: np.ndarray,
        coords: np.ndarray,
        corridor_width_m: float = 8.0,
        max_design_grade_pct: float = 8.0,
        critical_grade_pct: float = 12.0,
        clearance_height_m: float = 4.80,
        critical_clearance_m: float = 4.00,
        ctx: Optional[ProcessingContext] = None
    ) -> Dict[str, Any]:
        diffs = np.diff(cl_pts, axis=0)
        seg_dists = np.sqrt(np.sum(diffs[:, :2] ** 2, axis=1))
        grades = np.where(seg_dists > 0.01, (diffs[:, 2] / seg_dists) * 100.0, 0.0)
        total_len = float(np.sum(seg_dists))
        cum_dists = np.insert(np.cumsum(seg_dists), 0, 0.0)

        hazards: List[CorridorHazard] = []
        steep_count, crit_grade_count = cls._evaluate_grades(
            cl_pts, grades, cum_dists, max_design_grade_pct, critical_grade_pct, hazards
        )

        half_w = corridor_width_m / 2.0
        # Fast 2D bounding box pre-filter
        x_min = float(np.min(cl_pts[:, 0])) - (half_w + 2.0)
        x_max = float(np.max(cl_pts[:, 0])) + (half_w + 2.0)
        y_min = float(np.min(cl_pts[:, 1])) - (half_w + 2.0)
        y_max = float(np.max(cl_pts[:, 1])) + (half_w + 2.0)
        bbox_mask = (coords[:, 0] >= x_min) & (coords[:, 0] <= x_max) & (coords[:, 1] >= y_min) & (coords[:, 1] <= y_max)
        bbox_indices = np.where(bbox_mask)[0]

        cl_tree_2d = cKDTree(cl_pts[:, :2])
        if len(bbox_indices) > 0:
            dists_to_cl, nearest_sub_idx = cl_tree_2d.query(coords[bbox_indices, :2], distance_upper_bound=half_w)
            in_corr = (dists_to_cl <= half_w)
            corr_indices = bbox_indices[in_corr]
            nearest_cl_idx = np.zeros(len(coords), dtype=np.int32)
            nearest_cl_idx[corr_indices] = nearest_sub_idx[in_corr]
        else:
            corr_indices = np.array([], dtype=np.int64)
            nearest_cl_idx = np.zeros(len(coords), dtype=np.int32)

        potholes_count = 0
        crit_clear_count = 0
        warn_clear_count = 0
        iri_proxy = 0.0

        if len(corr_indices) > 0:
            corr_pts = coords[corr_indices]
            corr_cl_idx = nearest_cl_idx[corr_indices]
            road_z = cl_pts[corr_cl_idx, 2]
            vert_clearance = corr_pts[:, 2] - road_z

            potholes_count, iri_proxy = cls._evaluate_pavement_surface(
                corr_pts, road_z, vert_clearance, corr_cl_idx, cum_dists, hazards
            )

            crit_clear_count, warn_clear_count = cls._evaluate_overhead_clearance(
                corr_pts, vert_clearance, corr_cl_idx, cum_dists,
                clearance_height_m, critical_clearance_m, hazards
            )

        return {
            "total_corridor_length_m": round(total_len, 1),
            "max_grade_pct": round(float(np.max(np.abs(grades))), 2) if len(grades) > 0 else 0.0,
            "mean_grade_pct": round(float(np.mean(np.abs(grades))), 2) if len(grades) > 0 else 0.0,
            "steep_grade_count": steep_count,
            "critical_grade_count": crit_grade_count,
            "potholes_count": potholes_count,
            "critical_clearance_count": crit_clear_count,
            "warning_clearance_count": warn_clear_count,
            "total_hazards_count": len(hazards),
            "iri_proxy_m_km": iri_proxy,
            "hazards": hazards
        }

    @staticmethod
    def _evaluate_grades(
        cl_pts: np.ndarray,
        grades: np.ndarray,
        cum_dists: np.ndarray,
        max_design_grade: float,
        critical_grade: float,
        hazards: List[CorridorHazard]
    ) -> Tuple[int, int]:
        steep_cnt = 0
        crit_cnt = 0
        for i, grade in enumerate(grades):
            abs_g = abs(float(grade))
            mid_pt = (cl_pts[i] + cl_pts[i + 1]) / 2.0
            mid_chainage = (cum_dists[i] + cum_dists[i + 1]) / 2.0

            if abs_g >= critical_grade:
                crit_cnt += 1
                hazards.append(CorridorHazard(
                    hazard_type="Steep Grade Violation (Critical)",
                    severity="CRITICAL",
                    chainage_m=round(mid_chainage, 1),
                    x=float(mid_pt[0]), y=float(mid_pt[1]), z=float(mid_pt[2]),
                    metric_val=round(abs_g, 1),
                    description=f"Longitudinal slope {abs_g:.1f}% exceeds critical design limit {critical_grade:.1f}%"
                ))
            elif abs_g >= max_design_grade:
                steep_cnt += 1
                hazards.append(CorridorHazard(
                    hazard_type="Steep Grade Warning",
                    severity="WARNING",
                    chainage_m=round(mid_chainage, 1),
                    x=float(mid_pt[0]), y=float(mid_pt[1]), z=float(mid_pt[2]),
                    metric_val=round(abs_g, 1),
                    description=f"Longitudinal slope {abs_g:.1f}% exceeds design threshold {max_design_grade:.1f}%"
                ))
        return steep_cnt, crit_cnt

    @staticmethod
    def _evaluate_pavement_surface(
        corr_pts: np.ndarray,
        road_z: np.ndarray,
        vert_clearance: np.ndarray,
        corr_cl_idx: np.ndarray,
        cum_dists: np.ndarray,
        hazards: List[CorridorHazard]
    ) -> Tuple[int, float]:
        potholes = 0
        iri_proxy = 0.0

        pavement_mask = (vert_clearance >= -0.30) & (vert_clearance <= 0.30)
        if not np.any(pavement_mask):
            return 0, 0.0

        pav_local_indices = np.where(pavement_mask)[0]
        resids = vert_clearance[pavement_mask]
        pothole_indices = np.where(resids < -0.06)[0]

        if len(pothole_indices) > 0:
            p_pts = corr_pts[pavement_mask][pothole_indices]
            p_tree = cKDTree(p_pts[:, :2])
            visited = set()

            for pi in range(len(p_pts)):
                if pi in visited:
                    continue
                cluster = p_tree.query_ball_point(p_pts[pi, :2], r=1.5)
                visited.update(cluster)

                loc_idx = pav_local_indices[pothole_indices[pi]]
                dep_val = float(np.min(p_pts[cluster, 2]) - road_z[loc_idx])
                c_dist = float(cum_dists[corr_cl_idx[loc_idx]])
                potholes += 1

                hazards.append(CorridorHazard(
                    hazard_type="Pavement Surface Depression / Pothole",
                    severity="WARNING",
                    chainage_m=round(c_dist, 1),
                    x=float(p_pts[pi, 0]), y=float(p_pts[pi, 1]), z=float(p_pts[pi, 2]),
                    metric_val=round(abs(dep_val) * 100.0, 1),
                    description=f"Pavement depression of {abs(dep_val)*100.0:.1f} cm detected below road elevation"
                ))

        if len(resids) > 10:
            std_z_mm = np.std(resids) * 1000.0
            iri_proxy = round(float(0.12 * std_z_mm), 2)

        return potholes, iri_proxy

    @staticmethod
    def _evaluate_overhead_clearance(
        corr_pts: np.ndarray,
        vert_clearance: np.ndarray,
        corr_cl_idx: np.ndarray,
        cum_dists: np.ndarray,
        clearance_height: float,
        critical_clearance: float,
        hazards: List[CorridorHazard]
    ) -> Tuple[int, int]:
        crit_cnt = 0
        warn_cnt = 0

        overhead_mask = (vert_clearance >= 1.5) & (vert_clearance < clearance_height)
        if not np.any(overhead_mask):
            return 0, 0

        oh_pts = corr_pts[overhead_mask]
        oh_clearances = vert_clearance[overhead_mask]
        oh_cl_idx = corr_cl_idx[overhead_mask]

        oh_tree = cKDTree(oh_pts[:, :2])
        visited = set()

        for oi in range(len(oh_pts)):
            if oi in visited:
                continue
            clust = oh_tree.query_ball_point(oh_pts[oi, :2], r=2.0)
            visited.update(clust)

            min_c = float(np.min(oh_clearances[clust]))
            pt_obs = oh_pts[oi]
            c_dist = float(cum_dists[oh_cl_idx[oi]])

            if min_c < critical_clearance:
                crit_cnt += 1
                severity = "CRITICAL"
                h_type = "Overhead Collision Hazard (<4.0m)"
            else:
                warn_cnt += 1
                severity = "WARNING"
                h_type = "Low Vehicle Clearance Encroachment"

            hazards.append(CorridorHazard(
                hazard_type=h_type,
                severity=severity,
                chainage_m=round(c_dist, 1),
                x=float(pt_obs[0]), y=float(pt_obs[1]), z=float(pt_obs[2]),
                metric_val=round(min_c, 2),
                description=f"Overhead obstruction at {min_c:.2f} m clearance (Required: {clearance_height:.2f} m)"
            ))

        return crit_cnt, warn_cnt


class RoadConditionEngine:
    """Standalone engine for road longitudinal grade, roughness, and vehicle clearance audits."""

    @classmethod
    def analyze_road_condition(
        cls,
        road_centerline_source: str,
        lidar_source: str,
        output_vector_path: str,
        max_design_grade_pct: float = 8.0,
        critical_grade_pct: float = 12.0,
        vehicle_clearance_height_m: float = 4.80,
        critical_clearance_height_m: float = 4.00,
        corridor_width_m: float = 8.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Audits longitudinal grades, pavement roughness, surface depressions, and overhead vehicle clearances."""
        import laspy
        ctx = ProcessingContext(progress_callback, log_callback)

        ctx.progress(5, "Loading road centerline alignment...")
        cl_pts, srs_cl = RoadDataLoader.load_centerline_coords_with_srs(road_centerline_source)
        if len(cl_pts) < 2:
            raise ValueError("Road centerline must contain at least 2 vertices.")

        ctx.progress(15, "Loading LiDAR point cloud for corridor audit...")
        las = laspy.read(lidar_source)
        coords = np.vstack((las.x, las.y, las.z)).T
        srs_las = RoadSpatialReference.from_las(las)
        target_srs = srs_cl if RoadSpatialReference.is_valid(srs_cl) else srs_las

        ctx.progress(35, "Auditing longitudinal slope grades and overhead vehicle clearance envelope...")
        audit_res = RoadCorridorAuditor.audit_corridor(
            cl_pts=cl_pts,
            coords=coords,
            corridor_width_m=corridor_width_m,
            max_design_grade_pct=max_design_grade_pct,
            critical_grade_pct=critical_grade_pct,
            clearance_height_m=vehicle_clearance_height_m,
            critical_clearance_m=critical_clearance_height_m,
            ctx=ctx
        )

        ctx.progress(75, "Exporting road hazard inspection vector layer...")
        RoadVectorWriter.write_hazard_layers(audit_res["hazards"], output_vector_path, srs=target_srs)

        ctx.progress(90, "Generating comprehensive Road Corridor Engineering Report...")
        report_path = os.path.splitext(output_vector_path)[0] + "_audit_report.json"
        summary_report = {
            "title": "GeoStudio Road Corridor & Transportation Infrastructure Audit",
            "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "road_corridor_length_m": audit_res["total_corridor_length_m"],
            "maximum_grade_pct": audit_res["max_grade_pct"],
            "mean_grade_pct": audit_res["mean_grade_pct"],
            "steep_grade_sections_count": audit_res["steep_grade_count"],
            "critical_grade_sections_count": audit_res["critical_grade_count"],
            "iri_roughness_proxy_m_km": audit_res["iri_proxy_m_km"],
            "pothole_depressions_detected": audit_res["potholes_count"],
            "critical_clearance_strikes": audit_res["critical_clearance_count"],
            "warning_clearance_violations": audit_res["warning_clearance_count"],
            "total_corridor_hazards_flagged": audit_res["total_hazards_count"],
            "hazards": [asdict(h) for h in audit_res["hazards"][:50]]
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary_report, f, indent=2)

        ctx.progress(100, "Road condition & vehicle clearance audit complete!")

        audit_res["output_vector_path"] = output_vector_path
        audit_res["report_path"] = report_path
        return audit_res
