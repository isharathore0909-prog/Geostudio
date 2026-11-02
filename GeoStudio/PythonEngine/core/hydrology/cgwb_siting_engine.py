# -*- coding: utf-8 -*-
"""
GeoStudio - CGWB Artificial Recharge Master Plan (2020) & Rajasthan BSR BOQ Engine
Implements:
1. Macro Plan: District & block screening, volume calculations, regional surplus capping (Table 8.17.1 & 8.17.2).
2. Micro Siting: Multi-criteria field decision tree (Strahler stream order, bed width, slope, lithology, DTW, EC)
   with Rajasthan WRD/WDSC BSR 2023-24 BOQ cost estimations.
"""

from typing import Dict, Any, List, Optional
import math

WESTERN_DISTRICTS = {
    "barmer", "bikaner", "churu", "ganganagar", "hanumangarh",
    "jaisalmer", "jhunjhunu", "jodhpur", "nagaur", "sikar"
}

# CGWB Master Plan 2020 Unit Costs in Lakhs INR (Table 8.17.2)
UNIT_COST_CHECK_DAM_LAKH = 6.0
UNIT_COST_RECHARGE_SHAFT_LAKH = 2.0
UNIT_COST_FARM_POND_LAKH = 1.5
UNIT_COST_PERCOLATION_TANK_LAKH = 3.0
UNIT_COST_CAT_PER_HA_LAKH = 1.0
UNIT_COST_TANKA_LAKH = 2.0
UNIT_COST_ANICUT_LAKH = 15.0
UNIT_COST_MACRO_TANK_LAKH = 50.0
UNIT_COST_MINI_PERCOLATION_TANK_LAKH = 1.0

# Rajasthan WRD BSR Standard Rates
RATE_EARTHWORK = 165.0       # /cum
RATE_EXCAVATION = 240.0      # /cum
RATE_DRY_STONE = 2800.0      # /cum
RATE_RRM_MASONRY = 3400.0    # /cum
RATE_CC_136 = 4800.0         # /cum
RATE_CC_124 = 6200.0         # /cum
RATE_FILTER_MEDIA = 1850.0   # /cum
RATE_HDPE_LINER = 190.0      # /sqm
RATE_DRILLING_BORE = 850.0   # /m
RATE_PVC_CASING = 950.0      # /m
RATE_PLASTER_13 = 185.0      # /sqm
RATE_RCC_M25 = 7800.0        # /cum


