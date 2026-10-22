# -*- coding: utf-8 -*-
"""
GeoStudio - Building Planar Roof Extraction Engine
Segments and extracts 3D planar roof facets from LiDAR point clouds:
1. Multi-plane RANSAC segmentation and normal-constrained spatial clustering
2. Precise roof facet geometry: Pitch/Slope (°), Azimuth/Aspect (°), 3D Area (m²), 2D Footprint (m²)
3. Solar PV Insolation Potential Rating (Optimal, Good, Fair, Poor)
4. Vector 2D/3D Polygonization of individual roof planes (GPKG / SHP)
"""

import os
import json
import math
import time
from typing import Dict, Any, Callable, Optional, List, Tuple
import numpy as np
from scipy.spatial import cKDTree, ConvexHull
from osgeo import ogr, osr


class BuildingRoofEngine:
    """Extracts building planar roof facets, slopes, aspects, and solar potential from LiDAR point clouds."""

    @classmethod
    def extract_roof_facets(
        cls,
        input_las_path: str,
        output_vector_path: str,
        min_facet_area_m2: float = 4.0,
        distance_threshold_m: float = 0.20,
        max_angle_dev_deg: float = 15.0,
        min_inliers_count: int = 25,
        target_class: int = 6, # ASPRS Class 6: Building
        min_building_height_m: float = 2.20, # Minimum height above terrain to reject ground berms/slopes
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Extracts planar roof facets from building points in a LiDAR point cloud.
        Computes pitch, azimuth, area, and solar suitability.
        Outputs vector polygons (GPKG/SHP) and machine-readable JSON summary.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        import laspy

        progress(5, f"Reading LiDAR file: {os.path.basename(input_las_path)}...")
        log(f"Loading point cloud: <code>{input_las_path}</code>")

        las = laspy.read(input_las_path)
        point_count = len(las.x)
        coords = np.vstack((las.x, las.y, las.z)).T

        # 1. Height Above Ground (HAG) terrain normalization
        progress(10, "Modeling bare-earth terrain surface...")
        classes = np.array(las.classification)
        g_mask = (classes == 2)
        tree_g = None
        g_pts = None
        if np.sum(g_mask) >= 100:
            step_g = max(1, np.sum(g_mask) // 150000)
            g_pts = coords[g_mask][::step_g]
            tree_g = cKDTree(g_pts[:, :2])

        # 2. Isolate building points (Class 6) or elevated planar points
        progress(18, "Filtering building candidate points...")
        bldg_mask = (classes == target_class)

        # Fallback if building class is not populated: use elevated non-ground points
        if np.sum(bldg_mask) < 50:
            log(f"Notice: Class {target_class} has few points ({np.sum(bldg_mask)}). Analyzing elevated points (z > min+{min_building_height_m:.1f}m)...")
            z_min = np.min(coords[:, 2])
            bldg_mask = (classes != 2) & (coords[:, 2] >= (z_min + min_building_height_m))

        # Filter out misclassified bare ground, road berms, and low mounds via HAG
        if tree_g is not None and np.sum(bldg_mask) > 0:
            cand_indices = np.where(bldg_mask)[0]
            _, g_idxs = tree_g.query(coords[cand_indices, :2], k=1)
            bldg_hag = coords[cand_indices, 2] - g_pts[g_idxs, 2]
            elev_mask = (bldg_hag >= min_building_height_m)
            bldg_indices = cand_indices[elev_mask]
            num_rejected = np.sum(~elev_mask)
            if num_rejected > 0:
                log(f"Filtered out <b>{num_rejected:,}</b> misclassified bare ground/berm points with height &lt; {min_building_height_m:.1f} m.")
        else:
            bldg_indices = np.where(bldg_mask)[0]

        num_bldg_pts = len(bldg_indices)
        log(f"Validated elevated building candidate points: <b>{num_bldg_pts:,}</b>")

        if num_bldg_pts < min_inliers_count:
            raise ValueError(f"Insufficient elevated building points ({num_bldg_pts}) for roof extraction.")

        bldg_pts = coords[bldg_indices]

        # Estimate surface normals via k-NN PCA
        progress(25, "Estimating local point surface normal vectors...")
        k_norm = min(20, num_bldg_pts)
        tree = cKDTree(bldg_pts)
        dists, idxs = tree.query(bldg_pts, k=k_norm)

        normals = np.zeros((num_bldg_pts, 3), dtype=np.float32)
        batch_size = 50000
        for start in range(0, num_bldg_pts, batch_size):
            end = min(start + batch_size, num_bldg_pts)
            batch = bldg_pts[idxs[start:end]]
            means = np.mean(batch, axis=1, keepdims=True)
            diffs = batch - means
            covs = np.einsum('bki,bkj->bij', diffs, diffs) / (k_norm - 1)
            evals, evecs = np.linalg.eigh(covs)
            # Normal is minor eigenvector (evecs[:, :, 0])
            n = evecs[:, :, 0]
            # Orient normal upwards (positive z)
            flip = (n[:, 2] < 0)
            n[flip] = -n[flip]
            normals[start:end] = n

        # Multi-plane RANSAC segmentation
        progress(40, "Segmenting planar roof facets via Multi-Plane RANSAC...")
        remaining_indices = np.arange(num_bldg_pts)
        extracted_facets = []
        max_iterations = 80
        facet_id = 1
        cos_tol = math.cos(math.radians(max_angle_dev_deg))

        while len(remaining_indices) >= min_inliers_count and len(extracted_facets) < 150:
            sub_pts = bldg_pts[remaining_indices]
            sub_normals = normals[remaining_indices]
            n_sub = len(sub_pts)

            best_inliers_local = None
            best_plane = None
            max_inliers = 0

            # RANSAC trials
            num_trials = min(120, max(25, n_sub // 50))
            for _ in range(num_trials):
                # Pick 3 random points
                idx3 = np.random.choice(n_sub, 3, replace=False)
                p1, p2, p3 = sub_pts[idx3]
                # Plane normal
                v1 = p2 - p1
                v2 = p3 - p1
                cp = np.cross(v1, v2)
                cp_len = np.linalg.norm(cp)
                if cp_len < 1e-5:
                    continue
                pn = cp / cp_len
                if pn[2] < 0:
                    pn = -pn
                d_plane = -np.dot(pn, p1)

                # Distance from all points to plane: |pn . p + d|
                dists_p = np.abs(np.dot(sub_pts, pn) + d_plane)
                # Angular alignment between point normal and plane normal
                ang_align = np.dot(sub_normals, pn)

                inlier_mask = (dists_p <= distance_threshold_m) & (ang_align >= cos_tol)
                in_count = np.sum(inlier_mask)

                if in_count > max_inliers:
                    max_inliers = in_count
                    best_inliers_local = inlier_mask
                    best_plane = (pn, d_plane)

            if max_inliers < min_inliers_count or best_plane is None:
                break

            # Refit plane to all inliers using SVD
            inlier_pts = sub_pts[best_inliers_local]
            centroid = np.mean(inlier_pts, axis=0)
            u, s, vh = np.linalg.svd(inlier_pts - centroid)
            refit_n = vh[2]
            if refit_n[2] < 0:
                refit_n = -refit_n
            refit_d = -np.dot(refit_n, centroid)

            # Spatial clustering of inliers: disconnect disjoint buildings with same slope
            in_tree = cKDTree(inlier_pts[:, :2])
            visited = np.zeros(len(inlier_pts), dtype=bool)

            for i_pt in range(len(inlier_pts)):
                if visited[i_pt]:
                    continue
                # Connected component
                comp = []
                queue = [i_pt]
                visited[i_pt] = True
                while queue:
                    curr = queue.pop(0)
                    comp.append(curr)
                    neighs = in_tree.query_ball_point(inlier_pts[curr, :2], r=2.5)
                    for nb in neighs:
                        if not visited[nb]:
                            visited[nb] = True
                            queue.append(nb)

                if len(comp) >= min_inliers_count:
                    cluster_pts = inlier_pts[comp]

                    # Verify cluster clearance above local terrain
                    if tree_g is not None:
                        _, g_idxs = tree_g.query(cluster_pts[:, :2], k=1)
                        c_hag = cluster_pts[:, 2] - g_pts[g_idxs, 2]
                        if np.mean(c_hag) < min_building_height_m:
                            continue

                    # Compute facet morphometrics
                    facet_dict = cls._compute_facet_attributes(
                        facet_id=facet_id,
                        points=cluster_pts,
                        normal=refit_n,
                        min_area=min_facet_area_m2
                    )
                    if facet_dict is not None:
                        extracted_facets.append(facet_dict)
                        facet_id += 1

            # Remove extracted inliers from remaining pool
            remaining_indices = remaining_indices[~best_inliers_local]

            pct = 40 + int((len(extracted_facets) / 60.0) * 45)
            progress(min(85, pct), f"Extracted {len(extracted_facets)} planar roof facets...")

        log(f"Successfully segmented <b>{len(extracted_facets):,}</b> discrete planar roof facets.")

        # Vector Polygonization
        progress(88, "Polygonizing roof facet geometries and calculating solar potential...")
        cls._write_roof_polygons(output_vector_path, extracted_facets)

        progress(95, "Compiling Building Roof & Solar Potential Report...")
        base_rep, _ = os.path.splitext(output_vector_path)
        report_path = f"{base_rep}_roof_report.json"

        total_3d_area = sum(f["area_3d_m2"] for f in extracted_facets)
        optimal_solar_area = sum(f["area_3d_m2"] for f in extracted_facets if f["solar_rating"] in ["OPTIMAL", "GOOD"])

        results = {
            "status": "SUCCESS",
            "total_building_points": num_bldg_pts,
            "extracted_facets_count": len(extracted_facets),
            "total_roof_3d_area_m2": round(total_3d_area, 2),
            "total_roof_footprint_m2": round(sum(f["area_2d_m2"] for f in extracted_facets), 2),
            "optimal_pv_solar_area_m2": round(optimal_solar_area, 2),
            "solar_viable_area_pct": round((optimal_solar_area / max(1.0, total_3d_area)) * 100.0, 1),
            "mean_roof_pitch_deg": round(float(np.mean([f["pitch_deg"] for f in extracted_facets])), 1) if extracted_facets else 0.0,
            "output_vector": output_vector_path,
            "report_path": report_path
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        progress(100, f"Roof extraction complete: {len(extracted_facets)} facets ({total_3d_area:,.1f} m² surface area)!")
        return results

    @classmethod
    def _compute_facet_attributes(
        cls,
        facet_id: int,
        points: np.ndarray,
        normal: np.ndarray,
        min_area: float
    ) -> Optional[Dict[str, Any]]:
        """Calculates pitch, azimuth, area, and solar potential for a single roof facet."""
        # 1. Pitch / Slope: angle between normal and vertical Z axis
        # nz = normal[2]
        pitch_rad = math.acos(min(1.0, max(-1.0, abs(normal[2]))))
        pitch_deg = round(math.degrees(pitch_rad), 1)

        # 2. Azimuth / Aspect: compass direction of roof downslope (degrees from North)
        # Downslope horizontal projection is (-nx, -ny)
        down_x = -normal[0]
        down_y = -normal[1]
        if math.hypot(down_x, down_y) < 1e-4:
            azimuth_deg = 0.0 # Flat roof
            aspect_dir = "FLAT"
        else:
            az_rad = math.atan2(down_x, down_y)
            azimuth_deg = round((math.degrees(az_rad) + 360.0) % 360.0, 1)

            # Compass cardinal directions
            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            idx = int(((azimuth_deg + 11.25) % 360.0) / 22.5)
            aspect_dir = dirs[idx]

        # 3. 2D & 3D Area calculation via Convex Hull / footprint
        if len(points) < 4:
            return None
        try:
            hull_2d = ConvexHull(points[:, :2])
            area_2d = float(hull_2d.volume) # in 2D ConvexHull, 'volume' is polygon area
            boundary_pts_2d = points[hull_2d.vertices, :2]
            boundary_pts_3d = points[hull_2d.vertices]
        except Exception:
            # Bounding box fallback
            dx = np.max(points[:, 0]) - np.min(points[:, 0])
            dy = np.max(points[:, 1]) - np.min(points[:, 1])
            area_2d = float(dx * dy * 0.7)
            boundary_pts_2d = points[:4, :2]
            boundary_pts_3d = points[:4]

        # 3D surface area: Area_3D = Area_2D / cos(pitch)
        cos_pitch = max(0.05, math.cos(pitch_rad))
        area_3d = float(area_2d / cos_pitch)

        if area_2d < min_area:
            return None

        # 4. Roof morphology classification
        if pitch_deg < 8.0:
            roof_type = "Flat Roof"
        elif pitch_deg < 20.0:
            roof_type = "Low Pitch / Shed"
        elif pitch_deg <= 45.0:
            roof_type = "Standard Gable / Hip"
        else:
            roof_type = "Steep / Mansard"

        # 5. Solar PV Insolation Potential Rating
        # Ideal: South-facing (150° - 210° in northern hemisphere) with 25° - 35° pitch
        az_dev = abs(azimuth_deg - 180.0) # 0 = south, 180 = north
        if pitch_deg < 8.0:
            solar_rating = "GOOD"
            solar_score = 82.0 # Flat roofs accommodate angled solar racking
        elif az_dev <= 45.0 and 20.0 <= pitch_deg <= 40.0:
            solar_rating = "OPTIMAL"
            solar_score = 98.0 - (az_dev * 0.2)
        elif az_dev <= 70.0 and 15.0 <= pitch_deg <= 50.0:
            solar_rating = "GOOD"
            solar_score = 85.0 - (az_dev * 0.25)
        elif az_dev <= 110.0:
            solar_rating = "FAIR"
            solar_score = 65.0 - (az_dev * 0.2)
        else:
            solar_rating = "POOR"
            solar_score = max(10.0, 40.0 - (pitch_deg * 0.5))

        cent_x = float(np.mean(points[:, 0]))
        cent_y = float(np.mean(points[:, 1]))
        cent_z = float(np.mean(points[:, 2]))

        return {
            "facet_id": facet_id,
            "center_x": round(cent_x, 2),
            "center_y": round(cent_y, 2),
            "center_z": round(cent_z, 2),
            "pitch_deg": pitch_deg,
            "azimuth_deg": azimuth_deg,
            "aspect_dir": aspect_dir,
            "roof_type": roof_type,
            "area_2d_m2": round(area_2d, 2),
            "area_3d_m2": round(area_3d, 2),
            "solar_rating": solar_rating,
            "solar_score": round(solar_score, 1),
            "point_count": len(points),
            "boundary_pts": boundary_pts_2d
        }

    @classmethod
    def _write_roof_polygons(cls, path: str, facets: List[Dict[str, Any]]):
        """Writes roof facet 2D polygons to GeoPackage or Shapefile."""
        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(path):
            driver.DeleteDataSource(path)

        ds = driver.CreateDataSource(path)
        srs = osr.SpatialReference()
        lyr = ds.CreateLayer("building_roof_facets", srs, ogr.wkbPolygon)

        fields = [
            ("Facet_ID", ogr.OFTInteger),
            ("Pitch_deg", ogr.OFTReal),
            ("Azimuth_deg", ogr.OFTReal),
            ("Aspect_Dir", ogr.OFTString),
            ("Roof_Type", ogr.OFTString),
            ("Area_3D_m2", ogr.OFTReal),
            ("Area_2D_m2", ogr.OFTReal),
            ("Solar_Rating", ogr.OFTString),
            ("Solar_Score", ogr.OFTReal),
            ("Elevation_m", ogr.OFTReal),
            ("Point_Count", ogr.OFTInteger),
        ]
        for f_name, f_type in fields:
            lyr.CreateField(ogr.FieldDefn(f_name, f_type))

        for f in facets:
            b_pts = f.get("boundary_pts", [])
            if len(b_pts) < 3:
                continue

            ring = ogr.Geometry(ogr.wkbLinearRing)
            for pt in b_pts:
                ring.AddPoint_2D(float(pt[0]), float(pt[1]))
            # Close ring
            ring.AddPoint_2D(float(b_pts[0][0]), float(b_pts[0][1]))

            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)

            feat = ogr.Feature(lyr.GetLayerDefn())
            feat.SetField("Facet_ID", int(f["facet_id"]))
            feat.SetField("Pitch_deg", float(f["pitch_deg"]))
            feat.SetField("Azimuth_deg", float(f["azimuth_deg"]))
            feat.SetField("Aspect_Dir", str(f["aspect_dir"]))
            feat.SetField("Roof_Type", str(f["roof_type"]))
            feat.SetField("Area_3D_m2", float(f["area_3d_m2"]))
            feat.SetField("Area_2D_m2", float(f["area_2d_m2"]))
            feat.SetField("Solar_Rating", str(f["solar_rating"]))
            feat.SetField("Solar_Score", float(f["solar_score"]))
            feat.SetField("Elevation_m", float(f["center_z"]))
            feat.SetField("Point_Count", int(f["point_count"]))
            feat.SetGeometry(poly)

            lyr.CreateFeature(feat)
            feat = None

        ds.FlushCache()
        ds = None
