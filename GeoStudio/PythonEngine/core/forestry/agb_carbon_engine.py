# -*- coding: utf-8 -*-
"""
GeoStudio - Aboveground Biomass (AGB) & Carbon Stock Estimation Engine
Comprehensive scientific engine for calculating:
1. Aboveground Biomass (AGB) in metric tonnes / Mg (or kg per tree)
2. Belowground Biomass (BGB) / Root Biomass via IPCC allometric root-to-shoot ratios
3. Total Forest Carbon Stock (AGC + BGC) in tonnes Carbon
4. Carbon Dioxide Equivalent (CO2e) sequestered (tonnes CO2e)
5. Carbon Credit Valuation ($ USD) based on market carbon pricing
6. Continuous GeoTIFF AGB & Carbon Stock density maps (Mg/ha, t C/ha, t CO2e/ha)
"""

import os
import json
import math
import time
from typing import Dict, Any, Callable, Optional, List
import numpy as np
from osgeo import gdal, ogr, osr


class AGBCarbonEngine:
    """Scientific facade for area-wide and individual tree Aboveground Biomass (AGB) & Carbon Stock estimation."""

    # Allometric model coefficients for canopy height models (CHM -> AGB Mg/ha)
    # Power-law form: AGB (Mg/ha) = a * (H ^ b)
    CHM_PRESETS = {
        "tropical_asner": {
            "name": "Asner et al. (2012/2014) Tropical & Subtropical",
            "a": 0.055,
            "b": 1.42,
            "wood_density": 0.60,
            "desc": "Calibrated across moist tropical and neotropical broadleaf forest canopy heights."
        },
        "temperate_lefsky": {
            "name": "Lefsky et al. (2002) Temperate Mixed & Conifer",
            "a": 1.15,
            "b": 1.18,
            "wood_density": 0.52,
            "desc": "Calibrated for temperate mixed deciduous, spruce, pine, and fir stands."
        },
        "boreal_baccini": {
            "name": "Baccini / IPCC Boreal Taiga Forest",
            "a": 0.82,
            "b": 1.25,
            "wood_density": 0.45,
            "desc": "Optimized for high-latitude boreal pine, larch, and spruce forests."
        },
        "plantation_fast": {
            "name": "Fast-Growing Plantation (Eucalyptus / Acacia / Poplar)",
            "a": 0.95,
            "b": 1.32,
            "wood_density": 0.58,
            "desc": "High-density commercial timber and carbon sequestration plantations."
        },
        "custom": {
            "name": "Custom Allometric Equation",
            "a": 1.0,
            "b": 1.2,
            "wood_density": 0.55,
            "desc": "User-calibrated allometric power law."
        }
    }

    @classmethod
    def estimate_from_chm(
        cls,
        chm_path: str,
        output_raster_path: str,
        preset: str = "temperate_lefsky",
        custom_a: float = 1.15,
        custom_b: float = 1.18,
        wood_density: float = 0.52,
        root_to_shoot_ratio: float = 0.235,
        carbon_fraction: float = 0.47,
        co2_multiplier: float = 3.667,
        carbon_price_usd: float = 25.0,
        min_tree_height: float = 2.0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Estimates continuous Aboveground Biomass (AGB Mg/ha), Total Carbon Stock (t C/ha),
        and CO2 Equivalent (t CO2e/ha) rasters directly from a Canopy Height Model (CHM).
        Outputs a 3-band GeoTIFF and comprehensive stand-level carbon inventory JSON report.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        progress(5, "Opening Canopy Height Model (CHM)...")
        ds = gdal.Open(chm_path, gdal.GA_ReadOnly)
        if not ds:
            raise RuntimeError(f"Could not open input CHM raster: {chm_path}")

        gt = ds.GetGeoTransform()
        proj = ds.GetProjection()
        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        x_size = ds.RasterXSize
        y_size = ds.RasterYSize

        pixel_w = abs(gt[1])
        pixel_h = abs(gt[5])
        pixel_area_m2 = pixel_w * pixel_h
        pixel_area_ha = pixel_area_m2 / 10000.0

        p_info = cls.CHM_PRESETS.get(preset.lower(), cls.CHM_PRESETS["temperate_lefsky"])
        a = custom_a if preset == "custom" else p_info["a"]
        b = custom_b if preset == "custom" else p_info["b"]
        w_dens = wood_density if preset == "custom" else p_info["wood_density"]

        model_expr = f"AGB (Mg/ha) = {a:.3f} · H^{b:.3f} (Wood Density = {w_dens:.2f} g/cm³)"
        log(f"<b>Canopy Allometry Model:</b> {p_info['name']}")
        log(f"<b>Mathematical Formulation:</b> <code>{model_expr}</code>")
        log(f"<b>Root-to-Shoot Ratio (IPCC Cairns):</b> {root_to_shoot_ratio:.3f}")
        log(f"<b>Carbon Fraction (IPCC Tier 1/2):</b> {carbon_fraction:.2f} (CO2 Factor: {co2_multiplier:.3f})")
        log(f"<b>Carbon Price Reference:</b> ${carbon_price_usd:.2f} / tonne CO2e")

        progress(15, "Reading raster data and initializing output bands...")
        out_ext = os.path.splitext(output_raster_path)[1].lower()
        if out_ext not in [".tif", ".tiff"]:
            output_raster_path = os.path.splitext(output_raster_path)[0] + ".tif"

        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(
            output_raster_path,
            x_size,
            y_size,
            3,
            gdal.GDT_Float32,
            options=["COMPRESS=DEFLATE", "TILED=YES", "BIGTIFF=IF_SAFER"]
        )
        out_ds.SetGeoTransform(gt)
        out_ds.SetProjection(proj)

        band_agb = out_ds.GetRasterBand(1)
        band_agb.SetDescription("Aboveground_Biomass_Mg_per_ha")
        band_agb.SetNoDataValue(-9999.0)

        band_carbon = out_ds.GetRasterBand(2)
        band_carbon.SetDescription("Total_Carbon_Stock_tonnes_C_per_ha")
        band_carbon.SetNoDataValue(-9999.0)

        band_co2 = out_ds.GetRasterBand(3)
        band_co2.SetDescription("CO2_Equivalent_tonnes_CO2e_per_ha")
        band_co2.SetNoDataValue(-9999.0)

        block_size_y = 512
        num_blocks = math.ceil(y_size / block_size_y)

        total_pixels = 0
        forest_pixels = 0
        total_agb_mg = 0.0
        total_bgb_mg = 0.0
        total_carbon_mg = 0.0
        total_co2e_mg = 0.0
        max_agb_ha = 0.0
        max_carbon_ha = 0.0

        for b_idx in range(num_blocks):
            y_off = b_idx * block_size_y
            rows = min(block_size_y, y_size - y_off)

            chm_block = band.ReadAsArray(0, y_off, x_size, rows).astype(np.float32)
            mask_valid = (chm_block >= min_tree_height)
            if nodata is not None:
                mask_valid &= (chm_block != nodata)

            agb_block = np.full((rows, x_size), -9999.0, dtype=np.float32)
            carbon_block = np.full((rows, x_size), -9999.0, dtype=np.float32)
            co2_block = np.full((rows, x_size), -9999.0, dtype=np.float32)

            if np.any(mask_valid):
                h_vals = chm_block[mask_valid]
                # AGB in Mg / ha (tonnes per hectare)
                agb_vals = a * np.power(h_vals, b)
                # Total carbon in tonnes C / ha: AGB * (1 + root_ratio) * carbon_fraction
                total_c_vals = agb_vals * (1.0 + root_to_shoot_ratio) * carbon_fraction
                # CO2e in tonnes CO2e / ha
                co2_vals = total_c_vals * co2_multiplier

                agb_block[mask_valid] = agb_vals
                carbon_block[mask_valid] = total_c_vals
                co2_block[mask_valid] = co2_vals

                valid_cnt = int(np.sum(mask_valid))
                forest_pixels += valid_cnt
                block_agb_mg = float(np.sum(agb_vals * pixel_area_ha))
                block_bgb_mg = block_agb_mg * root_to_shoot_ratio
                block_c_mg = float(np.sum(total_c_vals * pixel_area_ha))
                block_co2_mg = float(np.sum(co2_vals * pixel_area_ha))

                total_agb_mg += block_agb_mg
                total_bgb_mg += block_bgb_mg
                total_carbon_mg += block_c_mg
                total_co2e_mg += block_co2_mg

                if len(agb_vals) > 0:
                    max_agb_ha = max(max_agb_ha, float(np.max(agb_vals)))
                    max_carbon_ha = max(max_carbon_ha, float(np.max(total_c_vals)))

            total_pixels += (rows * x_size)
            band_agb.WriteArray(agb_block, 0, y_off)
            band_carbon.WriteArray(carbon_block, 0, y_off)
            band_co2.WriteArray(co2_block, 0, y_off)

            pct = 20 + int((b_idx / max(1, num_blocks)) * 70)
            progress(pct, f"Calculating biomass & carbon pixels ({b_idx + 1}/{num_blocks})...")

        band_agb.FlushCache()
        band_carbon.FlushCache()
        band_co2.FlushCache()
        out_ds.FlushCache()
        out_ds = None
        ds = None

        forest_area_ha = forest_pixels * pixel_area_ha
        total_area_ha = total_pixels * pixel_area_ha
        mean_agb_ha = (total_agb_mg / forest_area_ha) if forest_area_ha > 0 else 0.0
        mean_carbon_ha = (total_carbon_mg / forest_area_ha) if forest_area_ha > 0 else 0.0
        economic_value_usd = total_co2e_mg * carbon_price_usd

        progress(95, "Compiling Stand Carbon Inventory Report...")

        base_report, _ = os.path.splitext(output_raster_path)
        report_path = f"{base_report}_carbon_report.json"
        results = {
            "status": "SUCCESS",
            "model": p_info["name"],
            "model_formula": model_expr,
            "wood_density_g_cm3": w_dens,
            "root_to_shoot_ratio": root_to_shoot_ratio,
            "carbon_fraction": carbon_fraction,
            "co2_conversion_factor": co2_multiplier,
            "carbon_price_usd_per_tonne": carbon_price_usd,
            "forest_area_ha": round(forest_area_ha, 3),
            "total_area_ha": round(total_area_ha, 3),
            "forest_canopy_cover_pct": round((forest_pixels / max(1, total_pixels)) * 100.0, 2),
            "total_aboveground_biomass_Mg": round(total_agb_mg, 2),
            "total_belowground_biomass_Mg": round(total_bgb_mg, 2),
            "total_biomass_Mg": round(total_agb_mg + total_bgb_mg, 2),
            "total_carbon_stock_tonnes_C": round(total_carbon_mg, 2),
            "total_co2_equivalent_tonnes_CO2e": round(total_co2e_mg, 2),
            "mean_agb_Mg_per_ha": round(mean_agb_ha, 2),
            "max_agb_Mg_per_ha": round(max_agb_ha, 2),
            "mean_carbon_density_tC_per_ha": round(mean_carbon_ha, 2),
            "max_carbon_density_tC_per_ha": round(max_carbon_ha, 2),
            "estimated_economic_value_usd": round(economic_value_usd, 2),
            "output_raster": output_raster_path,
            "report_path": report_path
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        progress(100, f"Carbon stock estimation complete: {total_carbon_mg:,.1f} tonnes C sequestered!")
        return results

    @classmethod
    def estimate_from_trees_vector(
        cls,
        trees_vector_path: str,
        output_vector_path: str,
        forest_preset: str = "conifer",
        wood_density: float = 0.55,
        root_to_shoot_ratio: float = 0.235,
        carbon_fraction: float = 0.47,
        co2_multiplier: float = 3.667,
        carbon_price_usd: float = 25.0,
        custom_a: float = 0.85,
        custom_b: float = 0.72,
        custom_c: float = 0.38,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Estimates individual tree AGB (kg), Belowground Biomass (kg), Total Carbon (kg C),
        and CO2e (kg) from detected tree apex markers or crown polygons.
        Outputs enriched vector layer (GPKG or SHP) and stand summary report.
        """
        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def progress(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        progress(5, "Opening trees inventory vector layer...")
        ds_v = ogr.Open(trees_vector_path, 0)
        if not ds_v:
            raise RuntimeError(f"Could not open trees layer: {trees_vector_path}")
        lyr = ds_v.GetLayer(0)
        srs = lyr.GetSpatialRef()
        wkt = srs.ExportToWkt() if srs else ""
        tree_count = lyr.GetFeatureCount()

        # Presets for DBH estimation if DBH field is not yet computed:
        # ln(DBH) = a + b*ln(H) + c*ln(CD)
        dbh_presets = {
            "conifer": (0.85, 0.72, 0.38),
            "hardwood": (1.02, 0.68, 0.42),
            "tropical": (1.15, 0.75, 0.35),
            "eucalyptus": (0.92, 0.81, 0.28),
            "custom": (custom_a, custom_b, custom_c)
        }
        coeff = dbh_presets.get(forest_preset.lower(), dbh_presets["conifer"])
        da, db, dc = coeff

        biomass_model_name = f"Chave et al. (2014) Allometric AGB (Wood Density={wood_density:.2f} g/cm³)"
        log(f"<b>Individual Tree Biomass Equation:</b> {biomass_model_name}")
        log(f"<b>Root-to-Shoot Ratio (IPCC Cairns):</b> {root_to_shoot_ratio:.3f}")
        log(f"<b>Carbon Fraction:</b> {carbon_fraction:.2f} | <b>Carbon Valuation:</b> ${carbon_price_usd:.2f}/tonne CO2e")

        records = []
        agb_list = []
        bgb_list = []
        carbon_list = []
        co2_list = []
        val_list = []

        progress(15, f"Processing {tree_count:,} trees for AGB & carbon estimation...")

        for i, feat in enumerate(lyr):
            geom = feat.GetGeometryRef()
            if not geom:
                continue

            h = float(feat.GetField("Height_m")) if feat.GetFieldIndex("Height_m") >= 0 else 15.0
            cd = float(feat.GetField("Crown_Diam_m")) if feat.GetFieldIndex("Crown_Diam_m") >= 0 else (h * 0.25)
            h = max(1.5, h)
            cd = max(0.5, cd)

            # DBH in cm
            if feat.GetFieldIndex("DBH_cm") >= 0 and feat.GetField("DBH_cm") is not None and float(feat.GetField("DBH_cm")) > 0:
                dbh_cm = float(feat.GetField("DBH_cm"))
            else:
                ln_dbh = da + db * math.log(h) + dc * math.log(cd)
                dbh_cm = round(math.exp(ln_dbh), 1)

            # Basal area m²
            radius_m = (dbh_cm / 100.0) / 2.0
            ba_m2 = round(math.pi * (radius_m ** 2), 4)

            # AGB (kg) - Chave et al. (2014)
            agb_kg = round(0.0673 * ((wood_density * (dbh_cm ** 2) * h) ** 0.976), 1)
            bgb_kg = round(agb_kg * root_to_shoot_ratio, 1)
            total_biomass_kg = round(agb_kg + bgb_kg, 1)

            # Carbon Stock (kg C) & CO2e (kg CO2e)
            carbon_kg = round(total_biomass_kg * carbon_fraction, 2)
            co2_kg = round(carbon_kg * co2_multiplier, 2)
            econ_val_usd = round((co2_kg / 1000.0) * carbon_price_usd, 2)

            t_id = feat.GetField("Tree_ID") if feat.GetFieldIndex("Tree_ID") >= 0 else (i + 1)
            if geom.GetGeometryType() in (ogr.wkbPoint, ogr.wkbPoint25D):
                gx, gy = geom.GetX(), geom.GetY()
                geom_copy = geom.Clone()
            else:
                centroid = geom.Centroid()
                gx, gy = centroid.GetX(), centroid.GetY()
                geom_copy = geom.Clone()

            records.append({
                "id": t_id,
                "x": gx,
                "y": gy,
                "height": h,
                "crown_diam": cd,
                "dbh_cm": dbh_cm,
                "basal_area": ba_m2,
                "agb_kg": agb_kg,
                "bgb_kg": bgb_kg,
                "total_biomass_kg": total_biomass_kg,
                "carbon_kg": carbon_kg,
                "co2e_kg": co2_kg,
                "carbon_val_usd": econ_val_usd,
                "geom": geom_copy
            })

            agb_list.append(agb_kg)
            bgb_list.append(bgb_kg)
            carbon_list.append(carbon_kg)
            co2_list.append(co2_kg)
            val_list.append(econ_val_usd)

            if i % 1000 == 0:
                pct = 15 + int((i / max(1, tree_count)) * 65)
                progress(pct, f"Processed {i:,} / {tree_count:,} individual trees...")

        # Export enriched vector layer
        progress(85, "Writing enriched Carbon & Biomass vector layer...")
        ext = os.path.splitext(output_vector_path)[1].lower()
        driver_name = "GPKG" if ext == ".gpkg" else "ESRI Shapefile"
        driver = ogr.GetDriverByName(driver_name)
        if not driver:
            driver = ogr.GetDriverByName("GPKG")
            output_vector_path = os.path.splitext(output_vector_path)[0] + ".gpkg"

        if os.path.exists(output_vector_path):
            driver.DeleteDataSource(output_vector_path)

        out_ds = driver.CreateDataSource(output_vector_path)
        first_geom_type = records[0]["geom"].GetGeometryType() if records else ogr.wkbPoint
        out_layer = out_ds.CreateLayer("tree_carbon_stock", srs, first_geom_type)

        fields = [
            ("Tree_ID", ogr.OFTInteger),
            ("Height_m", ogr.OFTReal),
            ("Crown_Diam_m", ogr.OFTReal),
            ("DBH_cm", ogr.OFTReal),
            ("BasalArea_m2", ogr.OFTReal),
            ("AGB_kg", ogr.OFTReal),
            ("BGB_kg", ogr.OFTReal),
            ("TotalBiom_kg", ogr.OFTReal),
            ("Carbon_kg", ogr.OFTReal),
            ("CO2e_kg", ogr.OFTReal),
            ("Carbon_Val_USD", ogr.OFTReal),
        ]
        for f_name, f_type in fields:
            out_layer.CreateField(ogr.FieldDefn(f_name, f_type))

        for r in records:
            feat = ogr.Feature(out_layer.GetLayerDefn())
            feat.SetField("Tree_ID", int(r["id"]))
            feat.SetField("Height_m", float(r["height"]))
            feat.SetField("Crown_Diam_m", float(r["crown_diam"]))
            feat.SetField("DBH_cm", float(r["dbh_cm"]))
            feat.SetField("BasalArea_m2", float(r["basal_area"]))
            feat.SetField("AGB_kg", float(r["agb_kg"]))
            feat.SetField("BGB_kg", float(r["bgb_kg"]))
            feat.SetField("TotalBiom_kg", float(r["total_biomass_kg"]))
            feat.SetField("Carbon_kg", float(r["carbon_kg"]))
            feat.SetField("CO2e_kg", float(r["co2e_kg"]))
            feat.SetField("Carbon_Val_USD", float(r["carbon_val_usd"]))
            feat.SetGeometry(r["geom"])
            out_layer.CreateFeature(feat)
            feat = None

        out_ds.FlushCache()
        out_ds = None

        total_agb_t = float(np.sum(agb_list) / 1000.0)
        total_bgb_t = float(np.sum(bgb_list) / 1000.0)
        total_carbon_t = float(np.sum(carbon_list) / 1000.0)
        total_co2e_t = float(np.sum(co2_list) / 1000.0)
        total_value_usd = float(np.sum(val_list))

        base_report, _ = os.path.splitext(output_vector_path)
        report_path = f"{base_report}_carbon_report.json"
        results = {
            "status": "SUCCESS",
            "total_trees": len(records),
            "biomass_model": biomass_model_name,
            "wood_density_g_cm3": wood_density,
            "root_to_shoot_ratio": root_to_shoot_ratio,
            "carbon_fraction": carbon_fraction,
            "carbon_price_usd": carbon_price_usd,
            "total_aboveground_biomass_Mg": round(total_agb_t, 2),
            "total_belowground_biomass_Mg": round(total_bgb_t, 2),
            "total_biomass_Mg": round(total_agb_t + total_bgb_t, 2),
            "total_carbon_stock_tonnes_C": round(total_carbon_t, 2),
            "total_co2_equivalent_tonnes_CO2e": round(total_co2e_t, 2),
            "mean_tree_carbon_kg": round(float(np.mean(carbon_list)), 2),
            "mean_tree_agb_kg": round(float(np.mean(agb_list)), 2),
            "total_economic_value_usd": round(total_value_usd, 2),
            "output_vector": output_vector_path,
            "report_path": report_path
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        progress(100, f"Tree carbon analysis complete for {len(records):,} trees!")
        return results
