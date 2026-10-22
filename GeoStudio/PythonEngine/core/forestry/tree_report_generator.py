# -*- coding: utf-8 -*-
"""
GeoStudio - Precision Forestry & ITD Inventory Report Generator
Generates machine-readable `GeoStudio_ITD_Report.json` and 300-DPI publication graphics
summarizing stand metrics, height distributions, crown spreads, and validation benchmarks.
"""

import os
import json
import numpy as np
from typing import Dict, Any, Optional, Callable
from osgeo import ogr


def export_itd_json_report(
    report_dict: Dict[str, Any],
    output_json_path: str
) -> str:
    """Exports structured ITD and forestry metadata to a clean JSON document."""
    os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    return output_json_path


def build_itd_report_payload(
    input_path: str,
    stats: Dict[str, Any],
    crs_desc: str = "Projected",
    validation_stats: Optional[Dict[str, Any]] = None,
    allometry_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Builds the standardized GeoStudio ITD Processing Report dictionary."""
    pc_meta = stats.get("point_cloud_meta", {})

    input_block = {
        "File": os.path.basename(input_path),
        "Points": pc_meta.get("point_count", "Raster / Pre-derived"),
        "CRS": crs_desc
    }

    processing_block = {
        "CHM_resolution_m": stats.get("chm_resolution_m", 0.50),
        "Ground_method": pc_meta.get("ground_source", "Pre-computed / Direct"),
        "Ground_coverage_pct": pc_meta.get("ground_cells_occupied_pct", "N/A"),
        "DTM_confidence": pc_meta.get("dtm_confidence", "HIGH"),
        "VWF_model": stats.get("vwf_model", "Adaptive Mixed Stand"),
        "VWF_equation": stats.get("vwf_equation", "0.28H + 1.5"),
        "Gaussian_sigma": stats.get("smoothing_sigma", 0.8),
        "Minimum_height_m": stats.get("min_height_threshold", 2.0),
        "Minimum_prominence_m": stats.get("min_prominence", 0.35),
        "Relative_prominence_factor": stats.get("alpha_prominence", 0.10)
    }

    results_block = {
        "Total_trees": stats.get("total_trees", 0),
        "Stand_density_trees_per_ha": round(stats.get("density_per_ha", 0.0), 1),
        "Survey_area_ha": round(stats.get("forest_area_ha", 0.0), 2),
        "Mean_height_m": round(stats.get("mean_height", 0.0), 2),
        "Max_height_m": round(stats.get("max_height", 0.0), 2),
        "Min_height_m": round(stats.get("min_height", 0.0), 2),
        "Mean_crown_diameter_m": round(stats.get("mean_crown_diam", 0.0), 2) if "mean_crown_diam" in stats else "N/A",
        "Max_crown_diameter_m": round(stats.get("max_crown_diam", 0.0), 2) if "max_crown_diam" in stats else "N/A"
    }

    report = {
        "GeoStudio_Precision_Forestry_Report": {
            "Input": input_block,
            "Processing": processing_block,
            "Results": results_block
        }
    }

    if validation_stats:
        report["GeoStudio_Precision_Forestry_Report"]["Validation"] = {
            "Match_distance_tolerance_m": validation_stats.get("match_distance_m", 2.0),
            "True_positives": validation_stats.get("true_positives", 0),
            "False_positives": validation_stats.get("false_positives", 0),
            "False_negatives": validation_stats.get("false_negatives", 0),
            "Precision": round(validation_stats.get("precision", 0.0), 3),
            "Recall": round(validation_stats.get("recall", 0.0), 3),
            "F1_score": round(validation_stats.get("f1_score", 0.0), 3),
            "Height_MAE_m": round(validation_stats.get("height_mae_m", 0.0), 2),
            "Height_RMSE_m": round(validation_stats.get("height_rmse_m", 0.0), 2),
            "Height_Bias_m": round(validation_stats.get("height_bias_m", 0.0), 2),
            "Sensitivity_curve": validation_stats.get("sensitivity_curve", [])
        }

    if allometry_stats:
        report["GeoStudio_Precision_Forestry_Report"]["Allometry"] = {
            "DBH_source": allometry_stats.get("dbh_source", "Allometric Model"),
            "DBH_model": allometry_stats.get("dbh_model", "Calibrated Allometry"),
            "DBH_confidence": allometry_stats.get("dbh_confidence", "Estimated (Aerial CHM)"),
            "Biomass_model": allometry_stats.get("biomass_model", "Chave et al. (2014)"),
            "Mean_DBH_cm": round(allometry_stats.get("mean_dbh_cm", 0.0), 1),
            "Total_stand_basal_area_m2": round(allometry_stats.get("total_basal_area_m2", 0.0), 2),
            "Total_stand_biomass_tons": round(allometry_stats.get("total_biomass_tons", 0.0), 2)
        }

    return report


def generate_forestry_inventory_report(
    trees_vector_path: str,
    output_report_path: str,
    validation_vector_path: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Reads an existing tree inventory vector layer and compiles:
    1. A machine-readable `GeoStudio_ITD_Report.json`
    2. A 300-DPI publication-quality 4-panel inventory chart (`.png`)
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    progress(15, "Parsing tree inventory dataset...")
    ds = ogr.Open(trees_vector_path, 0)
    if not ds:
        raise RuntimeError(f"Could not open trees inventory vector: {trees_vector_path}")
    lyr = ds.GetLayer(0)

    heights = []
    crown_diams = []
    dbhs = []
    basal_areas = []
    biomasses = []
    xs = []
    ys = []

    for feat in lyr:
        geom = feat.GetGeometryRef()
        if not geom:
            continue
        gx = geom.GetX() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetX()
        gy = geom.GetY() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetY()
        xs.append(gx)
        ys.append(gy)

        if feat.GetFieldIndex("Height_m") >= 0:
            heights.append(float(feat.GetField("Height_m")))
        if feat.GetFieldIndex("Crown_Diam_m") >= 0:
            crown_diams.append(float(feat.GetField("Crown_Diam_m")))
        if feat.GetFieldIndex("DBH_cm") >= 0:
            dbhs.append(float(feat.GetField("DBH_cm")))
        if feat.GetFieldIndex("BasalArea_m2") >= 0:
            basal_areas.append(float(feat.GetField("BasalArea_m2")))
        if feat.GetFieldIndex("Biomass_kg") >= 0:
            biomasses.append(float(feat.GetField("Biomass_kg")))

    total_trees = len(heights)
    if total_trees == 0:
        raise RuntimeError("No valid tree records found in dataset.")

    progress(40, "Calculating inventory distributions and stand statistics...")
    h_arr = np.array(heights)
    mean_h = float(np.mean(h_arr))
    max_h = float(np.max(h_arr))
    min_h = float(np.min(h_arr))
    std_h = float(np.std(h_arr))

    # Approximate bounding box area
    if len(xs) > 1:
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)
        # If geographic, convert to meters
        if abs(xs[0]) <= 180 and abs(ys[0]) <= 90:
            m_lon = 111412.84 * np.cos(np.radians(np.mean(ys)))
            m_lat = 111132.95
            area_ha = (dx * m_lon * dy * m_lat) / 10000.0
        else:
            area_ha = (dx * dy) / 10000.0
        area_ha = max(0.01, area_ha)
        density = total_trees / area_ha
    else:
        area_ha = 1.0
        density = float(total_trees)

    stats = {
        "total_trees": total_trees,
        "forest_area_ha": area_ha,
        "density_per_ha": density,
        "mean_height": mean_h,
        "max_height": max_h,
        "min_height": min_h,
        "std_height": std_h,
        "chm_resolution_m": 0.50,
        "vwf_model": "VWF Height-Adaptive",
        "vwf_equation": "Calibrated Forest Allometry",
        "smoothing_sigma": 0.8,
        "min_height_threshold": min_h,
        "min_prominence": 0.35,
        "alpha_prominence": 0.10
    }
    if crown_diams:
        stats["mean_crown_diam"] = float(np.mean(crown_diams))
        stats["max_crown_diam"] = float(np.max(crown_diams))

    allometry_stats = None
    if dbhs:
        allometry_stats = {
            "dbh_source": "Allometric Model",
            "dbh_model": "Calibrated Forest Preset",
            "dbh_confidence": "Estimated (Aerial CHM)",
            "biomass_model": "Chave et al. (2014) Allometric AGB",
            "mean_dbh_cm": float(np.mean(dbhs)),
            "total_basal_area_m2": float(np.sum(basal_areas)),
            "total_biomass_tons": float(np.sum(biomasses) / 1000.0)
        }

    # Validation stats if provided
    val_stats = None
    if validation_vector_path and os.path.exists(validation_vector_path):
        v_ds = ogr.Open(validation_vector_path, 0)
        if v_ds:
            v_lyr = v_ds.GetLayer(0)
            tp_c, fp_c, fn_c = 0, 0, 0
            v_errs = []
            for f in v_lyr:
                ct = f.GetField("Class_Type")
                if ct == "TP":
                    tp_c += 1
                    if f.GetFieldIndex("Height_Err_m") >= 0 and f.GetField("Height_Err_m") is not None:
                        v_errs.append(float(f.GetField("Height_Err_m")))
                elif ct == "FP":
                    fp_c += 1
                elif ct == "FN":
                    fn_c += 1
            v_prec = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
            v_rec = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
            v_f1 = (2 * v_prec * v_rec / (v_prec + v_rec)) if (v_prec + v_rec) > 0 else 0.0
            val_stats = {
                "match_distance_m": 2.0,
                "true_positives": tp_c,
                "false_positives": fp_c,
                "false_negatives": fn_c,
                "precision": v_prec,
                "recall": v_rec,
                "f1_score": v_f1,
                "height_mae_m": float(np.mean(np.abs(v_errs))) if v_errs else 0.0,
                "height_rmse_m": float(np.sqrt(np.mean(np.array(v_errs)**2))) if v_errs else 0.0,
                "height_bias_m": float(np.mean(v_errs)) if v_errs else 0.0
            }

    # 1. Export JSON Report
    progress(60, "Exporting GeoStudio_ITD_Report.json...")
    base_dir = os.path.dirname(output_report_path) or "."
    json_path = os.path.join(base_dir, "GeoStudio_ITD_Report.json")
    payload = build_itd_report_payload(
        input_path=trees_vector_path,
        stats=stats,
        validation_stats=val_stats,
        allometry_stats=allometry_stats
    )
    export_itd_json_report(payload, json_path)
    log(f"Exported machine-readable report: <b>{os.path.basename(json_path)}</b>")

    # 2. Render 300-DPI Publication Report Figure
    progress(75, "Rendering 300-DPI Precision Forestry Inventory Report graphic...")
    png_path = output_report_path if output_report_path.lower().endswith(".png") else os.path.splitext(output_report_path)[0] + ".png"

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(14, 10), dpi=300)
    fig.patch.set_facecolor("#0f172a")

    # Header title banner
    fig.text(0.08, 0.94, "GeoStudio — Precision Forestry Inventory Report", fontsize=18, fontweight="bold", color="#f8fafc")
    sub_title = f"Stand Census: {total_trees:,} Trees  |  Density: {density:.0f} trees/ha  |  Mean Height: {mean_h:.1f} m  |  Max Height: {max_h:.1f} m"
    fig.text(0.08, 0.91, sub_title, fontsize=11, color="#94a3b8")

    # Panel 1: Tree Height Distribution Histogram
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_facecolor("#1e293b")
    ax1.hist(h_arr, bins=25, color="#10b981", edgecolor="#064e3b", alpha=0.85)
    ax1.axvline(mean_h, color="#f59e0b", linestyle="--", linewidth=2, label=f"Mean: {mean_h:.1f} m")
    ax1.axvline(np.median(h_arr), color="#38bdf8", linestyle=":", linewidth=2, label=f"Median: {np.median(h_arr):.1f} m")
    ax1.set_title("Individual Tree Height Distribution", fontsize=12, fontweight="bold", color="#e2e8f0")
    ax1.set_xlabel("Tree Height (m)", color="#cbd5e1", fontsize=10)
    ax1.set_ylabel("Tree Frequency", color="#cbd5e1", fontsize=10)
    ax1.tick_params(colors="#94a3b8")
    ax1.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#f1f5f9")
    ax1.grid(True, linestyle="--", alpha=0.2, color="#94a3b8")

    # Panel 2: Spatial Tree Stem Distribution Map
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor("#1e293b")
    sc = ax2.scatter(xs, ys, c=h_arr, cmap="viridis", s=18, alpha=0.9, edgecolors="none")
    cbar = fig.colorbar(sc, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label("Height (m)", color="#cbd5e1")
    cbar.ax.tick_params(colors="#94a3b8")
    ax2.set_title("Spatial Apex Distribution & Canopy Height", fontsize=12, fontweight="bold", color="#e2e8f0")
    ax2.tick_params(colors="#94a3b8")
    ax2.grid(True, linestyle="--", alpha=0.15, color="#94a3b8")

    # Panel 3: Crown Spread / DBH Distribution
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.set_facecolor("#1e293b")
    if crown_diams:
        cd_arr = np.array(crown_diams)
        ax3.scatter(h_arr, cd_arr, color="#06b6d4", alpha=0.6, s=16)
        ax3.set_title(f"Crown Spread Allometry (Mean CD: {np.mean(cd_arr):.1f} m)", fontsize=12, fontweight="bold", color="#e2e8f0")
        ax3.set_xlabel("Tree Height (m)", color="#cbd5e1", fontsize=10)
        ax3.set_ylabel("Crown Diameter (m)", color="#cbd5e1", fontsize=10)
    elif dbhs:
        dbh_arr = np.array(dbhs)
        ax3.scatter(h_arr, dbh_arr, color="#f97316", alpha=0.6, s=16)
        ax3.set_title(f"Estimated DBH Allometry (Mean DBH: {np.mean(dbh_arr):.1f} cm)", fontsize=12, fontweight="bold", color="#e2e8f0")
        ax3.set_xlabel("Tree Height (m)", color="#cbd5e1", fontsize=10)
        ax3.set_ylabel("Estimated DBH (cm)", color="#cbd5e1", fontsize=10)
    else:
        ax3.text(0.5, 0.5, "Crown / DBH data not available in layer", color="#64748b", ha="center", va="center")
        ax3.set_title("Crown / Stem Metrics", fontsize=12, color="#e2e8f0")
    ax3.tick_params(colors="#94a3b8")
    ax3.grid(True, linestyle="--", alpha=0.2, color="#94a3b8")

    # Panel 4: Inventory Summary or Validation Benchmark Card
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor("#1e293b")
    ax4.axis("off")

    lines = [
        "FORESTRY INVENTORY EXECUTIVE METRICS",
        "──────────────────────────────────────────────",
        f"• Total Trees Detected:     {total_trees:,}",
        f"• Estimated Stand Density:   {density:.0f} trees/ha",
        f"• Stand Height (Mean / Max): {mean_h:.1f} m / {max_h:.1f} m",
        f"• Height Std Deviation:     {std_h:.2f} m",
    ]
    if crown_diams:
        lines.append(f"• Mean Crown Diameter:       {np.mean(crown_diams):.2f} m")
    if dbhs:
        lines.append(f"• Mean Estimated DBH:        {np.mean(dbhs):.1f} cm")
        lines.append(f"• Stand Basal Area:          {np.sum(basal_areas):.2f} m²")
        lines.append(f"• Aboveground Biomass:       {np.sum(biomasses)/1000.0:.2f} tons")

    if val_stats:
        lines.extend([
            "",
            "GROUND TRUTH ACCURACY BENCHMARK",
            "──────────────────────────────────────────────",
            f"• Precision (Correctness):   {val_stats['precision']*100:.1f}%",
            f"• Recall (Detection Rate):   {val_stats['recall']*100:.1f}%",
            f"• F1-Score:                  {val_stats['f1_score']*100:.1f}%",
            f"• Height MAE / RMSE:         {val_stats['height_mae_m']:.2f} m / {val_stats['height_rmse_m']:.2f} m",
            f"• Mean Height Bias:          {val_stats['height_bias_m']:+.2f} m"
        ])

    card_text = "\n".join(lines)
    ax4.text(0.08, 0.90, card_text, fontsize=9.5, family="monospace", color="#f1f5f9", va="top")

    plt.tight_layout(rect=[0.05, 0.04, 0.95, 0.90])
    plt.savefig(png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    progress(100, "Inventory report generation complete!")
    log(f"Rendered 300-DPI Publication Report: <b>{os.path.basename(png_path)}</b>")

    return {
        "json_report_path": json_path,
        "image_report_path": png_path,
        "total_trees": total_trees,
        "mean_height": mean_h,
        "max_height": max_h,
        "density_per_ha": density,
        "allometry": allometry_stats,
        "validation": val_stats
    }
