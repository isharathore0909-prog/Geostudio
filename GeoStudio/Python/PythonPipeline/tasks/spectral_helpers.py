
# -*- coding: utf-8 -*-
"""
Spectral band resolution and sibling file discovery for Landsat and Sentinel scenes.
"""
import os
import re

def find_sibling_band(base_path: str, candidates: list) -> str | None:
    """Finds matching sibling band GeoTIFF in same directory for Landsat/Sentinel."""
    if not base_path or not os.path.exists(base_path):
        return None

    dir_name = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)

    # Match band identifier at end of filename, e.g. _B10, _ST_B10, _SR_B10, _B1, _B04
    match = re.search(r'(_(?:SR_|ST_|QA_)?B\d+)', base_name, re.IGNORECASE)
    if not match:
        match = re.search(r'(_B\d+)', base_name, re.IGNORECASE)

    for cand in candidates:
        # Normalize candidate to always have B prefix, e.g. B5
        c_tag = cand if cand.upper().startswith("B") else f"B{cand}"
        if match:
            # 1. Direct replacement without ST/SR
            cand_name = base_name[:match.start()] + f"_{c_tag}" + base_name[match.end():]
            cand_path = os.path.join(dir_name, cand_name)
            if os.path.exists(cand_path):
                return cand_path

            # 2. Try replacing with _SR_ (Surface Reflectance bands)
            prefix = base_name[:match.start()].replace("_ST_", "").replace("_SR_", "").rstrip("_")
            cand_name_sr = f"{prefix}_SR_{c_tag}" + base_name[match.end():]
            cand_path_sr = os.path.join(dir_name, cand_name_sr)
            if os.path.exists(cand_path_sr):
                return cand_path_sr

            # 3. Try replacing with _ST_
            cand_name_st = f"{prefix}_ST_{c_tag}" + base_name[match.end():]
            cand_path_st = os.path.join(dir_name, cand_name_st)
            if os.path.exists(cand_path_st):
                return cand_path_st

        # 4. Fallback: scan directory for matching pattern
        for f in os.listdir(dir_name):
            if f.lower().endswith(('.tif', '.tiff', '.jp2')):
                f_upper = f.upper()
                if f"_{c_tag.upper()}." in f_upper or f"_{c_tag.upper()}_" in f_upper:
                    return os.path.join(dir_name, f)

    return None

def align_shapes(arr, target_shape):
    """Aligns 2D numpy array to target (height, width) if resolutions differ."""
    if arr.shape == target_shape:
        return arr
    try:
        from scipy.ndimage import zoom
        zy = target_shape[0] / arr.shape[0]
        zx = target_shape[1] / arr.shape[1]
        return zoom(arr, (zy, zx), order=0)
    except Exception:
        import numpy as np
        out = np.zeros(target_shape, dtype=arr.dtype)
        min_y = min(arr.shape[0], target_shape[0])
        min_x = min(arr.shape[1], target_shape[1])
        out[:min_y, :min_x] = arr[:min_y, :min_x]
        return out

def read_band_array(ds, band_idx: int, file_path: str | None = None):
    """Reads float32 numpy array from dataset or individual file."""
    import numpy as np
    from osgeo import gdal

    if file_path and os.path.exists(file_path):
        b_ds = gdal.Open(file_path, gdal.GA_ReadOnly)
        arr = b_ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        b_ds = None
        return arr

    if ds and band_idx <= ds.RasterCount:
        return ds.GetRasterBand(band_idx).ReadAsArray().astype(np.float32)

    raise ValueError(f"Unable to read band {band_idx} from dataset or file {file_path}")

