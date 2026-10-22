# -*- coding: utf-8 -*-
"""
GeoStudio - High-Performance Volumetric Analysis & Stage-Storage Engine
Calculates spatial volumes, hypsometric curves, and storage capacities from DEM rasters.
"""

import os
import csv
import io
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from osgeo import gdal


@dataclass
class StageStorageStep:
    """Represents a single step in a stage-storage / elevation capacity curve."""
    stage_index: int
    elevation_m: float
    stage_height_m: float
    surface_area_m2: float
    surface_area_ha: float
    volume_above_m3: float
    volume_below_m3: float
    cumulative_capacity_m3: float


@dataclass
class VolumetricResult:
    """Holds analytical results for a volumetric analysis execution."""
    layer_name: str
    datum_elevation: float
    total_valid_cells: int
    cell_size_x: float
    cell_size_y: float
    cell_area_m2: float
    total_surface_area_m2: float
    total_surface_area_ha: float
    
    # Elevation extremes
    min_elevation_m: float
    max_elevation_m: float
    mean_elevation_m: float
    elevation_range_m: float
    
    # Volumetrics above/below datum
    volume_above_m3: float
    volume_below_m3: float
    net_volume_m3: float
    surface_area_above_m2: float
    surface_area_below_m2: float
    max_height_above_datum_m: float
    max_depth_below_datum_m: float
    mean_height_above_m: float
    mean_depth_below_m: float
    
    # Stockpile & Pit estimation
    stockpile_estimated_volume_m3: float
    pit_void_estimated_volume_m3: float
    
    # Stage-storage hypsometric breakdown
    stage_storage_curve: List[StageStorageStep] = field(default_factory=list)


