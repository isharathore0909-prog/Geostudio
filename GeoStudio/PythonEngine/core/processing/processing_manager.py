# -*- coding: utf-8 -*-
"""
GeoStudio - Master Processing & Tile Execution Manager
Coordinates tiled window execution, CUDA / CPU backend selection, progress callbacks, and graceful fallback.
"""

import os
import time
import tempfile
from typing import Callable, Optional, Dict, Any

import numpy as np
from osgeo import gdal

from core.gpu.cuda_detector import CudaDetector
from core.gpu.vram_manager import VramManager
from core.gpu.cuda_kernels import CudaKernels
from core.gpu.gpu_fallback import CpuFallbackKernels
from .tile_manager import TileManager


class ProcessingManager:
    """Master controller that executes algorithms over streaming tiles with CUDA/CPU dispatch."""

    @classmethod
    def execute_tiled_raster_algorithm(
        cls,
        input_raster_path: str,
        output_raster_path: str,
        algo_name: str,
        params: Dict[str, Any],
        engine: str = "auto",  # "auto", "cuda", "cpu"
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        is_canceled: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Execute a raster algorithm tile-by-tile with bounded memory and optional CUDA GPU acceleration.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(val: float, status: str):
            if progress_callback:
                progress_callback(val, status)

        # 1. Open input dataset
        ds_in = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
        if not ds_in:
            raise RuntimeError(f"Could not open input raster: {input_raster_path}")

        raster_w = ds_in.RasterXSize
        raster_h = ds_in.RasterYSize
        geotransform = ds_in.GetGeoTransform()
        projection = ds_in.GetProjection()

        cellsize_x = abs(geotransform[1])
        cellsize_y = abs(geotransform[5])

        # 2. Determine backend engine & CUDA availability
        cuda_avail = CudaKernels.is_available()
        use_gpu = False

        if engine == "cuda":
            if not cuda_avail:
                log("<span style='color:#fbbf24;'>[Warning] CUDA requested but not available. Falling back to multi-threaded CPU.</span>")
                use_gpu = False
            else:
                use_gpu = True
        elif engine == "auto":
            use_gpu = cuda_avail
        else:
            use_gpu = False

        gpu_info = CudaDetector.get_gpu_info()
        if use_gpu:
            log(f"<b>Backend Engine:</b> <span style='color:#4ade80;'>CUDA GPU ({gpu_info['device_name']})</span>")
            log(f"Free VRAM: {gpu_info['free_vram_mb']:.0f} MB / Total: {gpu_info['total_vram_mb']:.0f} MB")
        else:
            log("<b>Backend Engine:</b> Multi-threaded CPU (NumPy/Vectorized)")

        # 3. Calculate optimal tile dimensions
        tile_w, tile_h = VramManager.calculate_tile_size(
            raster_width=raster_w,
            raster_height=raster_h,
            bytes_per_pixel=4,
            use_gpu=use_gpu
        )
        log(f"Calculated adaptive tile window: <b>{tile_w} × {tile_h} px</b>")

        # 4. Create output dataset
        driver = gdal.GetDriverByName("GTiff")
        # Optimization creation options: Tiled GeoTIFF with LZW compression
        options = ["TILED=YES", "BLOCKXSIZE=256", "BLOCKYSIZE=256", "COMPRESS=LZW", "BIGTIFF=IF_SAFER"]
        
        ds_out = driver.Create(output_raster_path, raster_w, raster_h, 1, gdal.GDT_Float32, options)
        if not ds_out:
            raise RuntimeError(f"Could not create output file: {output_raster_path}")

        ds_out.SetGeoTransform(geotransform)
        ds_out.SetProjection(projection)

        # 5. Halo requirements for 3x3 algorithms
        halo = 1 if algo_name in ("slope", "aspect", "hillshade", "tri", "tpi", "twi", "curvature", "focal") else 0
        windows = list(TileManager.generate_windows(raster_w, raster_h, tile_w, tile_h, halo=halo))
        total_tiles = len(windows)
        log(f"Processing total of <b>{total_tiles}</b> tiles...")

        start_time = time.time()

        # 6. Stream tiles
        for window in windows:
            if is_canceled and is_canceled():
                log("<span style='color:#f87171;'>Processing cancelled by user.</span>")
                ds_out = None
                ds_in = None
                return False

            # Read tile
            tile_data = TileManager.read_tile(ds_in, 1, window)

            # Compute tile result
            out_tile = None
            if use_gpu:
                try:
                    if algo_name in ("slope", "aspect", "hillshade", "tri", "tpi", "twi", "curvature"):
                        out_tile = CudaKernels.compute_slope_aspect_hillshade(
                            dem_tile=tile_data,
                            cellsize_x=cellsize_x,
                            cellsize_y=cellsize_y,
                            z_factor=params.get("z_factor", 1.0),
                            azimuth_deg=params.get("azimuth", 315.0),
                            altitude_deg=params.get("altitude", 45.0),
                            mode=algo_name
                        )
                except Exception as gpu_err:
                    log(f"<span style='color:#fbbf24;'>[GPU Error on tile {window.tile_index+1}]: {gpu_err}. Falling back to CPU for remaining tiles.</span>")
                    use_gpu = False

            if out_tile is None:
                # CPU computation
                out_tile = CpuFallbackKernels.compute_slope_aspect_hillshade(
                    dem_tile=tile_data,
                    cellsize_x=cellsize_x,
                    cellsize_y=cellsize_y,
                    z_factor=params.get("z_factor", 1.0),
                    azimuth_deg=params.get("azimuth", 315.0),
                    altitude_deg=params.get("altitude", 45.0),
                    mode=algo_name
                )

            # Write tile result to output
            TileManager.write_tile(ds_out, 1, window, out_tile)

            # Update progress
            pct = ((window.tile_index + 1) / total_tiles) * 100.0
            progress(pct, f"Processing tile {window.tile_index + 1} of {total_tiles} ({pct:.0f}%)")

        # 7. Finalize & Flush
        ds_out.FlushCache()
        ds_out = None
        ds_in = None

        elapsed = time.time() - start_time
        log(f"<span style='color:#4ade80;'>Finished processing {total_tiles} tiles in <b>{elapsed:.2f} s</b> ({raster_w*raster_h/1e6/elapsed:.2f} Mpixels/s).</span>")
        return True