class CgwbMasterPlanEngine:
    """Computational engine for CGWB artificial recharge evaluation and BOQ generation."""

    @staticmethod
    def is_western_district(district_name: str) -> bool:
        return district_name.strip().lower() in WESTERN_DISTRICTS

    @classmethod
    def calculate_macro_plan(
        cls,
        district_name: str,
        stage: str = "Over-Exploited",
        dtw_meters: float = 12.0,
        trend_m_per_year: float = -0.42,
        ec_micro_siemens: float = 1250.0,
        specific_yield_pct: float = 2.2,
        area_sq_km: float = 8000.0,
        surplus_runoff_mcm: float = 150.0
    ) -> Dict[str, Any]:
        """
        Executes Tier A Master Plan Volumetric & Regional Quota Allocation.
        """
        is_west = cls.is_western_district(district_name)

        # 1. SCREENING RULES
        if dtw_meters < 3.0:
            return {
                "screening_passed": False,
                "reason": "Post-monsoon DTW < 3.0 m bgl. Artificial recharge prohibited to prevent waterlogging & salinity."
            }

        if ec_micro_siemens > 2500.0:
            return {
                "screening_passed": False,
                "reason": f"Native groundwater EC ({ec_micro_siemens:.0f} µS/cm) exceeds 2,500 µS/cm potable limit."
            }

        is_declining = (trend_m_per_year <= -0.20 or trend_m_per_year >= 0.20)
        if dtw_meters < 9.0 and not is_declining:
            return {
                "screening_passed": False,
                "reason": "For moderate DTW (3-9m), long-term post-monsoon declining trend >= 0.2 m/yr is mandatory."
            }

        # 2. VOLUMETRIC FORMULAS
        t_unsat = max(0.0, dtw_meters - 3.0)
        vu_mcm = area_sq_km * t_unsat
        storage_space_mcm = vu_mcm * (specific_yield_pct / 100.0)
        water_req_mcm = storage_space_mcm / 0.75
        feasible_recharge_mcm = min(water_req_mcm, surplus_runoff_mcm)

        # 3. REGIONAL ALLOCATIONS
        quotas: List[Dict[str, Any]] = []
        is_safe = "safe" in stage.lower()

        if is_safe:
            cat_ha = area_sq_km * 12.0
            quotas.append({
                "structure": "Catchment Area Treatment (CAT)",
                "count": int(cat_ha),
                "unit_cost_lakh": UNIT_COST_CAT_PER_HA_LAKH,
                "total_cost_crores": (cat_ha * UNIT_COST_CAT_PER_HA_LAKH) / 100.0,
                "zone": "Ridge Watersheds"
            })
        elif is_west:
            tankas = int(area_sq_km * 2.5)
            talabs = int(area_sq_km * 0.15)
            cat_ha = area_sq_km * 1.0
            quotas.append({
                "structure": "Tanka (Covered Cistern)",
                "count": tankas,
                "unit_cost_lakh": UNIT_COST_TANKA_LAKH,
                "total_cost_crores": (tankas * UNIT_COST_TANKA_LAKH) / 100.0,
                "zone": "Desert Settlements"
            })
            quotas.append({
                "structure": "Outcrop Talab / Pond",
                "count": talabs,
                "unit_cost_lakh": UNIT_COST_FARM_POND_LAKH,
                "total_cost_crores": (talabs * UNIT_COST_FARM_POND_LAKH) / 100.0,
                "zone": "Rocky Outcrops"
            })
            quotas.append({
                "structure": "Catchment Treatment (ha)",
                "count": int(cat_ha),
                "unit_cost_lakh": UNIT_COST_CAT_PER_HA_LAKH,
                "total_cost_crores": (cat_ha * UNIT_COST_CAT_PER_HA_LAKH) / 100.0,
                "zone": "Ridges"
            })
        else:
            scale = max(0.2, min(4.0, surplus_runoff_mcm / 150.0))
            check_dams = int(1500 * scale)
            perc_tanks = int(3000 * scale)
            mini_perc = int(6300 * scale)
            anicuts = int(750 * scale)
            farm_ponds = int(8800 * scale)
            shafts = int(12 * scale)
            macro_tanks = int(40 * scale)
            cat_ha = 8500 * scale

            quotas.append({"structure": "Pacca Check Dam", "count": check_dams, "unit_cost_lakh": UNIT_COST_CHECK_DAM_LAKH, "total_cost_crores": (check_dams * UNIT_COST_CHECK_DAM_LAKH) / 100.0, "zone": "2nd-3rd Order Streams"})
            quotas.append({"structure": "Percolation Tank / Talab", "count": perc_tanks, "unit_cost_lakh": UNIT_COST_PERCOLATION_TANK_LAKH, "total_cost_crores": (perc_tanks * UNIT_COST_PERCOLATION_TANK_LAKH) / 100.0, "zone": "Valley Depressions"})
            quotas.append({"structure": "Mini Percolation Tank", "count": mini_perc, "unit_cost_lakh": UNIT_COST_MINI_PERCOLATION_TANK_LAKH, "total_cost_crores": (mini_perc * UNIT_COST_MINI_PERCOLATION_TANK_LAKH) / 100.0, "zone": "1st-2nd Order Streams"})
            quotas.append({"structure": "Masonry Anicut", "count": anicuts, "unit_cost_lakh": UNIT_COST_ANICUT_LAKH, "total_cost_crores": (anicuts * UNIT_COST_ANICUT_LAKH) / 100.0, "zone": "3rd-4th Order Streams"})
            quotas.append({"structure": "Farm Pond (Khet Talai)", "count": farm_ponds, "unit_cost_lakh": UNIT_COST_FARM_POND_LAKH, "total_cost_crores": (farm_ponds * UNIT_COST_FARM_POND_LAKH) / 100.0, "zone": "Farmlands"})
            quotas.append({"structure": "Recharge Shaft in Tank", "count": shafts, "unit_cost_lakh": UNIT_COST_RECHARGE_SHAFT_LAKH, "total_cost_crores": (shafts * UNIT_COST_RECHARGE_SHAFT_LAKH) / 100.0, "zone": "Clayey/Silted Tanks"})
            quotas.append({"structure": "Macro Storage Tank", "count": macro_tanks, "unit_cost_lakh": UNIT_COST_MACRO_TANK_LAKH, "total_cost_crores": (macro_tanks * UNIT_COST_MACRO_TANK_LAKH) / 100.0, "zone": "Major Bottlenecks"})
            quotas.append({"structure": "Catchment Treatment (ha)", "count": int(cat_ha), "unit_cost_lakh": UNIT_COST_CAT_PER_HA_LAKH, "total_cost_crores": (cat_ha * UNIT_COST_CAT_PER_HA_LAKH) / 100.0, "zone": "Ridges"})

        total_cr = sum(q["total_cost_crores"] for q in quotas)

        return {
            "screening_passed": True,
            "region": "Western Arid" if is_west else "Eastern General",
            "t_unsat_meters": t_unsat,
            "unsaturated_vol_mcm": vu_mcm,
            "storage_space_mcm": storage_space_mcm,
            "gross_water_req_mcm": water_req_mcm,
            "surplus_runoff_mcm": surplus_runoff_mcm,
            "feasible_recharge_mcm": feasible_recharge_mcm,
            "quotas": quotas,
            "total_outlay_crores": total_cr,
            "total_outlay_lakhs": total_cr * 100.0
        }

    @classmethod
    def evaluate_field_siting(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Tier B Multi-Criteria Field Siting & Sizing Decision Tree.
        """
        district = params.get("district", "Bhilwara")
        is_west = cls.is_western_district(district)
        stream_order = int(params.get("stream_order", 2))
        bed_width = float(params.get("bed_width", 10.0))
        slope_pct = float(params.get("slope_pct", 2.0))
        dtw = float(params.get("dtw", 11.5))
        ec = float(params.get("ec", 1200.0))
        catchment_ha = float(params.get("catchment_ha", 65.0))
        rainfall_mm = float(params.get("rainfall_mm", 620.0))
        has_clay = bool(params.get("has_clay_cover", False))
        is_outcrop = bool(params.get("is_outcrop_west", False))

        if dtw < 3.0:
            return {"eligible": False, "verdict": "REJECTED (Waterlogging Risk)", "reason": "DTW < 3m bgl."}
        if ec > 2500.0:
            return {"eligible": False, "verdict": "REJECTED (Saline Risk)", "reason": "EC > 2,500 µS/cm."}

        # Catchment yield Yc = 10 * C * P * A (m3)
        c_val = 0.22 if "good" in params.get("catchment_type", "").lower() else (0.10 if "bad" in params.get("catchment_type", "").lower() else 0.16)
        yield_m3 = 10.0 * c_val * rainfall_mm * catchment_ha
        yield_tcm = yield_m3 / 1000.0

        if is_west:
            if is_outcrop:
                struct = "Recharge Shaft with Desilting Chamber"
                dims = {"L": 4.0, "H": 25.0, "W": 0.45, "Df": 1.5}
                fillings = 2
            else:
                struct = "Tanka (Covered Cistern)"
                dims = {"L": 24.0, "H": 3.5, "W": 4.0, "Df": 0.5}
                fillings = 2
        else:
            if has_clay:
                struct = "Recharge Shaft in Village Tank"
                dims = {"L": 3.5, "H": 30.0, "W": 0.45, "Df": 1.5}
                fillings = 3
            elif stream_order == 1 or slope_pct > 3.0 or bed_width < 5.0:
                if catchment_ha < 25.0:
                    struct = "Farm Pond (Khet Talai) with Liner"
                    dims = {"L": 20.0, "H": 3.0, "W": 1.5, "Df": 0.0}
                    fillings = 2
                else:
                    struct = "Mini Percolation Tank"
                    dims = {"L": 15.0, "H": 2.0, "W": 2.0, "Df": 0.8}
                    fillings = 3
            elif stream_order >= 3 and bed_width >= 18.0 and slope_pct <= 1.5:
                struct = "Masonry Anicut (Spillway & Apron)"
                dims = {"L": max(25.0, bed_width), "H": 3.2, "W": 2.2, "Df": 1.5}
                fillings = 3
            elif bed_width > 12.0 and slope_pct < 2.0:
                struct = "Percolation Tank / Talab"
                dims = {"L": 60.0, "H": 3.0, "W": 2.5, "Df": 1.0}
                fillings = 2
            else:
                struct = "Pacca Masonry Check Dam"
                dims = {"L": max(15.0, bed_width), "H": 2.2, "W": 1.8, "Df": 1.2}
                fillings = 4

        boq = cls.calculate_boq(struct, dims)

        return {
            "eligible": True,
            "recommended_structure": struct,
            "dimensions": dims,
            "recommended_fillings": fillings,
            "catchment_yield_tcm": yield_tcm,
            "boq": boq
        }

    @staticmethod
    def calculate_boq(structure_name: str, dims: Dict[str, float]) -> Dict[str, Any]:
        """Calculates line-item BOQ according to Rajasthan WRD BSR rates."""
        L = dims.get("L", 25.0)
        H = dims.get("H", 2.5)
        W = dims.get("W", 1.8)
        Df = dims.get("Df", 1.2)

        items = []
        if "Check Dam" in structure_name or "Anicut" in structure_name:
            bottom_w = W + 0.8 * (H + Df)
            exc = L * bottom_w * Df * 1.15
            rrm = L * ((W + bottom_w) / 2.0) * (H + Df)
            cc_cap = L * W * 0.15
            cc_apron = L * (H * 2.5) * 0.3
            items.append({"item": 1, "desc": "Foundation Bed Excavation in Riverbed/Nallah", "qty": exc, "unit": "cum", "rate": RATE_EXCAVATION, "amount": exc * RATE_EXCAVATION})
            items.append({"item": 2, "desc": "Random Rubble Masonry (RRM) in CM 1:5", "qty": rrm, "unit": "cum", "rate": RATE_RRM_MASONRY, "amount": rrm * RATE_RRM_MASONRY})
            items.append({"item": 3, "desc": "Cement Concrete 1:2:4 M20 Coping/Crest Cap", "qty": cc_cap, "unit": "cum", "rate": RATE_CC_124, "amount": cc_cap * RATE_CC_124})
            items.append({"item": 4, "desc": "Cement Concrete 1:3:6 M15 Stilling Apron", "qty": cc_apron, "unit": "cum", "rate": RATE_CC_136, "amount": cc_apron * RATE_CC_136})
            capacity_tcm = (L * H * H * 18.0) / 1000.0
        elif "Percolation Tank" in structure_name:
            pit_vol = L * L * H * 0.85
            pitch = L * H * 0.35
            filt = L * 2.0 * 0.5
            items.append({"item": 1, "desc": "Earthwork Excavation for Basin & Bund", "qty": pit_vol, "unit": "cum", "rate": RATE_EARTHWORK, "amount": pit_vol * RATE_EARTHWORK})
            items.append({"item": 2, "desc": "Dry Stone Pitching on Slope (1:2)", "qty": pitch, "unit": "cum", "rate": RATE_DRY_STONE, "amount": pitch * RATE_DRY_STONE})
            items.append({"item": 3, "desc": "Graded Gravel Filter Bed on Trench", "qty": filt, "unit": "cum", "rate": RATE_FILTER_MEDIA, "amount": filt * RATE_FILTER_MEDIA})
            capacity_tcm = pit_vol / 1000.0
        elif "Tanka" in structure_name:
            r = W / 2.0
            exc = math.pi * math.pow(r + 0.4, 2) * (H + 0.5)
            wall = math.pi * W * 0.35 * H
            plaster = (math.pi * W * H) + (math.pi * math.pow(r, 2))
            slab = math.pi * math.pow(r + 0.3, 2) * 0.12
            agor = math.pi * (math.pow(12.0, 2) - math.pow(r, 2))
            items.append({"item": 1, "desc": "Circular Pit Excavation in Hard Murrum", "qty": exc, "unit": "cum", "rate": RATE_EXCAVATION, "amount": exc * RATE_EXCAVATION})
            items.append({"item": 2, "desc": "Class I Masonry Wall in CM 1:4", "qty": wall, "unit": "cum", "rate": RATE_RRM_MASONRY, "amount": wall * RATE_RRM_MASONRY})
            items.append({"item": 3, "desc": "20mm Waterproof Cement Plaster 1:3", "qty": plaster, "unit": "sqm", "rate": RATE_PLASTER_13, "amount": plaster * RATE_PLASTER_13})
            items.append({"item": 4, "desc": "RCC M25 Roof Cover Slab with Manhole", "qty": slab, "unit": "cum", "rate": RATE_RCC_M25, "amount": slab * RATE_RCC_M25})
            items.append({"item": 5, "desc": "Agor Catchment Apron Ramming", "qty": agor, "unit": "sqm", "rate": 45.0, "amount": agor * 45.0})
            capacity_tcm = (math.pi * math.pow(r, 2) * H) / 1000.0
        else:
            depth_m = H if H > 0 else 25.0
            items.append({"item": 1, "desc": "450mm Dia Rotary Drilling of Borehole", "qty": depth_m, "unit": "m", "rate": RATE_DRILLING_BORE, "amount": depth_m * RATE_DRILLING_BORE})
            items.append({"item": 2, "desc": "200mm Dia Slotted PVC Well Casing", "qty": depth_m, "unit": "m", "rate": RATE_PVC_CASING, "amount": depth_m * RATE_PVC_CASING})
            items.append({"item": 3, "desc": "Graded Pea Gravel Filter Pack", "qty": 8.5, "unit": "cum", "rate": RATE_FILTER_MEDIA, "amount": 8.5 * RATE_FILTER_MEDIA})
            items.append({"item": 4, "desc": "Surface Desilting Chamber Concrete Structure", "qty": 4.0, "unit": "cum", "rate": RATE_CC_124, "amount": 4.0 * RATE_CC_124})
            capacity_tcm = 12.0

        subtotal = sum(i["amount"] for i in items)
        contingency = subtotal * 0.03
        supervision = subtotal * 0.02
        total_cost = subtotal + contingency + supervision

        return {
            "items": items,
            "subtotal": subtotal,
            "contingency": contingency,
            "supervision": supervision,
            "total_cost_inr": total_cost,
            "storage_capacity_tcm": capacity_tcm
        }

