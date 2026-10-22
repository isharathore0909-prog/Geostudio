# -*- coding: utf-8 -*-
"""
GeoStudio - Cut & Fill Reports & Formatting
Formats text reports and CSV exports for Earthwork Cut & Fill volumetrics.
"""

import csv
from .cut_fill_models import CutFillResult


def generate_report_text(res: CutFillResult) -> str:
    """Formats an engineering cut & fill summary text report."""
    balance_desc = "EXCAVATION SURPLUS (Material to Export / Spoil)" if res.net_earthwork_volume_m3 > 0 else (
        "EMBANKMENT DEFICIT (Borrow Material Required)" if res.net_earthwork_volume_m3 < 0 else "BALANCED EARTHWORK"
    )
    lines = [
        "===========================================================",
        "       GEOSTUDIO - EARTHWORK CUT & FILL VOLUMETRIC REPORT   ",
        "===========================================================",
        f"Base (Existing Surface):       {res.base_name}",
        f"Comparison (Design Surface):   {res.comp_name}",
        f"Total Analyzed Area:           {res.total_analyzed_area_m2:,.1f} m² ({res.total_analyzed_area_ha:,.2f} ha)",
        "-----------------------------------------------------------",
        "SPATIAL AREA BREAKDOWN:",
        f"  Excavation (Cut) Area:       {res.cut_area_m2:,.1f} m² ({(res.cut_area_m2/res.total_analyzed_area_m2)*100:.1f}%)",
        f"  Embankment (Fill) Area:      {res.fill_area_m2:,.1f} m² ({(res.fill_area_m2/res.total_analyzed_area_m2)*100:.1f}%)",
        f"  Daylight (Zero Grade) Area:  {res.daylight_area_m2:,.1f} m²",
        "-----------------------------------------------------------",
        "VOLUMETRIC QUANTITIES:",
        f"  Gross Cut (Excavation) Volume:     {res.gross_cut_volume_m3:,.2f} m³",
        f"  Gross Fill (Embankment) Volume:    {res.gross_fill_volume_m3:,.2f} m³",
        f"  Swell / Bulking Factor:            {res.swell_factor:.2f}",
        f"  Compaction / Shrinkage Factor:     {res.shrinkage_factor:.2f}",
        f"  Factored Cut (Excavation) Volume:  {res.factored_cut_volume_m3:,.2f} m³",
        f"  Factored Fill (Embankment) Volume: {res.factored_fill_volume_m3:,.2f} m³",
        f"  Cut / Fill Volume Ratio:           {res.cut_fill_ratio:.3f}",
        "-----------------------------------------------------------",
        "NET EARTHWORK BALANCE:",
        f"  Net Factored Volume:         {abs(res.net_earthwork_volume_m3):,.2f} m³",
        f"  Earthwork Status:            {balance_desc}",
        "-----------------------------------------------------------",
        "DEPTH & THICKNESS STATISTICS:",
        f"  Maximum Cut Depth:           {res.max_cut_depth_m:.3f} m (Mean Cut: {res.mean_cut_depth_m:.3f} m)",
        f"  Maximum Fill Depth:          {res.max_fill_depth_m:.3f} m (Mean Fill: {res.mean_fill_depth_m:.3f} m)",
        "==========================================================="
    ]
    return "\n".join(lines)


def export_csv(res: CutFillResult, csv_path: str):
    """Exports the Cut & Fill summary to a CSV file."""
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value", "Unit"])
        writer.writerow(["Base Surface", res.base_name, ""])
        writer.writerow(["Comparison Surface", res.comp_name, ""])
        writer.writerow(["Total Analyzed Area", f"{res.total_analyzed_area_m2:.2f}", "m²"])
        writer.writerow(["Total Analyzed Area (Hectares)", f"{res.total_analyzed_area_ha:.4f}", "ha"])
        writer.writerow(["Cut Area", f"{res.cut_area_m2:.2f}", "m²"])
        writer.writerow(["Fill Area", f"{res.fill_area_m2:.2f}", "m²"])
        writer.writerow(["Daylight Area", f"{res.daylight_area_m2:.2f}", "m²"])
        writer.writerow(["Gross Cut Volume", f"{res.gross_cut_volume_m3:.2f}", "m³"])
        writer.writerow(["Gross Fill Volume", f"{res.gross_fill_volume_m3:.2f}", "m³"])
        writer.writerow(["Swell Factor", f"{res.swell_factor:.3f}", ""])
        writer.writerow(["Shrinkage Factor", f"{res.shrinkage_factor:.3f}", ""])
        writer.writerow(["Factored Cut Volume", f"{res.factored_cut_volume_m3:.2f}", "m³"])
        writer.writerow(["Factored Fill Volume", f"{res.factored_fill_volume_m3:.2f}", "m³"])
        writer.writerow(["Net Volume (+ Cut, - Fill)", f"{res.net_earthwork_volume_m3:.2f}", "m³"])
        writer.writerow(["Cut / Fill Ratio", f"{res.cut_fill_ratio:.4f}", ""])
        writer.writerow(["Max Cut Depth", f"{res.max_cut_depth_m:.3f}", "m"])
        writer.writerow(["Mean Cut Depth", f"{res.mean_cut_depth_m:.3f}", "m"])
        writer.writerow(["Max Fill Depth", f"{res.max_fill_depth_m:.3f}", "m"])
        writer.writerow(["Mean Fill Depth", f"{res.mean_fill_depth_m:.3f}", "m"])
