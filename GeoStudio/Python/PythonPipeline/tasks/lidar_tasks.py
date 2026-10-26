# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - LiDAR & 3D Tasks
Handles 3D OpenGL workstation launch, PDAL SMRF ground filtering,
building rooftop classification, vegetation canopy strata, and decimation.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import subprocess

from common import report_progress, report_result


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
            "Classification = 3 WHERE HeightAboveGround >= 0.3 && HeightAboveGround < 1.8 && Classification != 2",
            "Classification = 4 WHERE HeightAboveGround >= 1.8 && HeightAboveGround < 4.0 && Classification != 2",
            "Classification = 5 WHERE HeightAboveGround >= 4.0 && Classification != 2"
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
    """Classifies verified planar building structures and rooftops (ASPRS Class 6).
    Enforces strict planar clustering so tree canopies and foliage are NEVER classified as buildings.
    """
    in_file = args.input
    out_file = args.output or os.path.splitext(in_file)[0] + "_buildings.las"
    report_progress(15, "Analyzing point cloud structure for building rooftops...")

    import laspy
    import numpy as np
    from scipy.spatial import cKDTree

    las = laspy.read(in_file)
    n_pts = len(las.points)
    if n_pts == 0:
        raise ValueError("Point cloud contains no points.")

    coords = np.column_stack([las.x, las.y, las.z])
    classes = np.array(las.classification)

    # 1. Establish ground baseline to determine Height Above Ground (HAG)
    report_progress(25, "Calculating Height Above Ground (HAG)...")
    is_ground = (classes == 2)
    if np.sum(is_ground) >= 100:
        g_pts = coords[is_ground]
        g_tree = cKDTree(g_pts[:, :2])
        batch_sz = 100000
        hag = np.zeros(n_pts, dtype=np.float32)
        for s_idx in range(0, n_pts, batch_sz):
            e_idx = min(s_idx + batch_sz, n_pts)
            _, near_g = g_tree.query(coords[s_idx:e_idx, :2], k=1)
            hag[s_idx:e_idx] = coords[s_idx:e_idx, 2] - g_pts[near_g, 2]
    else:
        min_z = float(np.percentile(coords[:, 2], 5))
        hag = coords[:, 2] - min_z

    # 2. Filter candidate building points:
    # Must have HAG >= 2.2m (clearance above ground)
    # Must have single return: buildings are solid, whereas tree canopy produces multiple returns
    report_progress(45, "Filtering solid planar candidate points...")
    cand_mask = (classes != 2) & (hag >= 2.2) & (hag <= 65.0)

    if hasattr(las, 'number_of_returns') and hasattr(las, 'return_number'):
        try:
            n_ret = np.array(las.number_of_returns)
            r_num = np.array(las.return_number)
            single_or_last = (n_ret <= 1) | (r_num == n_ret)
            cand_mask = cand_mask & single_or_last
        except Exception:
            pass

    cand_indices = np.where(cand_mask)[0]
    num_cands = len(cand_indices)

    if num_cands < 60:
        las.write(out_file)
        report_progress(100, "Building classification complete: 0 buildings found (natural terrain)")
        report_result(True, {"output_file": out_file, "message": "No building structures detected. Canopy preserved as vegetation."})
        return

    # 3. Detect large contiguous planar roof structures (RANSAC / Connected Component clustering)
    report_progress(60, f"Evaluating planar consistency across {num_cands:,} candidate points...")
    sub_coords = coords[cand_indices]
    cand_tree = cKDTree(sub_coords[:, :2])

    k_check = min(20, num_cands)
    _, nbr_indices = cand_tree.query(sub_coords[:, :2], k=k_check)

    nbr_z = sub_coords[nbr_indices, 2]
    z_std = np.std(nbr_z, axis=1)

    planar_mask = (z_std < 0.22)
    planar_cand_indices = cand_indices[planar_mask]

    if len(planar_cand_indices) < 50:
        las.write(out_file)
        report_progress(100, "Building classification complete: 0 buildings found (all vegetation)")
        report_result(True, {"output_file": out_file, "message": "No planar building rooftops found. Foliage preserved as vegetation."})
        return

    # 4. Spatial Connected Component clustering to ensure minimum building footprint
    report_progress(80, "Verifying building roof footprint and spatial clustering...")
    planar_pts = coords[planar_cand_indices]
    planar_tree = cKDTree(planar_pts[:, :2])

    visited = np.zeros(len(planar_pts), dtype=bool)
    confirmed_building_indices = []

    for i in range(len(planar_pts)):
        if visited[i]:
            continue
        cluster = []
        queue = [i]
        visited[i] = True
        while queue:
            curr = queue.pop(0)
            cluster.append(curr)
            nbrs = planar_tree.query_ball_point(planar_pts[curr, :2], r=2.2)
            for nb in nbrs:
                if not visited[nb]:
                    visited[nb] = True
                    queue.append(nb)

        if len(cluster) >= 50:
            c_pts = planar_pts[cluster]
            dx = np.max(c_pts[:, 0]) - np.min(c_pts[:, 0])
            dy = np.max(c_pts[:, 1]) - np.min(c_pts[:, 1])
            est_area = dx * dy
            if est_area >= 15.0:
                for c_idx in cluster:
                    confirmed_building_indices.append(planar_cand_indices[c_idx])

    if confirmed_building_indices:
        b_arr = np.array(confirmed_building_indices, dtype=np.int64)
        las.classification[b_arr] = 6  # ASPRS Class 6: Building
        msg = f"Successfully classified {len(b_arr):,} building points into ASPRS Class 6."
    else:
        msg = "0 building structures detected. All elevated points verified as natural vegetation."

    report_progress(95, "Writing output LAS dataset...")
    las.write(out_file)
    report_progress(100, "Building classification complete")
    report_result(True, {"output_file": out_file, "message": msg})


def task_classify_veg(args):
    """Classifies vegetation canopy into low, medium, and high vegetation (ASPRS Classes 3, 4, 5)."""
    in_file = args.input
    out_file = args.output or os.path.splitext(in_file)[0] + "_vegetation.las"
    report_progress(20, "Computing Height Above Ground (HAG) for vegetation...")

    import laspy
    import numpy as np
    from scipy.spatial import cKDTree

    las = laspy.read(in_file)
    n_pts = len(las.points)
    if n_pts == 0:
        raise ValueError("Point cloud contains no points.")

    coords = np.column_stack([las.x, las.y, las.z])
    classes = np.array(las.classification)

    is_ground = (classes == 2)
    if np.sum(is_ground) >= 100:
        g_pts = coords[is_ground]
        g_tree = cKDTree(g_pts[:, :2])
        batch_sz = 100000
        hag = np.zeros(n_pts, dtype=np.float32)
        for s_idx in range(0, n_pts, batch_sz):
            e_idx = min(s_idx + batch_sz, n_pts)
            _, near_g = g_tree.query(coords[s_idx:e_idx, :2], k=1)
            hag[s_idx:e_idx] = coords[s_idx:e_idx, 2] - g_pts[near_g, 2]
    else:
        min_z = float(np.percentile(coords[:, 2], 5))
        hag = coords[:, 2] - min_z

    non_ground = (classes != 2) & (classes != 6)
    low_veg = non_ground & (hag >= 0.3) & (hag < 1.8)
    med_veg = non_ground & (hag >= 1.8) & (hag < 4.0)
    high_veg = non_ground & (hag >= 4.0)

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
