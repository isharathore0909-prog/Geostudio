# -*- coding: utf-8 -*-
"""
GeoStudio - Advanced Earthwork Cut & Fill Calculation Engine
Computes excavation, embankment, swell/shrinkage factors, optimal balance plane,
and generates differential GeoTIFFs and daylight isolines.
"""

import os
import tempfile
from typing import Optional, Union, Callable, Any
import numpy as np
from osgeo import gdal, ogr, osr

from .cut_fill_models import CutFillResult
from .cut_fill_reports import generate_report_text, export_csv


class CutFillEngine:
    """Core mathematical engine for Earthwork Cut & Fill calculations."""

    generate_report_text = staticmethod(generate_report_text)
    export_csv = staticmethod(export_csv)

    @staticmethod
    def compute_cut_fill(
        base_source: Union[str, Any],
        comp_source: Optional[Union[str, Any]] = None,
        datum_elevation: Optional[float] = None,
        swell_factor: float = 1.0,
        shrinkage_factor: float = 1.0,
        output_diff_path: Optional[str] = None,
        generate_daylight_vector: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> CutFillResult:
        """
        Executes complete Cut & Fill earthwork analysis.
        """
        if progress_callback: progress_callback(5.0, "Reading input DEM datasets...")

        base_path = base_source
        base_name = "Base DEM"
        if hasattr(base_source, "source") and hasattr(base_source, "name"):
            base_path = getattr(base_source, "_raw_dem_source", base_source.source())
            base_name = base_source.name()
        elif isinstance(base_source, str):
            base_name = os.path.splitext(os.path.basename(base_source))[0]

        is_datum_mode = (comp_source is None)

        ds_base = gdal.Open(base_path, gdal.GA_ReadOnly)
        if not ds_base:
            raise RuntimeError(f"Could not open base DEM: {base_path}")

        gt_base = ds_base.GetGeoTransform()
        proj_base = ds_base.GetProjection()
        w_base = ds_base.RasterXSize
        h_base = ds_base.RasterYSize
        dx = abs(gt_base[1])
        dy = abs(gt_base[5])
        cell_area = dx * dy

        b_base = ds_base.GetRasterBand(1)
        nodata_base = b_base.GetNoDataValue()
        arr_base = b_base.ReadAsArray().astype(np.float32)
        b_base = None
        ds_base = None

        if nodata_base is not None:
            arr_base = np.where(arr_base == nodata_base, np.nan, arr_base)

        if progress_callback: progress_callback(25.0, "Extracting elevation matrices...")

        if is_datum_mode:
            if datum_elevation is None:
                valid_elevs = arr_base[~np.isnan(arr_base)]
                datum_elevation = float(np.mean(valid_elevs)) if len(valid_elevs) > 0 else 0.0
            comp_name = f"Datum Plane ({datum_elevation:.2f} m)"
            diff = float(datum_elevation) - arr_base
        else:
            comp_path = comp_source
            comp_name = "Design DEM"
            if hasattr(comp_source, "source") and hasattr(comp_source, "name"):
                comp_path = getattr(comp_source, "_raw_dem_source", comp_source.source())
                comp_name = comp_source.name()
            elif isinstance(comp_source, str):
                comp_name = os.path.splitext(os.path.basename(comp_source))[0]

            if progress_callback: progress_callback(35.0, "Aligning and co-registering dual DEM surfaces...")
            ds_comp = gdal.Open(comp_path, gdal.GA_ReadOnly)
            if not ds_comp:
                raise RuntimeError(f"Could not open comparison DEM: {comp_path}")

            gt_comp = ds_comp.GetGeoTransform()
            if (gt_base == gt_comp and w_base == ds_comp.RasterXSize and h_base == ds_comp.RasterYSize):
                b_comp = ds_comp.GetRasterBand(1)
                nodata_comp = b_comp.GetNoDataValue()
                arr_comp = b_comp.ReadAsArray().astype(np.float32)
                b_comp = None
                if nodata_comp is not None:
                    arr_comp = np.where(arr_comp == nodata_comp, np.nan, arr_comp)
            else:
                warp_options = gdal.WarpOptions(
                    format="MEM",
                    outputBounds=[gt_base[0], gt_base[3] + gt_base[5] * h_base, gt_base[0] + gt_base[1] * w_base, gt_base[3]],
                    width=w_base,
                    height=h_base,
                    resampleAlg=gdal.GRA_Bilinear,
                    dstSRS=proj_base
                )
                ds_warped = gdal.Warp("", ds_comp, options=warp_options)
                b_comp = ds_warped.GetRasterBand(1)
                nodata_comp = b_comp.GetNoDataValue()
                arr_comp = b_comp.ReadAsArray().astype(np.float32)
                b_comp = None
                ds_warped = None
                if nodata_comp is not None:
                    arr_comp = np.where(arr_comp == nodata_comp, np.nan, arr_comp)

            ds_comp = None
            diff = arr_comp - arr_base

        if progress_callback: progress_callback(55.0, "Computing volumetric balance...")

        valid_mask = ~np.isnan(diff)
        valid_diff = diff[valid_mask]
        total_cells = len(valid_diff)

        if total_cells == 0:
            raise ValueError("No overlapping or valid elevation pixels between datasets.")

        total_area_m2 = total_cells * cell_area
        total_area_ha = total_area_m2 / 10000.0

        cut_mask = valid_diff < -0.005
        fill_mask = valid_diff > 0.005
        daylight_mask = np.abs(valid_diff) <= 0.005

        cut_cells = int(np.sum(cut_mask))
        fill_cells = int(np.sum(fill_mask))
        daylight_cells = int(np.sum(daylight_mask))

        cut_area_m2 = cut_cells * cell_area
        fill_area_m2 = fill_cells * cell_area
        daylight_area_m2 = daylight_cells * cell_area

        gross_cut_vol = float(np.sum(np.abs(valid_diff[cut_mask])) * cell_area)
        gross_fill_vol = float(np.sum(valid_diff[fill_mask]) * cell_area)

        factored_cut_vol = gross_cut_vol * float(swell_factor)
        factored_fill_vol = gross_fill_vol * float(shrinkage_factor)

        net_vol = factored_cut_vol - factored_fill_vol
        ratio = (factored_cut_vol / factored_fill_vol) if factored_fill_vol > 0 else 999.0

        max_cut = float(np.max(np.abs(valid_diff[cut_mask]))) if cut_cells > 0 else 0.0
        mean_cut = float(np.mean(np.abs(valid_diff[cut_mask]))) if cut_cells > 0 else 0.0
        max_fill = float(np.max(valid_diff[fill_mask])) if fill_cells > 0 else 0.0
        mean_fill = float(np.mean(valid_diff[fill_mask])) if fill_cells > 0 else 0.0

        # Save difference GeoTIFF
        if output_diff_path is None:
            output_diff_path = tempfile.mktemp(suffix="_cutfill_diff.tif")

        if progress_callback: progress_callback(75.0, "Generating difference raster GeoTIFF...")
        driver = gdal.GetDriverByName("GTiff")
        ds_out = driver.Create(
            output_diff_path, w_base, h_base, 1, gdal.GDT_Float32,
            ["TILED=YES", "COMPRESS=LZW", "BIGTIFF=IF_SAFER"]
        )
        ds_out.SetGeoTransform(gt_base)
        ds_out.SetProjection(proj_base)
        b_out = ds_out.GetRasterBand(1)
        b_out.SetNoDataValue(-9999.0)
        diff_out = np.where(np.isnan(diff), -9999.0, diff)
        b_out.WriteArray(diff_out)
        b_out.FlushCache()
        b_out = None
        ds_out = None

        daylight_shp_path = None
        if generate_daylight_vector:
            if progress_callback: progress_callback(85.0, "Extracting zero-grade daylight boundary line...")
            try:
                base_vec_dir = os.path.dirname(output_diff_path)
                daylight_shp_path = os.path.join(base_vec_dir, f"{os.path.splitext(os.path.basename(output_diff_path))[0]}_daylight.gpkg")

                ogr_driver = ogr.GetDriverByName("GPKG")
                if os.path.exists(daylight_shp_path):
                    ogr_driver.DeleteDataSource(daylight_shp_path)

                out_ds_vec = ogr_driver.CreateDataSource(daylight_shp_path)
                srs = osr.SpatialReference()
                srs.ImportFromWkt(proj_base)
                out_lyr = out_ds_vec.CreateLayer("daylight_contour", srs, ogr.wkbLineString)

                fld_id = ogr.FieldDefn("ID", ogr.OFTInteger)
                fld_val = ogr.FieldDefn("ELEV", ogr.OFTReal)
                out_lyr.CreateField(fld_id)
                out_lyr.CreateField(fld_val)

                ds_read = gdal.Open(output_diff_path, gdal.GA_ReadOnly)
                if ds_read:
                    b_read = ds_read.GetRasterBand(1)
                    gdal.ContourGenerate(
                        b_read, 0.0, 0.0, [0.0],
                        1, -9999.0,
                        out_lyr, 0, 1
                    )
                    out_ds_vec.FlushCache()
                    del out_lyr, fld_id, fld_val
                    out_ds_vec = None
                    b_read = None
                    ds_read = None
            except Exception:
                daylight_shp_path = None

        if progress_callback: progress_callback(100.0, "Calculations completed successfully.")

        return CutFillResult(
            base_name=base_name,
            comp_name=comp_name,
            is_datum_mode=is_datum_mode,
            datum_elevation=float(datum_elevation) if is_datum_mode else None,
            total_analyzed_area_m2=total_area_m2,
            total_analyzed_area_ha=total_area_ha,
            cut_area_m2=cut_area_m2,
            fill_area_m2=fill_area_m2,
            daylight_area_m2=daylight_area_m2,
            gross_cut_volume_m3=gross_cut_vol,
            gross_fill_volume_m3=gross_fill_vol,
            swell_factor=swell_factor,
            shrinkage_factor=shrinkage_factor,
            factored_cut_volume_m3=factored_cut_vol,
            factored_fill_volume_m3=factored_fill_vol,
            net_earthwork_volume_m3=net_vol,
            cut_fill_ratio=ratio,
            max_cut_depth_m=max_cut,
            mean_cut_depth_m=mean_cut,
            max_fill_depth_m=max_fill,
            mean_fill_depth_m=mean_fill,
            diff_raster_path=output_diff_path,
            daylight_vector_path=daylight_shp_path
        )

    @staticmethod
    def find_optimal_balance_plane(
        base_source: Union[str, Any],
        swell_factor: float = 1.0,
        shrinkage_factor: float = 1.0
    ) -> float:
        """
        Solves for the horizontal flat elevation plane that yields Net Earthwork Volume = 0.
        """
        file_path = base_source
        if hasattr(base_source, "source"):
            file_path = getattr(base_source, "_raw_dem_source", base_source.source())

        ds = gdal.Open(file_path, gdal.GA_ReadOnly)
        if not ds:
            raise RuntimeError(f"Could not open DEM: {file_path}")

        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        arr = band.ReadAsArray().astype(np.float32)
        band = None
        ds = None

        if nodata is not None:
            arr = arr[arr != nodata]
        arr = arr[~np.isnan(arr)]

        if len(arr) == 0:
            return 0.0

        low = float(np.min(arr))
        high = float(np.max(arr))

        def net_func(datum: float) -> float:
            diff = datum - arr
            c_mask = diff < 0.0
            f_mask = diff > 0.0
            c_vol = np.sum(np.abs(diff[c_mask])) * swell_factor
            f_vol = np.sum(diff[f_mask]) * shrinkage_factor
            return c_vol - f_vol

        for _ in range(35):
            mid = (low + high) / 2.0
            val = net_func(mid)
            if abs(val) < 0.001:
                return float(mid)
            if val > 0:
                low = mid
            else:
                high = mid

        return float((low + high) / 2.0)
