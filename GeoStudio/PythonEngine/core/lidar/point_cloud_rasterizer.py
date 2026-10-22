# -*- coding: utf-8 -*-
"""
GeoStudio - High-Performance Point Cloud Surface Rasterizer
Generates geo-referenced 2D surfaces with void hole filling, RGB true color,
Turbo elevation palettes, and ambient terrain relief from LAS/LAZ point clouds.
"""

import os
import time
import struct
import tempfile
import numpy as np
try:
    from osgeo import gdal, osr
except ImportError:
    try:
        import gdal
        import osr
    except ImportError:
        gdal = None
        osr = None


class PointCloudRasterizer:
    """Fast LAS/LAZ point cloud surface generator."""

    @staticmethod
    def turbo_colormap(norm_vals: np.ndarray) -> np.ndarray:
        """Turbo scientific colormap vectorization returning uint8 RGB."""
        x = np.clip(norm_vals, 0.0, 1.0)
        r = 0.1357 + x * (4.5974 - x * (42.681 - x * (152.58 - x * (221.38 - x * 111.4))))
        g = 0.0914 + x * (2.1856 + x * (4.8052 - x * (14.095 - x * (4.2115 - x * 10.36))))
        b = 0.1067 + x * (12.585 - x * (60.118 - x * (109.07 - x * (88.5 - x * 26.85))))
        rgb = np.clip(np.column_stack((r, g, b)), 0.0, 1.0)
        return (rgb * 255.0).astype(np.uint8)

    @classmethod
    def generate_las_surface(cls, las_path: str, max_points: int = 35_000_000) -> str:
        """Generates a high-speed geo-referenced 2D surface raster directly from LAS points."""
        clean_base = os.path.splitext(os.path.basename(las_path))[0]
        out_tif = os.path.join(tempfile.gettempdir(), f"geostudio_lidar_{clean_base}_{int(time.time())}.tif")

        try:
            with open(las_path, 'rb') as f:
                header = f.read(375)
                if header[:4] != b'LASF':
                    return None

                v_maj, v_min = header[24], header[25]
                hdr_sz, = struct.unpack('<H', header[94:96])
                offset_to_points, = struct.unpack('<I', header[96:100])
                point_format, point_len = struct.unpack('<BH', header[104:107])
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

            file_sz = os.path.getsize(las_path)
            avail_pts = (file_sz - offset_to_points) // point_len if point_len > 0 else 0
            total_points = min(total_points, avail_pts) if total_points > 0 else avail_pts
            if total_points <= 0:
                return None

            step = max(1, total_points // max_points)
            m = np.memmap(las_path, dtype=np.uint8, mode='r', offset=offset_to_points, shape=(total_points, point_len))
            raw = np.array(m[::step], copy=True)
            del m

            x_raw = np.ascontiguousarray(raw[:, 0:4]).view(np.int32).flatten()
            y_raw = np.ascontiguousarray(raw[:, 4:8]).view(np.int32).flatten()
            z_raw = np.ascontiguousarray(raw[:, 8:12]).view(np.int32).flatten()

            x = (x_raw * x_scale + x_off).astype(np.float64)
            y = (y_raw * y_scale + y_off).astype(np.float64)
            z = (z_raw * z_scale + z_off).astype(np.float32)

            # Determine RGB byte offset based on LAS point format (0-10)
            rgb_offset = None
            if point_format in [2]:
                rgb_offset = 20 if point_len >= 26 else None
            elif point_format in [3, 5]:
                rgb_offset = 28 if point_len >= 34 else None
            elif point_format in [7, 8, 10]:
                rgb_offset = 30 if point_len >= 36 else None

            if rgb_offset is not None and point_len >= rgb_offset + 6:
                r_raw = np.ascontiguousarray(raw[:, rgb_offset:rgb_offset + 2]).view(np.uint16).flatten()
                g_raw = np.ascontiguousarray(raw[:, rgb_offset + 2:rgb_offset + 4]).view(np.uint16).flatten()
                b_raw = np.ascontiguousarray(raw[:, rgb_offset + 4:rgb_offset + 6]).view(np.uint16).flatten()
                if np.max(r_raw) > 255 or np.max(g_raw) > 255 or np.max(b_raw) > 255:
                    r_raw = (r_raw >> 8).astype(np.uint8)
                    g_raw = (g_raw >> 8).astype(np.uint8)
                    b_raw = (b_raw >> 8).astype(np.uint8)
                else:
                    r_raw = r_raw.astype(np.uint8)
                    g_raw = g_raw.astype(np.uint8)
                    b_raw = b_raw.astype(np.uint8)
                has_rgb = True
            else:
                has_rgb = False
                r_raw, g_raw, b_raw = None, None, None

        except Exception:
            return None

        # Filter valid coordinates
        valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        valid &= ~((x == 0.0) & (y == 0.0))
        if not np.any(valid):
            return None

        x_v = x[valid]
        y_v = y[valid]
        z_v = z[valid]

        min_x_act = float(np.min(x_v))
        max_x_act = float(np.max(x_v))
        min_y_act = float(np.min(y_v))
        max_y_act = float(np.max(y_v))

        crs_wkt = None
        try:
            from qgis.core import QgsPointCloudLayer
            probe = QgsPointCloudLayer(las_path, "probe", "pdal")
            if not probe.isValid():
                probe = QgsPointCloudLayer(las_path, "probe", "copc")
            if probe.isValid() and probe.crs().isValid():
                crs_wkt = probe.crs().toWkt()
        except Exception:
            pass

        if not crs_wkt:
            srs = osr.SpatialReference()
            if abs(min_x_act) <= 180 and abs(max_y_act) <= 90:
                srs.ImportFromEPSG(4326)
            else:
                srs.ImportFromEPSG(32643)
            crs_wkt = srs.ExportToWkt()

        span_x = max(1e-9, max_x_act - min_x_act)
        span_y = max(1e-9, max_y_act - min_y_act)

        target_max_dim = 4500
        aspect = span_x / max(1e-9, span_y)
        if aspect >= 1.0:
            grid_w = min(6144, max(1024, target_max_dim))
            grid_h = min(6144, max(1024, int(round(target_max_dim / aspect))))
        else:
            grid_h = min(6144, max(1024, target_max_dim))
            grid_w = min(6144, max(1024, int(round(target_max_dim * aspect))))

        res_x = span_x / grid_w
        res_y = span_y / grid_h

        px = np.clip(((x_v - min_x_act) / span_x * (grid_w - 1)).astype(int), 0, grid_w - 1)
        py = np.clip(((max_y_act - y_v) / span_y * (grid_h - 1)).astype(int), 0, grid_h - 1)

        order = np.argsort(z_v)
        px_s = px[order]
        py_s = py[order]
        z_s = z_v[order]

        img_r = np.zeros((grid_h, grid_w), dtype=np.uint8)
        img_g = np.zeros((grid_h, grid_w), dtype=np.uint8)
        img_b = np.zeros((grid_h, grid_w), dtype=np.uint8)
        img_a = np.zeros((grid_h, grid_w), dtype=np.uint8)
        grid_z = np.full((grid_h, grid_w), np.nan, dtype=np.float32)

        if has_rgb and r_raw is not None:
            r_v = r_raw[valid][order]
            g_v = g_raw[valid][order]
            b_v = b_raw[valid][order]
            if not (np.all(r_v == 0) and np.all(g_v == 0) and np.all(b_v == 0)):
                colors = np.column_stack((r_v, g_v, b_v))
            else:
                z_min_p, z_max_p = np.percentile(z_s, [1.0, 99.0])
                z_norm = np.clip((z_s - z_min_p) / max(0.01, float(z_max_p - z_min_p)), 0.0, 1.0)
                colors = cls.turbo_colormap(z_norm)
        else:
            z_min_p, z_max_p = np.percentile(z_s, [1.0, 99.0])
            z_norm = np.clip((z_s - z_min_p) / max(0.01, float(z_max_p - z_min_p)), 0.0, 1.0)
            colors = cls.turbo_colormap(z_norm)

        img_r[py_s, px_s] = colors[:, 0]
        img_g[py_s, px_s] = colors[:, 1]
        img_b[py_s, px_s] = colors[:, 2]
        img_a[py_s, px_s] = 255
        grid_z[py_s, px_s] = z_s

        # Infill holes
        try:
            from scipy.ndimage import distance_transform_edt, binary_fill_holes, binary_closing
            valid_mask = img_a > 0
            ds_factor = 4
            m_sm = valid_mask[::ds_factor, ::ds_factor]
            cl_sm = binary_closing(m_sm, structure=np.ones((3, 3)))
            fill_sm = binary_fill_holes(cl_sm)
            fill_full = np.repeat(np.repeat(fill_sm, ds_factor, axis=0), ds_factor, axis=1)[:grid_h, :grid_w]
            infill_mask = fill_full & (~valid_mask)

            if np.any(infill_mask):
                distances, indices = distance_transform_edt(~valid_mask, return_indices=True)
                img_r[infill_mask] = img_r[indices[0][infill_mask], indices[1][infill_mask]]
                img_g[infill_mask] = img_g[indices[0][infill_mask], indices[1][infill_mask]]
                img_b[infill_mask] = img_b[indices[0][infill_mask], indices[1][infill_mask]]
                grid_z[infill_mask] = grid_z[indices[0][infill_mask], indices[1][infill_mask]]
                img_a[infill_mask] = 255
        except Exception:
            pass

        # 3D ambient shading
        try:
            z_filled = np.copy(grid_z)
            z_filled[np.isnan(z_filled)] = np.nanmin(grid_z)

            gy, gx = np.gradient(z_filled, res_y, res_x)
            slope = np.arctan(np.sqrt(gx**2 + gy**2))
            aspect_rad = np.arctan2(-gx, gy)

            zenith_rad = np.radians(90.0 - 45.0)
            azimuth_rad = np.radians(315.0)

            shaded = np.sin(zenith_rad) * np.cos(slope) + np.cos(zenith_rad) * np.sin(slope) * np.cos(azimuth_rad - aspect_rad)
            shaded = np.clip(shaded, 0.0, 1.0)
            shade_factor = 0.72 + 0.38 * shaded

            r_shaded = np.clip(img_r.astype(np.float32) * shade_factor, 0, 255).astype(np.uint8)
            g_shaded = np.clip(img_g.astype(np.float32) * shade_factor, 0, 255).astype(np.uint8)
            b_shaded = np.clip(img_b.astype(np.float32) * shade_factor, 0, 255).astype(np.uint8)

            bg = img_a == 0
            r_shaded[bg] = 0
            g_shaded[bg] = 0
            b_shaded[bg] = 0
        except Exception:
            r_shaded, g_shaded, b_shaded = img_r, img_g, img_b

        if os.path.exists(out_tif):
            try:
                os.remove(out_tif)
            except Exception:
                pass

        drv = gdal.GetDriverByName('GTiff')
        ds = drv.Create(out_tif, grid_w, grid_h, 4, gdal.GDT_Byte, ['COMPRESS=DEFLATE', 'TILED=YES', 'PREDICTOR=2'])
        ds.SetGeoTransform([min_x_act, res_x, 0, max_y_act, 0, -res_y])
        if crs_wkt:
            ds.SetProjection(crs_wkt)

        ds.GetRasterBand(1).WriteArray(r_shaded)
        ds.GetRasterBand(2).WriteArray(g_shaded)
        ds.GetRasterBand(3).WriteArray(b_shaded)
        ds.GetRasterBand(4).WriteArray(img_a)

        ds.FlushCache()
        ds = None

        return out_tif
