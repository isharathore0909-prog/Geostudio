"""GeoStudio Offline Hydrology & Artificial Recharge Siting Tasks.

Calibrated to:
- Central Ground Water Board (CGWB 2007) Artificial Recharge Screening Rules
- Govt of Rajasthan WRD / WDSC SOR & BSR benchmark rates
- Farmer water-budget & crop recommendations
"""

import sys
import json
import math
from pathlib import Path

def score_check_dam(slope_deg: float, catchment_ha: float, gw_depth_m: float, stream_order: int = 2) -> float:
    """Scores candidate location for Check Dam / Anicut (CGWB Criteria)."""
    score = 0.0
    # Slope criterion (Ideal: 0.5 - 3 degrees / 1-5%)
    if 0.5 <= slope_deg <= 3.0:
        score += 35.0
    elif slope_deg <= 5.0:
        score += 20.0
    elif slope_deg <= 8.0:
        score += 10.0

    # Catchment area (Ideal: 25 - 250 ha for check dams)
    if 25.0 <= catchment_ha <= 250.0:
        score += 30.0
    elif 10.0 <= catchment_ha <= 500.0:
        score += 15.0

    # Depth to water table (Ideal: 5 - 25 m bgl)
    if 5.0 <= gw_depth_m <= 25.0:
        score += 25.0
    elif gw_depth_m > 25.0:
        score += 15.0

    # Stream order (1st to 3rd order streams)
    if 1 <= stream_order <= 3:
        score += 10.0

    return min(100.0, score)

def score_percolation_pond(slope_deg: float, catchment_ha: float, gw_depth_m: float) -> float:
    """Scores candidate location for Percolation Pond (CGWB Criteria: 0-3 deg slope)."""
    score = 0.0
    if slope_deg <= 2.0:
        score += 40.0
    elif slope_deg <= 4.0:
        score += 20.0

    if 40.0 <= catchment_ha <= 400.0:
        score += 30.0
    elif 15.0 <= catchment_ha <= 800.0:
        score += 15.0

    if 6.0 <= gw_depth_m <= 30.0:
        score += 30.0
    elif gw_depth_m > 3.0:
        score += 15.0

    return min(100.0, score)

def score_farm_pond(slope_deg: float, catchment_ha: float) -> float:
    """Scores candidate location for Khet Talai / Farm Pond."""
    score = 0.0
    if slope_deg <= 3.0:
        score += 50.0
    elif slope_deg <= 6.0:
        score += 25.0

    if 2.0 <= catchment_ha <= 50.0:
        score += 50.0
    elif catchment_ha <= 100.0:
        score += 30.0

    return min(100.0, score)

def recommend_crops(annual_rainfall_mm: float, aquifer_type: str = "Alluvium", gw_status: str = "Semi-Critical"):
    """Recommends water-budget aligned Kharif, Rabi, and high-value horticulture crops."""
    is_water_scarce = annual_rainfall_mm < 400.0 or "Over-Exploited" in gw_status or "Critical" in gw_status

    if is_water_scarce:
        kharif = ["Bajra (Pearl Millet)", "Moong (Green Gram)", "Moth Bean", "Cluster Bean (Guar)"]
        rabi = ["Mustard (Low water)", "Gram (Chickpea)", "Barley"]
        horticulture = ["Pomegranate (Bhagwa)", "Ber (Gola/Seb)", "Date Palm", "Aonla (NA-7)"]
        commercial_veg = ["Garlic (Drip)", "Chilli (Mulched)", "Coriander (Seed)"]
    else:
        kharif = ["Soybean", "Maize", "Groundnut", "Cotton", "Moong"]
        rabi = ["Wheat (GW-322)", "Mustard", "Gram", "Vegetables"]
        horticulture = ["Guava (Taiwan Pink)", "Orange / Kinnow", "Lemon (Kagzi)", "Papaya"]
        commercial_veg = ["Tomato (Protected)", "Onion", "Capsicum", "Watermelon"]

    return {
        "Annual_Rainfall_mm": annual_rainfall_mm,
        "Aquifer_Type": aquifer_type,
        "Groundwater_Status": gw_status,
        "Recommended_Kharif_Crops": kharif,
        "Recommended_Rabi_Crops": rabi,
        "Recommended_Horticulture_Crops": horticulture,
        "Commercial_Vegetables": commercial_veg,
        "Water_Saving_Interventions": [
            "Drip Irrigation with Solar Pump Subsidy",
            "In-situ Moisture Conservation with Bunding",
            "HDPE-lined Farm Pond for Critical Supplemental Irrigation"
        ]
    }

def run_recharge_screening(input_points_json: str, output_geojson: str):
    """Processes array of points [ {lat, lng, slope, catchment, gw_depth} ] and outputs GeoJSON candidate sites."""
    with open(input_points_json, 'r', encoding='utf-8') as f:
        points = json.load(f)

    features = []
    for i, pt in enumerate(points):
        lat = pt.get("lat", 0.0)
        lng = pt.get("lng", 0.0)
        slope = pt.get("slope", 1.5)
        catchment = pt.get("catchment_ha", 50.0)
        gw_depth = pt.get("gw_depth_m", 12.0)

        cd_score = score_check_dam(slope, catchment, gw_depth)
        pp_score = score_percolation_pond(slope, catchment, gw_depth)
        fp_score = score_farm_pond(slope, catchment)

        best_score = max(cd_score, pp_score, fp_score)
        if best_score == cd_score:
            rec_structure = "Check Dam / Anicut"
        elif best_score == pp_score:
            rec_structure = "Percolation Pond"
        else:
            rec_structure = "Farm Pond"

        feat = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat]
            },
            "properties": {
                "Site_ID": f"SITE_{i+1:04d}",
                "Best_Structure": rec_structure,
                "Suitability_Score": round(best_score, 1),
                "Check_Dam_Score": round(cd_score, 1),
                "Percolation_Pond_Score": round(pp_score, 1),
                "Farm_Pond_Score": round(fp_score, 1),
                "Slope_Deg": slope,
                "Catchment_Ha": catchment,
                "Depth_To_Water_m": gw_depth
            }
        }
        features.append(feat)

    result = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_geojson, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    return {"status": "success", "candidate_sites": len(features)}

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--screen":
        run_recharge_screening(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 2 and sys.argv[1] == "--crop-plan":
        rainfall = float(sys.argv[2])
        res = recommend_crops(rainfall)
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python recharge_tasks.py --screen <input.json> <output.geojson>")
