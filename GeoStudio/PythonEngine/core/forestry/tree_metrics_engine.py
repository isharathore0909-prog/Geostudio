# -*- coding: utf-8 -*-
"""
GeoStudio - Precision Forestry & Tree Metrics Engine
Master facade and orchestrator for:
1. Individual Tree Detection & Count (ITD Local Maxima Filter + Labeled PNG Map)
2. Individual Tree Height Extraction from CHM / Point Cloud
3. Crown Delineation, Diameter & Canopy Spread Measurement
4. DBH (Diameter at Breast Height) Estimation & Biomass Allometry
"""

import os
from typing import Optional, Dict, Any, Callable

from .tree_detection import detect_tree_apexes
from .tree_heights import extract_heights_from_chm
from .crown_segmentation import delineate_crown_polygons
from .dbh_allometry import calculate_dbh_and_biomass
from .tree_accuracy_validation import validate_itd_accuracy
from .forestry_io import write_tree_points_vector
from .forestry_visualizer import render_tree_count_png


class TreeMetricsEngine:
    """Master facade coordinating precision forestry algorithms, vector serialization, and map rendering."""

    @classmethod
    def detect_trees(
        cls,
        chm_path: str,
        output_vector_path: str,
        min_height: float = 2.0,
        search_mode: str = "vwf_mixed",
        window_size: int = 5,
        smoothing_sigma: float = 0.8,
        min_prominence: float = 0.35,
        alpha_prominence: float = 0.10,
        ground_coverage_threshold_pct: float = 15.0,
        vwf_a: float = 0.28,
        vwf_b: float = 1.5,
        vwf_min_win: int = 3,
        vwf_max_win: int = 15,
        delineate_crowns: bool = False,
        crowns_vector_path: Optional[str] = None,
        generate_png: bool = True,
        png_path: Optional[str] = None,
        label_style: str = "number",
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Detects tree apexes on a Canopy Height Model (CHM) using Height-Adaptive Variable Window
        Filtering (VWF) or Fixed Local Maxima Filtering (LMF) with crown prominence: P >= max(P_min, alpha*H_apex).
        Optionally delineates individual tree crown polygons via Marker-Controlled Watershed.
        Automatically outputs machine-readable GeoStudio_ITD_Report.json alongside vector output.
        """
        def progress(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        # 1. Detect apexes and calculate stand metrics
        records, chm, gt, wkt, stats = detect_tree_apexes(
            chm_path=chm_path,
            min_height=min_height,
            search_mode=search_mode,
            window_size=window_size,
            smoothing_sigma=smoothing_sigma,
            min_prominence=min_prominence,
            alpha_prominence=alpha_prominence,
            ground_coverage_threshold_pct=ground_coverage_threshold_pct,
            vwf_a=vwf_a,
            vwf_b=vwf_b,
            vwf_min_win=vwf_min_win,
            vwf_max_win=vwf_max_win,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

        # 2. Write Tree Points Vector (GPKG or SHP)
        progress(68, f"Writing tree points vector: {os.path.basename(output_vector_path)}...")
        write_tree_points_vector(output_vector_path, records, wkt)

        # 3. Optional Marker-Controlled Watershed Crown Delineation
        crowns_output = None
        if delineate_crowns:
            if not crowns_vector_path or crowns_vector_path.strip() == "":
                base, ext = os.path.splitext(output_vector_path)
                crowns_vector_path = f"{base}_crowns{ext}"

            progress(75, "Delineating individual tree crowns via Marker-Controlled Watershed...")
            crown_res = delineate_crown_polygons(
                trees_vector_path=output_vector_path,
                chm_path=chm_path,
                output_vector_path=crowns_vector_path,
                method="watershed",
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            crowns_output = crowns_vector_path
            stats["mean_crown_diam"] = crown_res.get("mean_crown_diam", 0.0)
            stats["max_crown_diam"] = crown_res.get("max_crown_diam", 0.0)
            stats["mean_crown_area"] = crown_res.get("mean_crown_area", 0.0)

        # 4. Generate High-Res PNG with Total Count Label
        rendered_png = None
        if generate_png:
            if not png_path or png_path.strip() == "":
                base, _ = os.path.splitext(output_vector_path)
                png_path = f"{base}_count_report.png"

            progress(88, "Rendering high-resolution summary PNG map...")
            rendered_png = render_tree_count_png(
                chm=chm,
                gt=gt,
                tree_records=records,
                total_count=stats["total_trees"],
                forest_area_ha=stats["forest_area_ha"],
                density_per_ha=stats["density_per_ha"],
                mean_height=stats["mean_height"],
                max_height=stats["max_height"],
                label_style=label_style,
                output_png=png_path
            )
            if log_callback:
                log_callback(f"Exported Labeled Tree Count PNG: <b>{os.path.basename(png_path)}</b>")

        # 5. Export machine-readable GeoStudio_ITD_Report.json
        base_dir = os.path.dirname(output_vector_path) or "."
        json_path = os.path.join(base_dir, "GeoStudio_ITD_Report.json")
        try:
            from .tree_report_generator import build_itd_report_payload, export_itd_json_report
            payload = build_itd_report_payload(
                input_path=chm_path,
                stats=stats,
                crs_desc=wkt[:60] if wkt else "Projected"
            )
            export_itd_json_report(payload, json_path)
            if log_callback:
                log_callback(f"Exported Machine-Readable Report: <b>{os.path.basename(json_path)}</b>")
        except Exception as e:
            if log_callback:
                log_callback(f"Notice: Could not write JSON report: {e}")

        progress(100, "Precision Forestry inventory complete!")
        return {
            **stats,
            "vector_path": output_vector_path,
            "crowns_vector_path": crowns_output,
            "png_path": rendered_png,
            "json_report_path": json_path
        }

    @classmethod
    def extract_tree_heights(
        cls,
        trees_vector_path: str,
        chm_path: str,
        output_vector_path: Optional[str] = None,
        search_radius_m: float = 1.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Samples or updates exact individual tree apex heights from a CHM raster
        for every point feature in the input vector layer.
        """
        return extract_heights_from_chm(
            trees_vector_path=trees_vector_path,
            chm_path=chm_path,
            output_vector_path=output_vector_path,
            search_radius_m=search_radius_m,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    @classmethod
    def measure_crown_diameter(
        cls,
        trees_vector_path: str,
        chm_path: str,
        output_vector_path: str,
        max_crown_radius_m: float = 12.0,
        crown_base_ratio: float = 0.35,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Segments individual tree crowns and extracts crown diameter (m), crown area (m²),
        and crown perimeter polygon boundaries.
        """
        return delineate_crown_polygons(
            trees_vector_path=trees_vector_path,
            chm_path=chm_path,
            output_vector_path=output_vector_path,
            max_crown_radius_m=max_crown_radius_m,
            crown_base_ratio=crown_base_ratio,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    @classmethod
    def calculate_dbh(
        cls,
        trees_vector_path: str,
        output_vector_path: str,
        method: str = "allometric",
        forest_preset: str = "conifer",
        custom_a: float = 0.85,
        custom_b: float = 0.72,
        custom_c: float = 0.38,
        wood_density: float = 0.55,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Estimates DBH (cm), Basal Area (m²), and Tree Biomass (kg) using forestry allometry
        or direct 3D stem slices.
        """
        return calculate_dbh_and_biomass(
            trees_vector_path=trees_vector_path,
            output_vector_path=output_vector_path,
            method=method,
            forest_preset=forest_preset,
            custom_a=custom_a,
            custom_b=custom_b,
            custom_c=custom_c,
            wood_density=wood_density,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    @classmethod
    def validate_accuracy(
        cls,
        detected_vector_path: str,
        reference_vector_path: str,
        output_vector_path: str,
        match_distance_m: float = 2.0,
        height_tolerance_pct: float = 30.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Validates detected tree apexes/crowns against ground truth reference trees.
        Computes scientific performance metrics: Precision, Recall, F1 Score, and Height RMSE.
        """
        return validate_itd_accuracy(
            detected_vector_path=detected_vector_path,
            reference_vector_path=reference_vector_path,
            output_vector_path=output_vector_path,
            match_distance_m=match_distance_m,
            height_tolerance_pct=height_tolerance_pct,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    @classmethod
    def generate_inventory_report(
        cls,
        trees_vector_path: str,
        output_report_path: str,
        validation_vector_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Compiles a comprehensive machine-readable GeoStudio_ITD_Report.json and
        a 300-DPI publication figure from tree inventory and optional validation datasets.
        """
        from .tree_report_generator import generate_forestry_inventory_report
        return generate_forestry_inventory_report(
            trees_vector_path=trees_vector_path,
            output_report_path=output_report_path,
            validation_vector_path=validation_vector_path,
            progress_callback=progress_callback,
            log_callback=log_callback
        )

    @classmethod
    def estimate_agb_and_carbon(
        cls,
        input_path: str,
        output_path: str,
        is_raster_chm: bool = True,
        preset: str = "temperate_lefsky",
        custom_a: float = 1.15,
        custom_b: float = 1.18,
        wood_density: float = 0.55,
        root_to_shoot_ratio: float = 0.235,
        carbon_fraction: float = 0.47,
        carbon_price_usd: float = 25.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Estimates continuous Aboveground Biomass (AGB Mg/ha), Carbon Stock (t C),
        and CO2 Equivalent (tonnes CO2e) from CHM raster or tree inventory vector.
        """
        from .agb_carbon_engine import AGBCarbonEngine
        if is_raster_chm:
            return AGBCarbonEngine.estimate_from_chm(
                chm_path=input_path,
                output_raster_path=output_path,
                preset=preset,
                custom_a=custom_a,
                custom_b=custom_b,
                wood_density=wood_density,
                root_to_shoot_ratio=root_to_shoot_ratio,
                carbon_fraction=carbon_fraction,
                carbon_price_usd=carbon_price_usd,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
        else:
            return AGBCarbonEngine.estimate_from_trees_vector(
                trees_vector_path=input_path,
                output_vector_path=output_path,
                forest_preset=preset,
                wood_density=wood_density,
                root_to_shoot_ratio=root_to_shoot_ratio,
                carbon_fraction=carbon_fraction,
                carbon_price_usd=carbon_price_usd,
                custom_a=custom_a,
                custom_b=custom_b,
                progress_callback=progress_callback,
                log_callback=log_callback
            )



