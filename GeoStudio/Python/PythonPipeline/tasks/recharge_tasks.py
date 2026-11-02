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

def compute_crop_wai(rainfall_mm: float, gw_status: str, gw_depth_m: float, aquifer_type: str, canal_idx: float = 0.0) -> tuple[float, int, str]:
    """Computes the CGWB-calibrated Water Availability Index (WAI) and Tier."""
    s = str(gw_status).lower().replace("-", " ").replace("_", " ").strip()
    if "over" in s or s == "oe": cls, gw_score = "OE", 20.0
    elif "saline" in s: cls, gw_score = "SAL", 25.0
    elif "crit" in s: cls, gw_score = "C", 45.0
    elif "semi" in s or s == "sc": cls, gw_score = "SC", 70.0
    else: cls, gw_score = "S", 100.0

    aq_up = str(aquifer_type).upper()
    if any(x in aq_up for x in ("SCHIST", "GNEISS", "GRANITE", "BASALT", "PHYLLITE", "QUARTZITE")): aq_score = 40.0
    elif any(x in aq_up for x in ("SANDSTONE", "LIMESTONE", "DOLOMITE")): aq_score = 60.0
    elif any(x in aq_up for x in ("AEOLIAN", "DUNE")): aq_score = 70.0
    else: aq_score = 100.0

    depth_score = 15.0 if gw_depth_m > 30 else 30.0 if gw_depth_m > 20 else 50.0 if gw_depth_m > 12 else 75.0 if gw_depth_m > 6 else 100.0
    rain_score = 20.0 if rainfall_mm < 300 else 40.0 if rainfall_mm < 450 else 65.0 if rainfall_mm < 600 else 90.0 if rainfall_mm < 800 else 100.0

    wai = (0.40 * gw_score + 0.25 * depth_score + 0.20 * rain_score + 0.15 * aq_score + 15.0 * min(1.0, canal_idx))

    # Hydrological OE safety cap
    if cls == "OE":
        if canal_idx < 0.20:
            wai = min(38.0, wai)
        else:
            wai = min(48.0, 35.0 + 20.0 * canal_idx)
    elif cls == "C":
        wai = min(54.0, wai)

    wai = min(100.0, round(wai, 1))
    tier_n = 1 if wai < 40 else 2 if wai < 55 else 3 if wai < 70 else 4
    tier_label = {1: "Tier 1: Extreme Deficit", 2: "Tier 2: Moderate Deficit",
                  3: "Tier 3: Moderate Availability", 4: "Tier 4: High Availability"}[tier_n]
    return wai, tier_n, tier_label

