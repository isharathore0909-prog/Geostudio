# -*- coding: utf-8 -*-
"""
GeoStudio - 3D Viewer LAS/LAZ Point Cloud Reader
Fast reader to extract 3D points from LAS/LAZ/COPC formats via laspy, PDAL, and binary memmap.
"""

import os
import struct
import numpy as np
from .colormaps import apply_las_classification


def load_las_points_data(file_path: str, max_points: int = 8000000):
    """
    Extracts raw LAS point cloud arrays:
    Returns: (x, y, z, rgb_colors, class_colors, intensity_colors, total_points, extra_attrs)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Point cloud file not found: {file_path}")

    pts_data = None
    extra_attrs = {}

    # 1. Try laspy first if available
    try:
        import sys
        user_site = os.path.expanduser(r"~\AppData\Roaming\Python\Python312\site-packages")
        if os.path.exists(user_site) and user_site not in sys.path:
            sys.path.insert(0, user_site)

        import laspy
        with laspy.open(file_path) as fh:
            total_points = fh.header.point_count
            step = 1 if (max_points <= 0 or max_points >= total_points) else max(1, total_points // max_points)
            las = fh.read()

            x = np.array(las.x[::step], dtype=np.float64)
            y = np.array(las.y[::step], dtype=np.float64)
            z = np.array(las.z[::step], dtype=np.float32)

            has_rgb = hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue')
            if has_rgb:
                r_raw = np.array(las.red[::step], dtype=np.float32)
                g_raw = np.array(las.green[::step], dtype=np.float32)
                b_raw = np.array(las.blue[::step], dtype=np.float32)
                max_c = max(float(np.max(r_raw)), float(np.max(g_raw)), float(np.max(b_raw)))
                if max_c > 255.0:
                    all_c = np.concatenate([r_raw, g_raw, b_raw])
                    p1 = max(0.0, float(np.percentile(all_c, 1)))
                    p99 = min(65535.0, float(np.percentile(all_c, 99)))
                    rng = max(1.0, p99 - p1)
                    r = np.clip((r_raw - p1) / rng, 0.0, 1.0).astype(np.float32)
                    g = np.clip((g_raw - p1) / rng, 0.0, 1.0).astype(np.float32)
                    b = np.clip((b_raw - p1) / rng, 0.0, 1.0).astype(np.float32)
                else:
                    r = (r_raw / 255.0).astype(np.float32)
                    g = (g_raw / 255.0).astype(np.float32)
                    b = (b_raw / 255.0).astype(np.float32)
                rgb_colors = np.column_stack((r, g, b)).astype(np.float32)
            else:
                rgb_colors = None

            if hasattr(las, 'classification'):
                class_raw = np.array(las.classification[::step])
                class_colors = apply_las_classification(class_raw)
            else:
                class_colors = None

            if hasattr(las, 'intensity'):
                intens_raw = np.array(las.intensity[::step], dtype=np.float32)
                i_min, i_max = np.percentile(intens_raw, [2, 98]) if len(intens_raw) > 0 else (0, 1)
                i_norm = np.clip((intens_raw - i_min) / max(1.0, i_max - i_min), 0.0, 1.0)
                intensity_colors = np.column_stack((i_norm, i_norm, i_norm)).astype(np.float32)
            else:
                intensity_colors = None

            if hasattr(las, 'return_number'):
                extra_attrs['return_number'] = np.array(las.return_number[::step])
            if hasattr(las, 'scan_angle') or hasattr(las, 'scan_angle_rank'):
                sa = getattr(las, 'scan_angle', None) or getattr(las, 'scan_angle_rank', None)
                extra_attrs['scan_angle'] = np.array(sa[::step], dtype=np.float32)
            if hasattr(las, 'point_source_id'):
                extra_attrs['point_source_id'] = np.array(las.point_source_id[::step])
            if hasattr(las, 'nir'):
                extra_attrs['nir'] = np.array(las.nir[::step])
            if hasattr(las, 'withheld'):
                extra_attrs['withheld'] = np.array(las.withheld[::step])
            if hasattr(las, 'key_point'):
                extra_attrs['keypoint'] = np.array(las.key_point[::step])
            if hasattr(las, 'overlap'):
                extra_attrs['overlap'] = np.array(las.overlap[::step])

            pts_data = (x, y, z, rgb_colors, class_colors, intensity_colors, total_points)
    except Exception:
        pts_data = None

    # 2. If compressed (.laz / .copc.laz) and laspy failed, use PDAL
    if pts_data is None and file_path.lower().endswith(('.laz', '.copc.laz')):
        try:
            import subprocess, tempfile, shutil
            qgis_root = r"C:\Program Files\QGIS 3.40.14"
            pdal_candidates = [
                os.path.join(qgis_root, "bin", "pdal.exe"),
                os.path.join(qgis_root, "apps", "qgis-ltr", "bin", "pdal.exe"),
                shutil.which("pdal")
            ]
            pdal_exe = next((p for p in pdal_candidates if p and os.path.exists(p)), None)
            if pdal_exe:
                tmp_las = os.path.join(tempfile.gettempdir(), f"view3d_{os.getpid()}.las")
                env = os.environ.copy()
                proj_dir = os.path.join(qgis_root, "share", "proj")
                if os.path.exists(proj_dir):
                    env["PROJ_LIB"] = proj_dir
                    env["PROJ_DATA"] = proj_dir

                subprocess.run(
                    [pdal_exe, "translate", file_path, tmp_las, f"--readers.copc.count={max_points}"],
                    capture_output=True, env=env, timeout=20
                )
                if os.path.exists(tmp_las) and os.path.getsize(tmp_las) > 1024:
                    file_path = tmp_las
        except Exception:
            pass

    # 3. Universal binary parser for uncompressed LAS 1.0 - 1.4 formats
    if pts_data is None:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.gpkg', '.shp', '.geojson', '.json', '.kml']:
            raise ValueError(f"'{os.path.basename(file_path)}' is a GIS vector layer. Use PointCloudReader.load_vector_3d_points to render.")
        if ext in ['.tif', '.tiff', '.dem', '.asc', '.hgt']:
            raise ValueError(f"'{os.path.basename(file_path)}' is a raster/DEM layer. Use PointCloudReader.load_dem_points to render.")

        with open(file_path, 'rb') as f:
            header = f.read(375)
            if header[:4] != b'LASF':
                raise ValueError(f"'{os.path.basename(file_path)}' is not a valid standard LAS/LAZ point cloud dataset.")

            v_maj, v_min = header[24], header[25]
            hdr_sz, = struct.unpack('<H', header[94:96])
            offset_to_points, = struct.unpack('<I', header[96:100])
            point_format = header[104]
            point_len, = struct.unpack('<H', header[105:107])
            num_points_legacy, = struct.unpack('<I', header[107:111])
            x_scale, y_scale, z_scale = struct.unpack('<3d', header[131:155])
            x_off, y_off, z_off = struct.unpack('<3d', header[155:179])

            total_points = num_points_legacy
            if v_maj == 1 and v_min >= 4 and hdr_sz >= 375 and len(header) >= 255:
                try:
                    num_points_64, = struct.unpack('<Q', header[247:255])
                    if num_points_64 > 0:
                        total_points = num_points_64
                except Exception:
                    pass

            file_sz = os.path.getsize(file_path)
            avail_pts = (file_sz - offset_to_points) // point_len if point_len > 0 else 0
            total_points = min(total_points, avail_pts) if total_points > 0 else avail_pts
            if total_points <= 0:
                raise ValueError("Point cloud contains 0 points or invalid header.")

            step = max(1, total_points // max_points)
            m = np.memmap(
                file_path, dtype=np.uint8, mode='r',
                offset=offset_to_points, shape=(total_points, point_len)
            )
            raw = np.array(m[::step], copy=True)
            del m

            x_raw = np.ascontiguousarray(raw[:, 0:4]).view(np.int32).flatten()
            y_raw = np.ascontiguousarray(raw[:, 4:8]).view(np.int32).flatten()
            z_raw = np.ascontiguousarray(raw[:, 8:12]).view(np.int32).flatten()

            x = (x_raw * x_scale + x_off).astype(np.float64)
            y = (y_raw * y_scale + y_off).astype(np.float64)
            z = (z_raw * z_scale + z_off).astype(np.float32)

            rgb_offset = None
            if point_format in [2]:
                rgb_offset = 20 if point_len >= 26 else None
            elif point_format in [3, 5]:
                rgb_offset = 28 if point_len >= 34 else None
            elif point_format in [7, 8, 10]:
                rgb_offset = 30 if point_len >= 36 else None

            if rgb_offset is not None and point_len >= rgb_offset + 6:
                r_raw = np.ascontiguousarray(raw[:, rgb_offset:rgb_offset + 2]).view(np.uint16).flatten().astype(np.float32)
                g_raw = np.ascontiguousarray(raw[:, rgb_offset + 2:rgb_offset + 4]).view(np.uint16).flatten().astype(np.float32)
                b_raw = np.ascontiguousarray(raw[:, rgb_offset + 4:rgb_offset + 6]).view(np.uint16).flatten().astype(np.float32)
                max_c = max(float(np.max(r_raw)), float(np.max(g_raw)), float(np.max(b_raw)))
                if max_c > 255.0:
                    all_c = np.concatenate([r_raw, g_raw, b_raw])
                    p1 = max(0.0, float(np.percentile(all_c, 1)))
                    p99 = min(65535.0, float(np.percentile(all_c, 99)))
                    rng = max(1.0, p99 - p1)
                    r = np.clip((r_raw - p1) / rng, 0.0, 1.0).astype(np.float32)
                    g = np.clip((g_raw - p1) / rng, 0.0, 1.0).astype(np.float32)
                    b = np.clip((b_raw - p1) / rng, 0.0, 1.0).astype(np.float32)
                else:
                    r = (r_raw / 255.0).astype(np.float32)
                    g = (g_raw / 255.0).astype(np.float32)
                    b = (b_raw / 255.0).astype(np.float32)
                rgb_colors = np.column_stack((r, g, b)).astype(np.float32)
            else:
                rgb_colors = None

            class_byte_idx = 16 if point_format in [6, 7, 8, 9, 10] else 15
            if point_len > class_byte_idx:
                class_raw = raw[:, class_byte_idx].flatten()
                class_colors = apply_las_classification(class_raw)
            else:
                class_colors = None

            if point_len >= 14:
                intens_raw = raw[:, 12:14].view(np.uint16).flatten().astype(np.float32)
                i_min, i_max = np.percentile(intens_raw, [2, 98]) if len(intens_raw) > 0 else (0, 1)
                i_norm = np.clip((intens_raw - i_min) / max(1.0, i_max - i_min), 0.0, 1.0)
                intensity_colors = np.column_stack((i_norm, i_norm, i_norm)).astype(np.float32)
            else:
                intensity_colors = None

            pts_data = (x, y, z, rgb_colors, class_colors, intensity_colors, total_points)

    x, y, z, rgb_colors, class_colors, intensity_colors, total_points = pts_data
    return x, y, z, rgb_colors, class_colors, intensity_colors, total_points, extra_attrs
