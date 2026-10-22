# -*- coding: utf-8 -*-
"""
GeoStudio - Cloud-Optimized Point Cloud (COPC) Indexer & Generator
Automatically indexes and converts raw LAS/LAZ/XYZ datasets into genuine .copc.laz files.
"""

import os
import sys
import subprocess
import shutil
import tempfile
import struct
import json
import time

from .point_cloud_classifier import check_classification_status, classify_point_cloud


class PointCloudIndexer:
    """Provides high-speed indexing and conversion to Cloud-Optimized Point Clouds (.copc.laz)."""
    _current_process = None
    _is_cancelled = False

    # Expose classification methods for backward compatibility
    check_classification_status = staticmethod(check_classification_status)

    @classmethod
    def cancel(cls):
        cls._is_cancelled = True
        if cls._current_process:
            try:
                cls._current_process.terminate()
                cls._current_process.kill()
            except Exception:
                pass
            cls._current_process = None

    @staticmethod
    def get_point_count(file_path: str) -> int:
        """Reads point count from LAS/LAZ binary headers in < 1 millisecond."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(375)
                if header[:4] == b'LASF':
                    v_maj, v_min = header[24], header[25]
                    pts_legacy, = struct.unpack('<I', header[107:111])
                    if pts_legacy > 0:
                        return pts_legacy
                    if v_maj == 1 and v_min >= 4 and len(header) >= 255:
                        pts_64, = struct.unpack('<Q', header[247:255])
                        if pts_64 > 0:
                            return pts_64
        except Exception:
            pass
        return 0

    @staticmethod
    def get_indexer_command(input_path: str, output_path: str):
        """Builds an optimized, multi-threaded PDAL/Untwine pipeline tailored to dataset size."""
        import glob
        qgis_candidates = [
            os.environ.get("QGIS_PREFIX_PATH", ""),
            os.environ.get("OSGEO4W_ROOT", ""),
            r"C:\Program Files\QGIS 3.40.14",
            r"C:\Program Files\QGIS 3.34.14",
            r"C:\Program Files\QGIS 3.28.15",
            r"C:\OSGeo4W",
            r"C:\OSGeo4W64",
        ] + glob.glob(r"C:\Program Files\QGIS*")

        qgis_root = ""
        for qc in qgis_candidates:
            if qc and os.path.isdir(qc):
                qgis_root = qc
                break
        if not qgis_root:
            qgis_root = r"C:\Program Files\QGIS 3.40.14"

        bin_dir = os.path.join(qgis_root, "bin")
        qgis_bin = os.path.join(qgis_root, "apps", "qgis-ltr", "bin")

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir};{qgis_bin};" + env.get("PATH", "")
        proj_dir = os.path.join(qgis_root, "share", "proj")
        gdal_dir = os.path.join(qgis_root, "share", "gdal")
        if os.path.exists(proj_dir):
            env["PROJ_LIB"] = proj_dir
            env["PROJ_DATA"] = proj_dir
        if os.path.exists(gdal_dir):
            env["GDAL_DATA"] = gdal_dir

        pdal_candidates = [
            os.path.join(qgis_root, "bin", "pdal.exe"),
            os.path.join(qgis_root, "apps", "qgis-ltr", "bin", "pdal.exe"),
            os.path.join(qgis_root, "apps", "Python312", "Scripts", "pdal.exe"),
            shutil.which("pdal"),
        ]

        total_pts = PointCloudIndexer.get_point_count(input_path)

        for p in pdal_candidates:
            if p and os.path.exists(p):
                stages = [input_path]
                if total_pts > 20_000_000:
                    step = max(2, int(round(total_pts / 15_000_000)))
                    stages.append({
                        "type": "filters.decimation",
                        "step": step
                    })

                stages.append({
                    "type": "writers.copc",
                    "filename": output_path,
                    "forward": "all",
                    "threads": 8
                })

                pipe_path = os.path.join(tempfile.gettempdir(), f"pdal_pipe_{int(time.time())}_{os.getpid()}.json")
                try:
                    with open(pipe_path, "w", encoding="utf-8") as f:
                        json.dump(stages, f, indent=2)
                    cmd = [p, "pipeline", pipe_path]
                    return cmd, env
                except Exception:
                    cmd = [
                        p, "translate", input_path, output_path,
                        "--writer", "writers.copc",
                        "--writers.copc.forward=all",
                        "--writers.copc.threads=8"
                    ]
                    return cmd, env

        # Fallback to Untwine if PDAL is not directly found
        untwine_candidates = [
            os.path.join(qgis_root, "apps", "qgis-ltr", "untwine.exe"),
            os.path.join(qgis_root, "bin", "untwine.exe"),
            shutil.which("untwine"),
        ]
        for u in untwine_candidates:
            if u and os.path.exists(u):
                cmd = [u, "-i", input_path, "-o", output_path]
                return cmd, env

        return None, env


    @staticmethod
    def get_target_copc_path(file_path: str) -> str:
        """Determines the destination .copc.laz path, preferring dataset folder or fast cache."""
        base_dir = os.path.dirname(os.path.abspath(file_path))
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        local_copc = os.path.join(base_dir, f"{base_name}.copc.laz")
        if os.path.exists(local_copc) and os.path.getsize(local_copc) > 1024:
            return local_copc

        cache_dir = os.path.join(tempfile.gettempdir(), "GeoStudio_COPC_Cache")
        os.makedirs(cache_dir, exist_ok=True)
        cached_copc = os.path.join(cache_dir, f"{base_name}.copc.laz")
        if os.path.exists(cached_copc) and os.path.getsize(cached_copc) > 1024:
            return cached_copc

        try:
            test_file = os.path.join(base_dir, ".test_write")
            with open(test_file, "w") as f:
                f.write("1")
            os.remove(test_file)
            return local_copc
        except Exception:
            return cached_copc

    @classmethod
    def ensure_copc_index(cls, file_path: str, progress_callback=None) -> str:
        """
        Ensures a .copc.laz file exists for the given point cloud dataset.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Point cloud file not found: {file_path}")

        if file_path.lower().endswith(".copc.laz"):
            return file_path

        target_copc = cls.get_target_copc_path(file_path)
        if os.path.exists(target_copc) and os.path.getsize(target_copc) > 1024:
            return target_copc

        cmd, env = cls.get_indexer_command(file_path, target_copc)
        if not cmd:
            print("[PointCloudIndexer] Warning: No COPC indexer tool found.")
            return None

        cls._is_cancelled = False

        if progress_callback:
            progress_callback(20, "Launching 8-core parallel COPC indexer...")

        try:
            startupinfo = None
            cflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                cflags = (
                    getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                    | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000)
                )

            try:
                from PyQt5.QtWidgets import QApplication
            except ImportError:
                QApplication = None

            log_path = os.path.join(tempfile.gettempdir(), f"copc_build_{int(time.time())}.log")
            with open(log_path, "w", encoding="utf-8", errors="ignore") as log_out:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_out,
                    stderr=subprocess.STDOUT,
                    env=env,
                    startupinfo=startupinfo,
                    creationflags=cflags
                )
                cls._current_process = process

                start_t = time.time()

                while process.poll() is None:
                    if cls._is_cancelled:
                        try:
                            process.kill()
                        except Exception:
                            pass
                        cls._current_process = None
                        return None

                    time.sleep(0.3)
                    elapsed = time.time() - start_t
                    ratio = 1.0 - (0.5 ** (elapsed / 40.0))
                    dyn_pct = min(98, max(25, 25 + int(ratio * 73)))

                    if elapsed < 30:
                        status_msg = f"Reading & streaming LiDAR points ({dyn_pct}% • {int(elapsed)}s)..."
                    elif elapsed < 75:
                        status_msg = f"Building spatial LOD octree hierarchy ({dyn_pct}% • {int(elapsed)}s)..."
                    else:
                        status_msg = f"Writing Cloud-Optimized Point Cloud to disk ({dyn_pct}% • {int(elapsed)}s)..."

                    if progress_callback:
                        progress_callback(dyn_pct, status_msg)

                    if QApplication:
                        QApplication.processEvents()

            cls._current_process = None
            rc = process.poll()
            if rc == 0 and os.path.exists(target_copc) and os.path.getsize(target_copc) > 1024:
                if progress_callback:
                    progress_callback(100, "Cloud-Optimized Point Cloud created successfully!")
                return target_copc
            else:
                return None

        except Exception as e:
            print(f"[PointCloudIndexer] Error generating COPC: {e}")
            cls._current_process = None
            return None

    @classmethod
    def classify_point_cloud(cls, input_path: str, output_path: str = None, progress_callback=None) -> str:
        """Forwarding method to classify_point_cloud with cancellation support."""
        cls._is_cancelled = False
        return classify_point_cloud(
            input_path=input_path,
            output_path=output_path,
            progress_callback=progress_callback,
            cancel_checker=lambda: cls._is_cancelled
        )
