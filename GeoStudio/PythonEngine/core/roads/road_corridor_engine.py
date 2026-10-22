# -*- coding: utf-8 -*-
"""
GeoStudio - Road Centerline, Curbs & Corridor Vector Alignment Engine
Extracts 3D continuous road centerlines, curb lines, and equidistant station chainage markers:
- PCA principal axis alignment and coordinate projection
- Cross-section slicing at user-specified interval steps
- Centerline 3D centroid tracing
- Left and right road curb / edge boundary delineation
- Equidistant station chainage markers (0+000, 0+025, etc.) with longitudinal slope gradient
"""

import os
from typing import Dict, Any, Callable, Optional, List
import numpy as np

from .road_models import ProcessingContext, StationMarker, CorridorGeometryResult
from .road_io import RoadVectorWriter, RoadDataLoader


class RoadAlignmentTracer:
    """Traces continuous 3D road centerlines, curbs, and equidistant station chainage."""

    @classmethod
    def trace_corridor(
        cls,
        road_points: np.ndarray,
        station_interval_m: float = 25.0,
        corridor_step_m: float = 5.0,
        detect_curbs: bool = True
    ) -> CorridorGeometryResult:
        coords = road_points[:, :3]

        # 1. PCA principal orientation
        mean_c = np.mean(coords[:, :2], axis=0)
        cov_2d = np.cov(coords[:, :2] - mean_c, rowvar=False)
        eigvals, eigvecs = np.linalg.eigh(cov_2d)
        main_dir = eigvecs[:, 1]
        cross_dir = eigvecs[:, 0]

        proj_dist = np.dot(coords[:, :2] - mean_c, main_dir)
        order = np.argsort(proj_dist)
        sorted_coords = coords[order]
        sorted_proj = proj_dist[order]

        # 2. Cross-section slicing
        slices = np.arange(sorted_proj[0], sorted_proj[-1], corridor_step_m)
        centerline_pts = []
        curb_left_pts = []
        curb_right_pts = []
        widths = []
        half_step = corridor_step_m * 0.75

        for s in slices:
            i_start = np.searchsorted(sorted_proj, s - half_step)
            i_end = np.searchsorted(sorted_proj, s + half_step)
            pts_slice = sorted_coords[i_start:i_end]
            if len(pts_slice) < 3:
                continue

            cent_init = np.median(pts_slice, axis=0)
            lateral_dist = np.dot(pts_slice[:, :2] - cent_init[:2], cross_dir)

            # Robust outlier rejection along the cross-section
            q25, q75 = np.percentile(lateral_dist, [25, 75])
            iqr = max(0.5, q75 - q25)
            inliers = (lateral_dist >= q25 - 2.0 * iqr) & (lateral_dist <= q75 + 2.0 * iqr)
            pts_road_slice = pts_slice[inliers]
            lat_road = lateral_dist[inliers]

            if len(pts_road_slice) < 3:
                continue

            cent_3d = np.mean(pts_road_slice, axis=0)
            centerline_pts.append(cent_3d)

            w = float(np.max(lat_road) - np.min(lat_road))
            widths.append(w)

            if detect_curbs:
                curb_left_pts.append(pts_road_slice[np.argmax(lat_road)])
                curb_right_pts.append(pts_road_slice[np.argmin(lat_road)])

        if len(centerline_pts) < 2:
            raise RuntimeError("Could not construct a valid continuous road centerline from the given points.")

        centerline_arr = np.array(centerline_pts)
        avg_width = float(np.mean(widths)) if widths else 7.0

        diffs = np.diff(centerline_arr, axis=0)
        seg_lens = np.sqrt(np.sum(diffs ** 2, axis=1))
        total_len = float(np.sum(seg_lens))
        cum_dist = np.insert(np.cumsum(seg_lens), 0, 0.0)

        station_markers = cls._compute_stations(
            centerline_arr, diffs, seg_lens, cum_dist, total_len, avg_width, station_interval_m
        )

        all_grades = [abs(s.grade_pct) for s in station_markers]
        max_grade = float(np.max(all_grades)) if all_grades else 0.0

        return CorridorGeometryResult(
            centerline_points=centerline_arr,
            curb_left_points=np.array(curb_left_pts) if curb_left_pts else np.empty((0, 3)),
            curb_right_points=np.array(curb_right_pts) if curb_right_pts else np.empty((0, 3)),
            station_markers=station_markers,
            total_length_m=total_len,
            average_width_m=avg_width,
            max_grade_pct=max_grade
        )

    @staticmethod
    def _compute_stations(
        centerline_pts: np.ndarray,
        diffs: np.ndarray,
        seg_lens: np.ndarray,
        cum_dist: np.ndarray,
        total_len: float,
        avg_width: float,
        interval_m: float
    ) -> List[StationMarker]:
        markers = []
        chainages = np.arange(0.0, total_len, interval_m)
        if len(chainages) == 0 or chainages[-1] < (total_len - 5.0):
            chainages = np.append(chainages, total_len)

        for tc in chainages:
            idx = np.searchsorted(cum_dist, tc)
            if idx == 0:
                pt_3d = centerline_pts[0]
                grade = 0.0
            elif idx >= len(centerline_pts):
                pt_3d = centerline_pts[-1]
                ds = seg_lens[-1]
                grade = (centerline_pts[-1, 2] - centerline_pts[-2, 2]) / ds * 100.0 if ds > 0 else 0.0
            else:
                ratio = (tc - cum_dist[idx - 1]) / seg_lens[idx - 1] if seg_lens[idx - 1] > 0 else 0.0
                pt_3d = centerline_pts[idx - 1] + ratio * diffs[idx - 1]
                ds = seg_lens[idx - 1]
                grade = (diffs[idx - 1, 2] / ds * 100.0) if ds > 0 else 0.0

            km = int(tc // 1000)
            m = tc % 1000
            st_label = f"{km}+{m:05.1f}"

            markers.append(StationMarker(
                station=st_label,
                chainage_m=round(float(tc), 1),
                x=float(pt_3d[0]),
                y=float(pt_3d[1]),
                z=float(pt_3d[2]),
                grade_pct=round(float(grade), 2),
                width_m=round(avg_width, 1)
            ))
        return markers


class RoadCorridorEngine:
    """Standalone engine for road centerline, curbs, and corridor vector alignment."""

    @classmethod
    def extract_road_corridor(
        cls,
        input_source: str,
        output_vector_path: str,
        station_interval_m: float = 25.0,
        corridor_search_step_m: float = 5.0,
        detect_curbs: bool = True,
        curb_step_height_m: float = 0.12,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Extracts 3D continuous road centerlines, curbs, and equidistant station chainage markers."""
        ctx = ProcessingContext(progress_callback, log_callback)

        ctx.progress(5, "Loading road surface data...")
        ctx.log(f"Reading input road source: <code>{os.path.basename(input_source)}</code>")

        road_points, srs = RoadDataLoader.load_road_points_with_srs(input_source)
        if len(road_points) < 10:
            raise ValueError("Insufficient road points found in input source (minimum 10 required).")

        ctx.progress(25, "Tracing principal road corridor alignment and cross-sections...")
        geom_result = RoadAlignmentTracer.trace_corridor(
            road_points=road_points,
            station_interval_m=station_interval_m,
            corridor_step_m=corridor_search_step_m,
            detect_curbs=detect_curbs
        )

        ctx.progress(75, "Writing 3D road vector layers to GeoPackage...")
        curbs_written = RoadVectorWriter.write_corridor_layers(
            geom_res=geom_result,
            out_path=output_vector_path,
            detect_curbs=detect_curbs,
            srs=srs
        )

        ctx.progress(100, "Road corridor alignment vector extraction complete!")

        return {
            "centerline_length_m": round(geom_result.total_length_m, 1),
            "average_road_width_m": round(geom_result.average_width_m, 1),
            "max_longitudinal_grade_pct": round(geom_result.max_grade_pct, 2),
            "station_markers_count": len(geom_result.station_markers),
            "curb_lines_count": curbs_written,
            "output_vector_path": output_vector_path,
        }
