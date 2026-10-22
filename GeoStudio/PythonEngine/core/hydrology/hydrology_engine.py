# -*- coding: utf-8 -*-
"""
GeoStudio - Hydrology & Watershed Analysis Engine
Comprehensive hydrological modeling suite:
- Priority-Flood Depression Filling (Sink Removal)
- Garbrecht & Martz Flat Area Flow Routing (Shortest Path to Spill-Points)
- D8 Steepest Slope Flow Direction Routing
- High-Performance Linear Topological Flow Accumulation
- Strahler Stream Network Extraction
- Complete Catchment & Drainage Basin Delineation
"""

import os
import time
from typing import Callable, Optional, Dict, Any, Tuple
import numpy as np
import scipy.ndimage as ndi
from osgeo import gdal

from .sink_filling import fill_sinks_array
from .flow_routing import flow_direction_array, flow_accumulation_array
from .watershed_delineation import stream_network_array, delineate_watersheds_array


class HydrologyEngine:
    """Master computational engine for raster hydrology and watershed delineation."""

    # Re-expose standalone functional algorithms as static methods for full backward compatibility
    fill_sinks_array = staticmethod(fill_sinks_array)
    flow_direction_array = staticmethod(flow_direction_array)
    flow_accumulation_array = staticmethod(flow_accumulation_array)
    stream_network_array = staticmethod(stream_network_array)
    delineate_watersheds_array = staticmethod(delineate_watersheds_array)

    @classmethod
    def execute_hydrology_algorithm(
        cls,
        input_raster_path: str,
        output_raster_path: str,
        algo_id: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        is_canceled: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Execute full-extent hydrological modeling workflows with progress updates.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(val: float, status: str):
            if progress_callback:
                progress_callback(val, status)

        log(f"<b>Reading DEM raster:</b> <code>{os.path.basename(input_raster_path)}</code>")
        progress(5.0, "Reading DEM...")

        ds_in = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
        if not ds_in:
            raise RuntimeError(f"Could not open input raster: {input_raster_path}")

        raster_w = ds_in.RasterXSize
        raster_h = ds_in.RasterYSize
        geotransform = ds_in.GetGeoTransform()
        projection = ds_in.GetProjection()
        band_in = ds_in.GetRasterBand(1)
        nodata_val = band_in.GetNoDataValue()

        dem = band_in.ReadAsArray().astype(np.float32)
        band_in = None
        ds_in = None

        cellsize_x = abs(geotransform[1])
        cellsize_y = abs(geotransform[5])
        total_cells = raster_w * raster_h

        # Optional DSM smoothing to remove micro-vegetation noise
        smooth_dsm = params.get("smooth_surface", False)
        if smooth_dsm or ("dsm" in os.path.basename(input_raster_path).lower() and params.get("auto_smooth_dsm", True)):
            log("Applying mild Gaussian terrain filter to eliminate DSM tree canopy noise...")
            dem = ndi.gaussian_filter(dem, sigma=1.0)

        log(f"Grid dimensions: <b>{raster_w} × {raster_h} px</b> ({total_cells/1e6:.2f} Mpixels), Resolution: <b>{cellsize_x:.2f} × {cellsize_y:.2f} m</b>")

        start_time = time.time()
        out_data = None
        out_dtype = gdal.GDT_Float32
        out_nodata = nodata_val if nodata_val is not None else -9999.0

        auto_fill = params.get("auto_fill_sinks", True)

        if algo_id in ("hydrology:fillsinks", "fillsinks"):
            log("Running <b>Priority-Flood depression filling</b>...")
            progress(10.0, "Filling sinks...")
            out_data = fill_sinks_array(
                dem, nodata_val=nodata_val,
                progress_cb=progress, is_canceled=is_canceled
            )
            out_dtype = gdal.GDT_Float32

        elif algo_id in ("hydrology:flowdir", "flowdir"):
            if auto_fill:
                log("Pre-processing: Filling sinks and depressions...")
                progress(10.0, "Filling depressions...")
                dem = fill_sinks_array(dem, nodata_val=nodata_val, progress_cb=progress, is_canceled=is_canceled)

            log("Computing <b>D8 Flow Direction</b> (with Garbrecht & Martz Flat Resolution)...")
            progress(50.0, "Calculating flow directions...")
            flowdir, _ = flow_direction_array(dem, cellsize_x, cellsize_y, nodata_val=nodata_val)
            out_data = flowdir.astype(np.float32)
            out_dtype = gdal.GDT_Byte
            out_nodata = 255

        elif algo_id in ("hydrology:flowaccum", "flowaccum"):
            if auto_fill:
                log("Pre-processing: Filling sinks and depressions...")
                progress(10.0, "Filling depressions...")
                dem = fill_sinks_array(dem, nodata_val=nodata_val, progress_cb=progress, is_canceled=is_canceled)

            log("Computing <b>D8 Flow Direction</b>...")
            progress(40.0, "Routing flow...")
            flowdir, nodata_mask = flow_direction_array(dem, cellsize_x, cellsize_y, nodata_val=nodata_val)

            log("Computing <b>Flow Accumulation</b>...")
            progress(60.0, "Accumulating upslope area...")
            accum, _ = flow_accumulation_array(flowdir, nodata_mask=nodata_mask)
            out_data = accum
            out_dtype = gdal.GDT_Float32
            out_nodata = -9999.0

        elif algo_id in ("hydrology:stream_network", "stream_network"):
            if auto_fill:
                log("Pre-processing: Filling sinks and depressions...")
                progress(10.0, "Filling depressions...")
                dem = fill_sinks_array(dem, nodata_val=nodata_val, progress_cb=progress, is_canceled=is_canceled)

            progress(35.0, "Routing flow...")
            flowdir, nodata_mask = flow_direction_array(dem, cellsize_x, cellsize_y, nodata_val=nodata_val)

            progress(50.0, "Accumulating flow...")
            accum, _ = flow_accumulation_array(flowdir, nodata_mask=nodata_mask)

            thresh = params.get("threshold", 0)
            if thresh <= 0:
                thresh = 2000
            log(f"Extracting Stream Channels (Threshold: <b>{thresh} cells</b> / <b>{thresh*cellsize_x*cellsize_y/1e4:.2f} ha</b>)...")

            progress(75.0, "Computing Strahler stream orders...")
            strahler = stream_network_array(accum, flowdir, threshold=thresh, nodata_mask=nodata_mask)
            out_data = strahler.astype(np.int32)
            out_dtype = gdal.GDT_Int32
            out_nodata = -9999

        elif algo_id in ("hydrology:watershed", "watershed"):
            if auto_fill:
                log("Pre-processing: Filling sinks and depressions...")
                progress(10.0, "Filling depressions...")
                dem = fill_sinks_array(dem, nodata_val=nodata_val, progress_cb=progress, is_canceled=is_canceled)

            progress(35.0, "Routing flow...")
            flowdir, nodata_mask = flow_direction_array(dem, cellsize_x, cellsize_y, nodata_val=nodata_val)

            progress(55.0, "Accumulating flow...")
            accum, flat_targets = flow_accumulation_array(flowdir, nodata_mask=nodata_mask)

            thresh = params.get("threshold", 0)
            if thresh <= 0:
                thresh = 2000
            log(f"Delineating Catchment Basins (Stream Threshold: <b>{thresh} cells</b>)...")

            progress(75.0, "Delineating catchment basins...")
            basins = delineate_watersheds_array(flowdir, accum, flat_targets, threshold=thresh, nodata_mask=nodata_mask)
            num_basins = int(np.max(basins))
            log(f"Successfully delineated <b>{num_basins}</b> distinct hydrological drainage catchments.")

            out_data = basins.astype(np.int32)
            out_dtype = gdal.GDT_Int32
            out_nodata = -9999

        else:
            raise ValueError(f"Unknown hydrology algorithm: {algo_id}")

        if is_canceled and is_canceled():
            return False

        progress(90.0, "Saving GeoTIFF output...")
        driver = gdal.GetDriverByName("GTiff")
        options = ["TILED=YES", "BLOCKXSIZE=256", "BLOCKYSIZE=256", "COMPRESS=LZW", "BIGTIFF=IF_SAFER"]
        ds_out = driver.Create(output_raster_path, raster_w, raster_h, 1, out_dtype, options)
        if not ds_out:
            raise RuntimeError(f"Could not create output GeoTIFF: {output_raster_path}")

        ds_out.SetGeoTransform(geotransform)
        ds_out.SetProjection(projection)
        band_out = ds_out.GetRasterBand(1)
        if out_nodata is not None:
            band_out.SetNoDataValue(float(out_nodata))

        band_out.WriteArray(out_data)

        try:
            valid_out = out_data[out_data != out_nodata] if out_nodata is not None else out_data
            if len(valid_out) > 0:
                band_out.SetStatistics(
                    float(np.min(valid_out)), float(np.max(valid_out)),
                    float(np.mean(valid_out)), float(np.std(valid_out))
                )
        except Exception:
            pass

        band_out.FlushCache()
        band_out = None
        ds_out = None

        elapsed = time.time() - start_time
        progress(100.0, "Complete")
        log(f"<span style='color:#4ade80;'>Hydrological analysis finished successfully in <b>{elapsed:.2f} s</b> ({total_cells/1e6/elapsed:.2f} Mpixels/s).</span>")
        return True