def recommend_crops(annual_rainfall_mm: float, aquifer_type: str = "Alluvium", gw_status: str = "Semi-Critical",
                    gw_depth_m: float = 15.0, canal_idx: float = 0.0, soil_texture: str = "loam",
                    ecw_dsm: float = 1.0):
    """Recommends water-budget aligned Kharif, Rabi, and high-value horticulture crops using calibrated FAO/CGWB criteria."""
    wai, tier_n, tier_label = compute_crop_wai(annual_rainfall_mm, gw_status, gw_depth_m, aquifer_type, canal_idx)
    zone = "arid" if annual_rainfall_mm < 350 else ("semi" if annual_rainfall_mm < 550 else "humid")
    soil = str(soil_texture).lower()

    # Crop suitability database
    # format: (ETc_mm, ece, zones, soils, irr_tech)
    crop_cat = {
        "Bajra (Pearl Millet)": (350, 6.0, ("arid", "semi", "humid"), ("sandy", "loam"), "Protective sprinkler in dry spells"),
        "Moong (Green Gram)": (300, 1.8, ("arid", "semi", "humid"), ("sandy", "loam", "clay"), "Sprinkler"),
        "Moth Bean": (250, 2.5, ("arid", "semi"), ("sandy", "loam"), "Rainfed / dryland"),
        "Cluster Bean (Guar)": (250, 4.5, ("arid", "semi"), ("sandy", "loam"), "Rainfed + 1 life-saving sprinkler"),
        "Soybean": (320, 5.0, ("semi", "humid"), ("loam", "clay"), "Sprinkler"),
        "Groundnut": (550, 3.2, ("arid", "semi", "humid"), ("sandy", "loam"), "Pressurized Sprinkler"),
        "Maize": (500, 1.7, ("semi", "humid"), ("loam", "clay"), "Sprinkler / furrow"),
        "Cotton": (550, 7.7, ("arid", "semi", "humid"), ("loam", "clay"), "Precision Drip + Fertigation"),
        "Mustard (Pusa Bold / RH-30)": (370, 5.5, ("arid", "semi", "humid"), ("sandy", "loam", "clay"), "Pressurized Sprinkler"),
        "Gram (Chickpea)": (266, 1.7, ("arid", "semi", "humid"), ("sandy", "loam", "clay"), "Mini-sprinkler"),
        "Barley (RD-2035)": (428, 8.0, ("arid", "semi", "humid"), ("sandy", "loam", "clay"), "Sprinkler (high salinity tolerant)"),
        "Wheat (GW-322 / Raj-4037)": (450, 6.0, ("semi", "humid"), ("loam", "clay"), "Sprinkler / border strip"),
        "Cumin (GC-4)": (280, 2.2, ("arid", "semi"), ("sandy", "loam"), "Micro-sprinkler / Drip (dry canopy against blight)"),
        "Isabgol (GI-2)": (220, 3.0, ("arid", "semi"), ("sandy", "loam"), "Pressurized Sprinkler"),
    }

    def is_ok(crop_name):
        etc, ece, czones, csoils, _ = crop_cat[crop_name]
        if zone not in czones: return False
        if ece is not None and ecw_dsm > (ece / 1.5): return False
        if not any(st in soil for st in csoils): return False
        return True

    # Tier-based selection
    if tier_n == 1: # Extreme deficit
        kharif = [c for c in ["Bajra (Pearl Millet)", "Moth Bean", "Cluster Bean (Guar)", "Moong (Green Gram)"] if is_ok(c)] or ["Moth Bean", "Cluster Bean (Guar)"]
        rabi = [c for c in ["Isabgol (GI-2)", "Gram (Chickpea)", "Barley (RD-2035)", "Mustard (Pusa Bold / RH-30)"] if is_ok(c)] or ["Barley (RD-2035)"]
        horticulture = ["Date Palm (Barhee / Khadrawy)", "Aloe Vera (Barbadensis)", "Ber (Gola / Seb)", "Kair / Gundha"]
        commercial_veg = ["None recommended (extreme deficit)"]
        target_water_saving_pct = 40.0
    elif tier_n == 2: # Moderate deficit
        kharif = [c for c in ["Moong (Green Gram)", "Bajra (Pearl Millet)", "Cluster Bean (Guar)", "Groundnut"] if is_ok(c)] or ["Moong (Green Gram)"]
        rabi = [c for c in ["Cumin (GC-4)", "Mustard (Pusa Bold / RH-30)", "Gram (Chickpea)", "Isabgol (GI-2)"] if is_ok(c)] or ["Mustard (Pusa Bold / RH-30)"]
        horticulture = ["Pomegranate (Bhagwa)", "Ber (Umran / Seb)", "Aonla (NA-7)", "Dragon Fruit"]
        commercial_veg = ["Garlic (Drip + Mulch)", "Chilli (Drip)", "Coriander (Seed)"]
        target_water_saving_pct = 25.0
    elif tier_n == 3: # Moderate availability
        kharif = [c for c in ["Groundnut", "Cotton", "Soybean", "Maize", "Moong (Green Gram)"] if is_ok(c)] or ["Soybean", "Maize"]
        rabi = [c for c in ["Mustard (Pusa Bold / RH-30)", "Gram (Chickpea)", "Wheat (GW-322 / Raj-4037)"] if is_ok(c)] or ["Mustard (Pusa Bold / RH-30)"]
        horticulture = ["Guava (L-49 / Taiwan Pink)", "Mandarin Orange (Nagpur Santra)", "Kagzi Lemon", "Kinnow"]
        commercial_veg = ["Tomato (Drip + Staking)", "Onion", "Capsicum", "Watermelon"]
        target_water_saving_pct = 10.0
    else: # High availability
        kharif = [c for c in ["Soybean", "Maize", "Cotton", "Groundnut"] if is_ok(c)] or ["Soybean", "Maize"]
        rabi = [c for c in ["Wheat (GW-322 / Raj-4037)", "Mustard (Pusa Bold / RH-30)", "Gram (Chickpea)"] if is_ok(c)] or ["Wheat (GW-322 / Raj-4037)"]
        horticulture = ["Kinnow (Abohar)", "Guava (L-49)", "Kagzi Lemon", "Mango (Amrapali)"]
        commercial_veg = ["Tomato (High yield)", "Onion (Rabi)", "Capsicum", "Cauliflower"]
        target_water_saving_pct = 0.0

    # Irrigation tech summary
    irrig_tech = []
    if rabi:
        irrig_tech.append(f"Rabi Crop: {crop_cat[rabi[0]][4]}")
    if kharif:
        irrig_tech.append(f"Kharif Crop: {crop_cat[kharif[0]][4]}")
    if tier_n <= 2 and canal_idx < 0.2:
        irrig_tech.append("Conveyance: Underground PVC pipe distribution mandatory (save 25-30% transit seepage)")

    # Baseline & water savings estimate
    base_annual_water_mm = 650.0 if tier_n >= 3 else 450.0
    rec_annual_water_mm = round(base_annual_water_mm * (1.0 - target_water_saving_pct / 100.0), 1)
    saved_water_mm = round(base_annual_water_mm - rec_annual_water_mm, 1)
    saved_water_m3_ha = round(saved_water_mm * 10.0, 1)
    est_net_profit_gain_inr = round(saved_water_m3_ha * 2.0 + (12000.0 if tier_n >= 2 else 6000.0), 0)

    return {
        "Annual_Rainfall_mm": annual_rainfall_mm,
        "Rain_Zone": zone,
        "Aquifer_Type": aquifer_type,
        "Groundwater_Status": gw_status,
        "Groundwater_Depth_m": gw_depth_m,
        "Soil_Texture": soil,
        "Water_Salinity_ECw_dSm": ecw_dsm,
        "WAI_Score": wai,
        "WAI_Tier": tier_label,
        "Tier_Number": tier_n,
        "Recommended_Kharif_Crops": kharif,
        "Recommended_Rabi_Crops": rabi,
        "Recommended_Horticulture_Crops": horticulture,
        "Commercial_Vegetables": commercial_veg,
        "Prescribed_Irrigation_Technology": irrig_tech,
        "Baseline_Annual_Applied_Water_mm": base_annual_water_mm,
        "Recommended_Annual_Applied_Water_mm": rec_annual_water_mm,
        "Annual_Applied_Water_Saved_mm": saved_water_mm,
        "Annual_Applied_Water_Saved_m3_per_ha": saved_water_m3_ha,
        "Estimated_Farmer_Net_Profit_Gain_INR_per_ha": est_net_profit_gain_inr,
        "Water_Saving_Interventions": [
            "Pressurized Drip / Micro-Sprinkler with Leaching Fraction" if ecw_dsm > 2.0 else "Pressurized Drip / Micro-Sprinkler with Solar Pump Subsidy",
            "Underground PVC Piped Conveyance to eliminate transit seepage",
            "In-situ Moisture Conservation with Broad Bed Furrows (BBF) and Bunding",
            "HDPE-lined Farm Pond (Khet Talai) for Critical Supplemental Irrigation"
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
        aquifer = sys.argv[3] if len(sys.argv) > 3 else "Alluvium"
        gw_status = sys.argv[4] if len(sys.argv) > 4 else "Semi-Critical"
        gw_depth = float(sys.argv[5]) if len(sys.argv) > 5 else 15.0
        canal = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
        soil = sys.argv[7] if len(sys.argv) > 7 else "loam"
        ecw = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
        res = recommend_crops(rainfall, aquifer, gw_status, gw_depth, canal, soil, ecw)
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python recharge_tasks.py --screen <input.json> <output.geojson> | --crop-plan <rain_mm> [aquifer] [gw_status] [depth_m] [canal_idx] [soil] [ecw]")
