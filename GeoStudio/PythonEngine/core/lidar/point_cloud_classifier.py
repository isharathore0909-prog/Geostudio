# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Point Cloud Classifier
Multi-threaded SMRF ground classification and HAG vegetation/building segmentation.
"""

import os
import json
import time
import shutil
import subprocess
import tempfile
from typing import Optional, Dict, Any


def check_classification_status(file_path: str) -> Dict[str, Any]:
    """
    Quickly queries the point cloud statistics to determine if Classification has been populated.
    Returns dict with: 'is_unclassified' (bool), 'max_class' (int), 'min_class' (int).
    """
    try:
        qgis_root = r"C:\Program Files\QGIS 3.40.14"
        pdal_candidates = [
            os.path.join(qgis_root, "bin", "pdal.exe"),
            os.path.join(qgis_root, "apps", "qgis-ltr", "bin", "pdal.exe"),
            shutil.which("pdal"),
        ]
        pdal_exe = next((p for p in pdal_candidates if p and os.path.exists(p)), None)
        if not pdal_exe:
            return {'is_unclassified': False, 'max_class': 0}

        env = os.environ.copy()
        proj_dir = os.path.join(qgis_root, "share", "proj")
        if os.path.exists(proj_dir):
            env["PROJ_LIB"] = proj_dir
            env["PROJ_DATA"] = proj_dir

        startupinfo = None
        cflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        res = subprocess.run(
            [pdal_exe, 'info', '--stats', '--dimensions=Classification', file_path],
            capture_output=True, text=True, env=env,
            startupinfo=startupinfo, creationflags=cflags, timeout=15
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            stats = data.get('stats', {}).get('statistic', [{}])
            if stats:
                mx = stats[0].get('maximum', 0)
                mn = stats[0].get('minimum', 0)
                return {
                    'is_unclassified': (mx == 0),
                    'max_class': mx,
                    'min_class': mn
                }
    except Exception as e:
        print(f"[PointCloudClassifier] Error checking classification: {e}")
    return {'is_unclassified': False, 'max_class': 0}


def classify_point_cloud(input_path: str, output_path: Optional[str] = None, progress_callback=None, cancel_checker=None) -> Optional[str]:
    """
    Executes multi-threaded SMRF ground classification and HAG vegetation segmentation on any point cloud.
    """
    if not output_path:
        base, ext = os.path.splitext(input_path)
        if input_path.lower().endswith(".copc.laz"):
            base = input_path[:-9]
        output_path = f"{base}_classified.copc.laz"

    qgis_root = r"C:\Program Files\QGIS 3.40.14"
    pdal_exe = os.path.join(qgis_root, "bin", "pdal.exe")
    if not os.path.exists(pdal_exe):
        pdal_exe = shutil.which("pdal")
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

    is_geographic = False
    utm_epsg = 32643
    try:
        startupinfo = None
        cflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        sum_res = subprocess.run(
            [pdal_exe, 'info', '--summary', input_path],
            capture_output=True, text=True, env=env,
            startupinfo=startupinfo, creationflags=cflags, timeout=15
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
    is_copc = input_path.lower().endswith(".copc.laz")
    stages.append({
        "type": "readers.copc" if is_copc else "readers.las",
        "filename": input_path,
        "threads": 8
    })

    if is_geographic:
        stages.append({
            "type": "filters.reprojection",
            "out_srs": f"EPSG:{utm_epsg}"
        })

    stages.append({
        "type": "filters.smrf",
        "cell": 1.0,
        "slope": 0.15,
        "window": 18.0,
        "threshold": 0.5,
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
            (
                "Classification = 3 WHERE HeightAboveGround >= 0.3 "
                "&& HeightAboveGround < 1.8 && Classification != 2"
            ),
            (
                "Classification = 4 WHERE HeightAboveGround >= 1.8 "
                "&& HeightAboveGround < 4.0 && Classification != 2"
            ),
            (
                "Classification = 5 WHERE HeightAboveGround >= 4.0 "
                "&& Classification != 2"
            ),
        ]
    })

    if is_geographic:
        stages.append({
            "type": "filters.reprojection",
            "out_srs": "EPSG:4326"
        })

    is_out_copc = output_path.lower().endswith(".copc.laz") or output_path.lower().endswith(".laz")
    w_stage = {
        "type": "writers.copc" if is_out_copc else "writers.las",
        "filename": output_path,
        "forward": "all"
    }
    if is_out_copc:
        w_stage["threads"] = 8
    stages.append(w_stage)

    pipe_path = os.path.join(tempfile.gettempdir(), f"pdal_classify_{int(time.time())}.json")
    with open(pipe_path, "w", encoding="utf-8") as f:
        json.dump(stages, f, indent=2)

    startupinfo = None
    cflags = 0
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        cflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        QApplication = None

    proc = subprocess.Popen(
        [pdal_exe, 'pipeline', pipe_path],
        env=env,
        startupinfo=startupinfo,
        creationflags=cflags
    )

    start_t = time.time()
    while proc.poll() is None:
        if cancel_checker and cancel_checker():
            try:
                proc.kill()
            except Exception:
                pass
            return None

        time.sleep(0.3)
        elapsed = time.time() - start_t
        ratio = 1.0 - (0.5 ** (elapsed / 30.0))
        dyn_pct = min(98, max(10, 10 + int(ratio * 88)))

        if elapsed < 20:
            msg = f"Detecting bare-earth ground via SMRF ({dyn_pct}% • {int(elapsed)}s)..."
        elif elapsed < 50:
            msg = f"Extracting building planarity & classifying canopy ({dyn_pct}% • {int(elapsed)}s)..."
        else:
            msg = f"Writing classified COPC dataset ({dyn_pct}% • {int(elapsed)}s)..."

        if progress_callback:
            progress_callback(dyn_pct, msg)

        if QApplication:
            QApplication.processEvents()

    rc = proc.poll()
    if rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        if progress_callback:
            progress_callback(100, "Point cloud classification complete!")
        return output_path
    return None