class VolumetricEngine:
    """Core mathematical engine for single-surface volumetric calculations."""

    @staticmethod
    def compute_volumetrics(
        raster_source: Union[str, Any],
        datum_elevation: Optional[float] = None,
        num_stages: int = 25
    ) -> VolumetricResult:
        """
        Executes comprehensive single-surface volumetric analysis.
        
        :param raster_source: Path to GeoTIFF file or QgsRasterLayer instance
        :param datum_elevation: Target datum elevation level. If None, uses mean elevation.
        :param num_stages: Number of incremental levels for Stage-Storage capacity curve.
        :return: VolumetricResult dataclass
        """
        file_path = raster_source
        layer_name = "DEM Surface"
        if hasattr(raster_source, "source") and hasattr(raster_source, "name"):
            file_path = getattr(raster_source, "_raw_dem_source", raster_source.source())
            layer_name = raster_source.name()
        elif isinstance(raster_source, str):
            layer_name = os.path.splitext(os.path.basename(raster_source))[0]

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DEM raster file not found: {file_path}")

        ds = gdal.Open(file_path, gdal.GA_ReadOnly)
        if not ds:
            raise RuntimeError(f"Could not open DEM with GDAL: {file_path}")

        gt = ds.GetGeoTransform()
        dx = abs(gt[1])
        dy = abs(gt[5])
        cell_area = dx * dy

        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        arr = band.ReadAsArray().astype(np.float32)
        band = None
        ds = None

        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)

        valid_mask = ~np.isnan(arr)
        valid_z = arr[valid_mask]

        if len(valid_z) == 0:
            raise ValueError("The DEM contains no valid elevation data pixels.")

        min_z = float(np.min(valid_z))
        max_z = float(np.max(valid_z))
        mean_z = float(np.mean(valid_z))
        z_range = max_z - min_z

        if datum_elevation is None:
            datum_elevation = mean_z

        # Elevation diff from datum
        diff = valid_z - datum_elevation
        above_mask = diff > 0.0
        below_mask = diff < 0.0

        vol_above = float(np.sum(diff[above_mask]) * cell_area) if np.any(above_mask) else 0.0
        vol_below = float(np.sum(np.abs(diff[below_mask])) * cell_area) if np.any(below_mask) else 0.0
        net_vol = vol_above - vol_below

        area_above = float(np.sum(above_mask) * cell_area)
        area_below = float(np.sum(below_mask) * cell_area)
        total_valid_cells = int(len(valid_z))
        total_area_m2 = float(total_valid_cells * cell_area)
        total_area_ha = total_area_m2 / 10000.0

        max_h_above = float(np.max(diff[above_mask])) if np.any(above_mask) else 0.0
        max_d_below = float(np.max(np.abs(diff[below_mask]))) if np.any(below_mask) else 0.0
        mean_h_above = float(np.mean(diff[above_mask])) if np.any(above_mask) else 0.0
        mean_d_below = float(np.mean(np.abs(diff[below_mask]))) if np.any(below_mask) else 0.0

        # Stockpile volume (elevations above min_z baseline)
        stockpile_vol = float(np.sum(valid_z - min_z) * cell_area)
        # Pit void volume (void space below max_z rim plane)
        pit_vol = float(np.sum(max_z - valid_z) * cell_area)

        # Stage-Storage Curve Generation
        stage_curve: List[StageStorageStep] = []
        if num_stages > 1 and z_range > 0.0001:
            stage_elevations = np.linspace(min_z, max_z, num_stages)
            for idx, stage_e in enumerate(stage_elevations):
                submerged_mask = valid_z <= stage_e
                sub_area_m2 = float(np.sum(submerged_mask) * cell_area)
                sub_area_ha = sub_area_m2 / 10000.0
                # Cumulative capacity = volume stored under stage_e
                sub_depth = stage_e - valid_z[submerged_mask]
                cumul_vol = float(np.sum(sub_depth) * cell_area) if len(sub_depth) > 0 else 0.0
                
                # Volume above this stage
                ab_mask = valid_z > stage_e
                vol_ab = float(np.sum(valid_z[ab_mask] - stage_e) * cell_area) if np.any(ab_mask) else 0.0

                stage_curve.append(StageStorageStep(
                    stage_index=idx + 1,
                    elevation_m=float(stage_e),
                    stage_height_m=float(stage_e - min_z),
                    surface_area_m2=sub_area_m2,
                    surface_area_ha=sub_area_ha,
                    volume_above_m3=vol_ab,
                    volume_below_m3=cumul_vol,
                    cumulative_capacity_m3=cumul_vol
                ))

        return VolumetricResult(
            layer_name=layer_name,
            datum_elevation=float(datum_elevation),
            total_valid_cells=total_valid_cells,
            cell_size_x=dx,
            cell_size_y=dy,
            cell_area_m2=cell_area,
            total_surface_area_m2=total_area_m2,
            total_surface_area_ha=total_area_ha,
            min_elevation_m=min_z,
            max_elevation_m=max_z,
            mean_elevation_m=mean_z,
            elevation_range_m=z_range,
            volume_above_m3=vol_above,
            volume_below_m3=vol_below,
            net_volume_m3=net_vol,
            surface_area_above_m2=area_above,
            surface_area_below_m2=area_below,
            max_height_above_datum_m=max_h_above,
            max_depth_below_datum_m=max_d_below,
            mean_height_above_m=mean_h_above,
            mean_depth_below_m=mean_d_below,
            stockpile_estimated_volume_m3=stockpile_vol,
            pit_void_estimated_volume_m3=pit_vol,
            stage_storage_curve=stage_curve
        )

    @staticmethod
    def generate_report_text(res: VolumetricResult) -> str:
        """Formats the result into a clean engineering report."""
        lines = [
            "===========================================================",
            "       GEOSTUDIO - VOLUMETRIC & CAPACITY ANALYSIS REPORT   ",
            "===========================================================",
            f"Analyzed Dataset:       {res.layer_name}",
            f"Reference Datum Plane:  {res.datum_elevation:.3f} m",
            f"Pixel Resolution:       {res.cell_size_x:.3f} m x {res.cell_size_y:.3f} m (Cell Area: {res.cell_area_m2:.3f} m²)",
            f"Total Valid Area:       {res.total_surface_area_m2:,.1f} m² ({res.total_surface_area_ha:,.2f} ha)",
            "-----------------------------------------------------------",
            "ELEVATION STATISTICS:",
            f"  Minimum Elevation:    {res.min_elevation_m:,.3f} m",
            f"  Maximum Elevation:    {res.max_elevation_m:,.3f} m",
            f"  Mean Elevation:       {res.mean_elevation_m:,.3f} m",
            f"  Total Relief Range:   {res.elevation_range_m:,.3f} m",
            "-----------------------------------------------------------",
            "VOLUMETRIC ANALYSIS (RELATIVE TO DATUM):",
            f"  Volume Above Datum:   {res.volume_above_m3:,.2f} m³ (Mound/Surplus)",
            f"  Area Above Datum:     {res.surface_area_above_m2:,.1f} m² (Max Height: +{res.max_height_above_datum_m:.2f} m)",
            f"  Volume Below Datum:   {res.volume_below_m3:,.2f} m³ (Void/Capacity)",
            f"  Area Below Datum:     {res.surface_area_below_m2:,.1f} m² (Max Depth: -{res.max_depth_below_datum_m:.2f} m)",
            f"  Net Relative Volume:  {res.net_volume_m3:,.2f} m³",
            "-----------------------------------------------------------",
            "SPECIALIZED ESTIMATES:",
            f"  Stockpile Volume (from minimum base):  {res.stockpile_estimated_volume_m3:,.2f} m³",
            f"  Pit Void Capacity (from maximum rim):  {res.pit_void_estimated_volume_m3:,.2f} m³",
            "==========================================================="
        ]
        return "\n".join(lines)

    @staticmethod
    def export_csv(res: VolumetricResult, csv_path: str):
        """Exports the complete Stage-Storage capacity curve to a CSV file."""
        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["# GeoStudio Stage-Storage Volumetric Capacity Table"])
            writer.writerow(["# Dataset", res.layer_name])
            writer.writerow(["# Datum Elevation (m)", res.datum_elevation])
            writer.writerow(["# Total Area (m2)", res.total_surface_area_m2])
            writer.writerow([])
            writer.writerow([
                "Stage Index",
                "Elevation (m)",
                "Stage Height (m)",
                "Submerged Area (m2)",
                "Submerged Area (ha)",
                "Cumulative Storage Capacity (m3)",
                "Volume Above Stage (m3)"
            ])
            for step in res.stage_storage_curve:
                writer.writerow([
                    step.stage_index,
                    f"{step.elevation_m:.3f}",
                    f"{step.stage_height_m:.3f}",
                    f"{step.surface_area_m2:.2f}",
                    f"{step.surface_area_ha:.4f}",
                    f"{step.cumulative_capacity_m3:.2f}",
                    f"{step.volume_above_m3:.2f}"
                ])
