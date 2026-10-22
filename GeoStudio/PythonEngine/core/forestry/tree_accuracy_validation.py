# -*- coding: utf-8 -*-
"""
GeoStudio - LiDAR Individual Tree Detection (ITD) Accuracy Validation & Benchmarking
Implements bipartite spatial matching against reference ground truth / field inventory.
Calculates Sensitivity Curves (1m, 2m, 3m, 5m), Precision, Recall, F1 Score, 
Height Diagnostics (MAE, RMSE, Bias), and Height-Stratified Metrics.
"""

import os
import math
from typing import Dict, Any, List, Optional, Callable
import numpy as np
from osgeo import ogr, osr


def validate_itd_accuracy(
    detected_vector_path: str,
    reference_vector_path: str,
    output_vector_path: str,
    match_distance_m: float = 2.0,
    height_tolerance_pct: float = 30.0,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Evaluates detected tree points or crowns against reference ground-truth data.
    Implements clean spatial 1-to-1 matching (Spatial match -> TP/FP/FN), continuous height error
    diagnostics (MAE, RMSE, Bias) on matched trees, and sensitivity curve benchmarking across radii.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    def progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    progress(10, "Opening detected trees and reference ground truth layers...")
    log(f"Evaluating: <b>{os.path.basename(detected_vector_path)}</b> against Reference: <b>{os.path.basename(reference_vector_path)}</b>")

    # 1. Read Detected Trees
    ds_det = ogr.Open(detected_vector_path, 0)
    if not ds_det:
        raise RuntimeError(f"Could not open detected trees dataset: {detected_vector_path}")
    lyr_det = ds_det.GetLayer(0)
    srs_det = lyr_det.GetSpatialRef()
    proj_wkt = srs_det.ExportToWkt() if srs_det else ""

    det_trees = []
    for feat in lyr_det:
        geom = feat.GetGeometryRef()
        if not geom:
            continue
        gx = geom.GetX() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetX()
        gy = geom.GetY() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetY()
        h = float(feat.GetField("Height_m")) if feat.GetFieldIndex("Height_m") >= 0 else 0.0
        t_id = feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else len(det_trees) + 1
        det_trees.append({
            "id": t_id,
            "x": gx,
            "y": gy,
            "height": h,
            "matched": False,
            "match_ref_id": None,
            "dist_err": None,
            "h_err": None
        })

    # 2. Read Reference Truth Trees
    ds_ref = ogr.Open(reference_vector_path, 0)
    if not ds_ref:
        raise RuntimeError(f"Could not open reference trees dataset: {reference_vector_path}")
    lyr_ref = ds_ref.GetLayer(0)

    ref_trees = []
    for feat in lyr_ref:
        geom = feat.GetGeometryRef()
        if not geom:
            continue
        gx = geom.GetX() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetX()
        gy = geom.GetY() if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D) else geom.Centroid().GetY()
        h = 0.0
        for fld in ["Height_m", "Height", "h_m", "HEIGHT", "Z"]:
            if feat.GetFieldIndex(fld) >= 0:
                h = float(feat.GetField(fld))
                break
        r_id = feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else len(ref_trees) + 1
        ref_trees.append({
            "id": r_id,
            "x": gx,
            "y": gy,
            "height": h,
            "matched": False,
            "match_det_id": None,
            "dist_err": None,
            "h_err": None
        })

    n_det = len(det_trees)
    n_ref = len(ref_trees)
    log(f"Loaded <b>{n_det:,}</b> detected trees and <b>{n_ref:,}</b> ground-truth reference trees.")

    if n_det == 0 or n_ref == 0:
        raise RuntimeError("Detection or reference dataset contains 0 features.")

    # 3. Spatial Coordinate Normalization (Geographic vs Projected)
    progress(25, "Computing pairwise spatial distance candidates...")
    is_geo = (abs(det_trees[0]["x"]) <= 180 and abs(det_trees[0]["y"]) <= 90)
    if is_geo:
        mean_lat = det_trees[0]["y"]
        m_lon = max(1000.0, 111412.84 * math.cos(math.radians(mean_lat)))
        m_lat = max(1000.0, 111132.954 - 559.822 * math.cos(2 * math.radians(mean_lat)))
    else:
        m_lon = 1.0
        m_lat = 1.0

    # Max search radius for sensitivity testing
    max_search_r = max(5.0, match_distance_m)

    # Compute pairwise candidate distances up to max_search_r
    candidates = []
    for d_idx, d in enumerate(det_trees):
        for r_idx, r in enumerate(ref_trees):
            dx = (d["x"] - r["x"]) * m_lon
            dy = (d["y"] - r["y"]) * m_lat
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= max_search_r:
                candidates.append((dist, d_idx, r_idx))

    # Sort all candidates by distance ascending (greedy nearest 1-to-1 matching)
    candidates.sort(key=lambda item: item[0])

    # 4. Multi-Radius Sensitivity Analysis (1m, 2m, 3m, 5m + operating point)
    progress(40, "Calculating matching sensitivity curve across multiple spatial tolerances...")
    radii_eval = sorted(list(set([1.0, 2.0, 3.0, 5.0, round(match_distance_m, 2)])))
    sensitivity_results = []

    for r_tol in radii_eval:
        matched_d_set = set()
        matched_r_set = set()
        for dist, d_idx, r_idx in candidates:
            if dist > r_tol:
                break
            if d_idx not in matched_d_set and r_idx not in matched_r_set:
                matched_d_set.add(d_idx)
                matched_r_set.add(r_idx)

        r_tp = len(matched_d_set)
        r_fp = n_det - r_tp
        r_fn = n_ref - r_tp
        r_prec = float(r_tp / n_det) if n_det > 0 else 0.0
        r_rec = float(r_tp / n_ref) if n_ref > 0 else 0.0
        r_f1 = float(2.0 * r_prec * r_rec / (r_prec + r_rec)) if (r_prec + r_rec) > 0 else 0.0

        sensitivity_results.append({
            "radius_m": r_tol,
            "precision": r_prec,
            "recall": r_rec,
            "f1_score": r_f1,
            "tp": r_tp,
            "fp": r_fp,
            "fn": r_fn
        })

    # 5. Primary 1-to-1 Spatial Match for Selected Operating Tolerance
    progress(55, f"Finalizing primary validation at tolerance = {match_distance_m:.1f} m...")
    matched_det_set = set()
    matched_ref_set = set()
    matched_pairs = []

    for dist, d_idx, r_idx in candidates:
        if dist > match_distance_m:
            break
        if d_idx not in matched_det_set and r_idx not in matched_ref_set:
            matched_det_set.add(d_idx)
            matched_ref_set.add(r_idx)
            det_trees[d_idx]["matched"] = True
            det_trees[d_idx]["match_ref_id"] = ref_trees[r_idx]["id"]
            det_trees[d_idx]["dist_err"] = dist

            # Signed height error: H_det - H_ref
            signed_h_err = (det_trees[d_idx]["height"] - ref_trees[r_idx]["height"]) if ref_trees[r_idx]["height"] > 0 else 0.0
            det_trees[d_idx]["h_err"] = signed_h_err

            ref_trees[r_idx]["matched"] = True
            ref_trees[r_idx]["match_det_id"] = det_trees[d_idx]["id"]
            ref_trees[r_idx]["dist_err"] = dist
            ref_trees[r_idx]["h_err"] = signed_h_err
            matched_pairs.append((d_idx, r_idx))

    tp = len(matched_pairs)
    fp = n_det - tp
    fn = n_ref - tp

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1_score = float(2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # 6. Continuous Height Diagnostics on Matched Trees (MAE, RMSE, Bias)
    matched_h_errors = [d["h_err"] for d in det_trees if d["matched"] and d["h_err"] is not None]
    if matched_h_errors:
        err_arr = np.array(matched_h_errors, dtype=np.float64)
        h_mae = float(np.mean(np.abs(err_arr)))
        h_rmse = float(np.sqrt(np.mean(err_arr ** 2)))
        h_bias = float(np.mean(err_arr))
        # Height tolerance diagnostic check
        within_diag = [d for d in det_trees if d["matched"] and d["h_err"] is not None and abs(d["h_err"]) <= (0.01 * height_tolerance_pct * max(1.0, d["height"]))]
        h_diagnostic_pct = (len(within_diag) / len(matched_h_errors)) * 100.0
    else:
        h_mae = 0.0
        h_rmse = 0.0
        h_bias = 0.0
        h_diagnostic_pct = 100.0

    # 7. Height-Stratified Accuracy Benchmarking
    stratified = {}
    h_tiers = [("Small (<5m)", 0.0, 5.0), ("Medium (5-15m)", 5.0, 15.0), ("Tall (>15m)", 15.0, 150.0)]
    for tier_name, h_min, h_max in h_tiers:
        tier_ref_idx = [r_idx for r_idx, r in enumerate(ref_trees) if h_min <= r["height"] < h_max]
        if tier_ref_idx:
            tier_tp = sum(1 for r_idx in tier_ref_idx if ref_trees[r_idx]["matched"])
            tier_fn = len(tier_ref_idx) - tier_tp
            tier_recall = float(tier_tp / len(tier_ref_idx))
            stratified[tier_name] = {
                "ref_count": len(tier_ref_idx),
                "tp": tier_tp,
                "fn": tier_fn,
                "recall": tier_recall
            }

    progress(75, "Exporting classified validation vector layer...")

    # 8. Write Classified Validation Vector (GPKG)
    driver = ogr.GetDriverByName("GPKG" if output_vector_path.endswith(".gpkg") else "ESRI Shapefile")
    if os.path.exists(output_vector_path):
        driver.DeleteDataSource(output_vector_path)

    ds_out = driver.CreateDataSource(output_vector_path)
    srs_out = osr.SpatialReference()
    if proj_wkt:
        srs_out.ImportFromWkt(proj_wkt)
    lyr_out = ds_out.CreateLayer("itd_validation_results", srs_out, ogr.wkbPoint)

    lyr_out.CreateField(ogr.FieldDefn("Feature_ID", ogr.OFTInteger))
    lyr_out.CreateField(ogr.FieldDefn("Class_Type", ogr.OFTString))      # TP, FP, FN
    lyr_out.CreateField(ogr.FieldDefn("Status_Desc", ogr.OFTString))
    lyr_out.CreateField(ogr.FieldDefn("Height_m", ogr.OFTReal))
    lyr_out.CreateField(ogr.FieldDefn("Dist_Err_m", ogr.OFTReal))
    lyr_out.CreateField(ogr.FieldDefn("Height_Err_m", ogr.OFTReal))
    defn = lyr_out.GetLayerDefn()

    fid = 1
    # Write Detected Points (TP and FP)
    for d in det_trees:
        feat = ogr.Feature(defn)
        feat.SetField("Feature_ID", fid)
        feat.SetField("Class_Type", "TP" if d["matched"] else "FP")
        feat.SetField("Status_Desc", "True Positive (Correct Detection)" if d["matched"] else "False Positive (Commission Error)")
        feat.SetField("Height_m", d["height"])
        if d["dist_err"] is not None:
            feat.SetField("Dist_Err_m", round(d["dist_err"], 2))
        if d["h_err"] is not None:
            feat.SetField("Height_Err_m", round(d["h_err"], 2))

        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint_2D(d["x"], d["y"])
        feat.SetGeometry(pt)
        lyr_out.CreateFeature(feat)
        fid += 1

    # Write Missed Reference Points (FN)
    for r in ref_trees:
        if not r["matched"]:
            feat = ogr.Feature(defn)
            feat.SetField("Feature_ID", fid)
            feat.SetField("Class_Type", "FN")
            feat.SetField("Status_Desc", "False Negative (Missed Tree / Omission Error)")
            feat.SetField("Height_m", r["height"])
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint_2D(r["x"], r["y"])
            feat.SetGeometry(pt)
            lyr_out.CreateFeature(feat)
            fid += 1

    ds_out = None
    progress(100, "Validation complete!")

    # 9. Log Comprehensive Scientific Summary Table & Sensitivity Curve
    log(f"\n<b>📊 ITD Accuracy Benchmarking Summary (Tolerance: {match_distance_m:.1f} m):</b>")
    log(f"• <b>Precision (Correctness):</b> {precision * 100:.1f}%")
    log(f"• <b>Recall (Detection Rate):</b> {recall * 100:.1f}%")
    log(f"• <b>F1-Score (Harmonic Accuracy):</b> {f1_score * 100:.1f}%")
    log(f"• <b>Confusion Matrix:</b> TP = <b>{tp:,}</b> | FP (Commission) = <b>{fp:,}</b> | FN (Omission) = <b>{fn:,}</b>")
    if matched_h_errors:
        log(f"• <b>Height Error Diagnostics (Matched TPs):</b> MAE = <b>{h_mae:.2f} m</b> | RMSE = <b>{h_rmse:.2f} m</b> | Mean Bias = <b>{h_bias:+.2f} m</b>")
        log(f"• <b>Height Diagnostic Compliance (≤{height_tolerance_pct:.0f}% error):</b> <b>{h_diagnostic_pct:.1f}%</b>")

    # Formatted Sensitivity Table
    log("<br><b>📈 Spatial Matching Sensitivity Curve:</b>")
    table_header = "<table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse; font-size:12px; margin-top:4px;'>" \
                   "<tr style='background-color:#2e3440; color:#eceff4; font-weight:bold;'>" \
                   "<th>Matching Radius</th><th>Precision</th><th>Recall</th><th>F1-Score</th><th>TP</th><th>FP</th><th>FN</th></tr>"
    table_rows = []
    for s in sensitivity_results:
        is_sel = (abs(s["radius_m"] - match_distance_m) < 0.05)
        bg = "#1e293b" if is_sel else "transparent"
        hl = "font-weight:bold; color:#38bdf8;" if is_sel else ""
        row = f"<tr style='background-color:{bg}; {hl}'>" \
              f"<td align='center'>{s['radius_m']:.1f} m</td>" \
              f"<td align='center'>{s['precision']:.2f}</td>" \
              f"<td align='center'>{s['recall']:.2f}</td>" \
              f"<td align='center'>{s['f1_score']:.2f}</td>" \
              f"<td align='center'>{s['tp']:,}</td>" \
              f"<td align='center'>{s['fp']:,}</td>" \
              f"<td align='center'>{s['fn']:,}</td></tr>"
        table_rows.append(row)
    log(table_header + "".join(table_rows) + "</table>")

    return {
        "total_detected": n_det,
        "total_reference": n_ref,
        "match_distance_m": match_distance_m,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "height_mae_m": h_mae,
        "height_rmse_m": h_rmse,
        "height_bias_m": h_bias,
        "height_diagnostic_pass_pct": h_diagnostic_pct,
        "sensitivity_curve": sensitivity_results,
        "stratified_by_height": stratified,
        "output_vector_path": output_vector_path
    }
