# -*- coding: utf-8 -*-
"""
GeoStudio - Specialized Algorithm Runners
Contains execution routines for contours, viewshed, cut & fill, flood simulation, and vector buffering.
"""

import os
import tempfile
import numpy as np
from osgeo import gdal, ogr, osr
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsProcessingFeedback,
    QgsSingleBandPseudoColorRenderer, QgsColorRampShader, QgsRasterShader
)
import processing

from core.elevation_styler import ElevationStyler


def run_raster_contours(dialog):
    """Generates contour vector lines from an input DEM."""
    r_id = dialog.raster_combo.currentData()
    if not r_id:
        raise ValueError("Please select an input DEM raster layer.")
    layer = QgsProject.instance().mapLayer(r_id)
    if not layer or not layer.isValid():
        raise ValueError("Selected DEM layer is invalid.")

    interval = dialog.interval_spin.value() if hasattr(dialog, "interval_spin") else 20.0
    base_val = dialog.base_spin.value() if hasattr(dialog, "base_spin") else 0.0

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]" or out_path.endswith(".tif"):
        out_path = tempfile.mktemp(suffix=".gpkg")

    dialog.log(f"Extracting contour lines: interval = <b>{interval:.1f} m</b>, base = <b>{base_val:.1f} m</b>...")
    dialog.progress_bar.setValue(20)

    ds_in = gdal.Open(layer.source(), gdal.GA_ReadOnly)
    if not ds_in:
        raise RuntimeError(f"Could not open input raster: {layer.source()}")
    band = ds_in.GetRasterBand(1)
    nodata = band.GetNoDataValue()

    ext = os.path.splitext(out_path)[1].lower()
    driver_name = "GPKG" if ext == ".gpkg" else "ESRI Shapefile"
    ogr_driver = ogr.GetDriverByName(driver_name)
    if not ogr_driver:
        driver_name = "GPKG"
        ogr_driver = ogr.GetDriverByName("GPKG")
        out_path = tempfile.mktemp(suffix=".gpkg")

    if os.path.exists(out_path):
        ogr_driver.DeleteDataSource(out_path)

    out_ds = ogr_driver.CreateDataSource(out_path)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds_in.GetProjection())
    out_layer_ogr = out_ds.CreateLayer("contours", srs, ogr.wkbLineString)

    id_fld = ogr.FieldDefn("ID", ogr.OFTInteger)
    elev_fld = ogr.FieldDefn("ELEV", ogr.OFTReal)
    out_layer_ogr.CreateField(id_fld)
    out_layer_ogr.CreateField(elev_fld)

    dialog.progress_bar.setValue(45)
    gdal.ContourGenerate(
        band, interval, base_val, [],
        1 if nodata is not None else 0,
        float(nodata) if nodata is not None else 0.0,
        out_layer_ogr, 0, 1
    )

    feat_count = out_layer_ogr.GetFeatureCount()
    del out_layer_ogr, id_fld, elev_fld
    out_ds.FlushCache()
    out_ds = None
    band = None
    ds_in = None

    dialog.progress_bar.setValue(85)
    dialog.log(f"Contour extraction complete: generated <b>{feat_count:,}</b> contour lines.")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        clean_name = layer.name().replace(" [DEM]", "").replace(" [3D Relief]", "")
        qgs_vec = QgsVectorLayer(out_path, f"{clean_name}_contours_{int(interval)}m", "ogr")
        if qgs_vec.isValid():
            QgsProject.instance().addMapLayer(qgs_vec)
            dialog.log(f"Added contour layer to project: <b>{qgs_vec.name()}</b>")


def run_raster_viewshed(dialog):
    """Performs line-of-sight viewshed computation using GDAL."""
    r_id = dialog.raster_combo.currentData()
    if not r_id:
        raise ValueError("Please select an input DEM raster layer.")
    layer = QgsProject.instance().mapLayer(r_id)
    if not layer or not layer.isValid():
        raise ValueError("Selected DEM layer is invalid.")

    obs_x = dialog.observer_x_spin.value()
    obs_y = dialog.observer_y_spin.value()
    obs_h = dialog.observer_h_spin.value()
    tgt_h = dialog.target_h_spin.value()
    max_d = dialog.max_dist_spin.value()

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".tif")

    dialog.log(f"Running Viewshed analysis from observer ({obs_x:.2f}, {obs_y:.2f})...")
    dialog.log(f"Observer height: <b>{obs_h:.1f} m</b> | Target height: <b>{tgt_h:.1f} m</b> | Radius: <b>{max_d:,.0f} m</b>")
    dialog.progress_bar.setValue(30)

    ds_in = gdal.Open(layer.source(), gdal.GA_ReadOnly)
    if not ds_in:
        raise RuntimeError(f"Could not open input raster: {layer.source()}")
    band = ds_in.GetRasterBand(1)

    vs_ds = gdal.ViewshedGenerate(
        srcBand=band, driverName="GTiff", targetRasterName=out_path,
        creationOptions=["TILED=YES", "COMPRESS=LZW"],
        observerX=obs_x, observerY=obs_y, observerHeight=obs_h, targetHeight=tgt_h,
        visibleVal=255.0, invisibleVal=0.0, outOfRangeVal=0.0, noDataVal=0.0,
        dfCurvCoeff=0.85714, mode=gdal.GVM_Diagonal, maxDistance=max_d
    )
    band = None
    vs_ds = None
    ds_in = None

    dialog.progress_bar.setValue(85)
    dialog.log("Viewshed line-of-sight computation complete.")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        clean_name = layer.name().replace(" [DEM]", "").replace(" [3D Relief]", "")
        vs_layer = QgsRasterLayer(out_path, f"{clean_name}_viewshed")
        if vs_layer.isValid():
            fcn = QgsColorRampShader()
            fcn.setColorRampType(QgsColorRampShader.Exact)
            fcn.setColorRampItemList([
                QgsColorRampShader.ColorRampItem(0, QColor(0, 0, 0, 0), "Invisible"),
                QgsColorRampShader.ColorRampItem(255, QColor(34, 197, 94, 180), "Visible")
            ])
            shader = QgsRasterShader()
            shader.setRasterShaderFunction(fcn)
            renderer = QgsSingleBandPseudoColorRenderer(vs_layer.dataProvider(), 1, shader)
            vs_layer.setRenderer(renderer)
            vs_layer.triggerRepaint()
            QgsProject.instance().addMapLayer(vs_layer)
            dialog.log(f"Added viewshed visibility layer to project: <b>{vs_layer.name()}</b>")


def run_terrain_cutfill(dialog):
    """Performs earthwork cut and fill volumetric calculation."""
    from core.earthworks.cut_fill_engine import CutFillEngine
    r_id = dialog.raster_combo.currentData()
    if not r_id:
        raise ValueError("Please select a base DEM layer.")
    base_layer = QgsProject.instance().mapLayer(r_id)
    if not base_layer or not base_layer.isValid():
        raise ValueError("Selected base DEM is invalid.")

    mode_idx = dialog.compare_mode_combo.currentIndex()
    datum = dialog.datum_height_spin.value() if mode_idx == 0 else None
    comp_layer = None
    if mode_idx == 1:
        comp_id = dialog.compare_dem_combo.currentData() if hasattr(dialog, "compare_dem_combo") else None
        if not comp_id:
            raise ValueError("Please select a comparison (second) DEM layer.")
        comp_layer = QgsProject.instance().mapLayer(comp_id)

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".tif")

    res = CutFillEngine.compute_cut_fill(
        base_source=base_layer, comp_source=comp_layer, datum_elevation=datum,
        output_diff_path=out_path, generate_daylight_vector=False,
        progress_callback=lambda pct, msg: (dialog.progress_bar.setValue(int(pct)), dialog.progress_bar.setFormat(msg))
    )

    dialog.log(CutFillEngine.generate_report_text(res))

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        clean_name = base_layer.name().replace(" [DEM]", "").replace(" [3D Relief]", "")
        diff_layer = QgsRasterLayer(out_path, f"{clean_name}_cutfill_diff")
        if diff_layer.isValid():
            ElevationStyler.apply_cut_fill_colormap(diff_layer)
            QgsProject.instance().addMapLayer(diff_layer)
            dialog.log(f"Added earthwork difference raster to project: <b>{diff_layer.name()}</b>")


def run_terrain_flood(dialog):
    """Simulates flood inundation and computes depth/volume statistics."""
    r_id = dialog.raster_combo.currentData()
    if not r_id:
        raise ValueError("Please select an input DEM layer.")
    base_layer = QgsProject.instance().mapLayer(r_id)
    if not base_layer or not base_layer.isValid():
        raise ValueError("Selected DEM layer is invalid.")

    water_lvl = dialog.water_level_spin.value()
    dialog.log(f"Simulating flood inundation at elevation: <b>{water_lvl:.2f} m</b>...")
    dialog.progress_bar.setValue(25)

    ds_in = gdal.Open(base_layer.source(), gdal.GA_ReadOnly)
    gt = ds_in.GetGeoTransform()
    w = ds_in.RasterXSize
    h = ds_in.RasterYSize
    cell_area = abs(gt[1]) * abs(gt[5])

    b = ds_in.GetRasterBand(1)
    nodata = b.GetNoDataValue()
    arr = b.ReadAsArray().astype(np.float32)
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)

    valid_mask = ~np.isnan(arr)
    flood_mask = valid_mask & (arr <= water_lvl)
    depth_arr = np.where(flood_mask, water_lvl - arr, 0.0)

    flooded_cells = int(np.sum(flood_mask))
    flooded_area_m2 = flooded_cells * cell_area
    flooded_area_km2 = flooded_area_m2 / 1e6
    inundated_vol_m3 = float(np.sum(depth_arr[flood_mask]) * cell_area)
    max_depth = float(np.max(depth_arr[flood_mask])) if flooded_cells > 0 else 0.0
    avg_depth = float(np.mean(depth_arr[flood_mask])) if flooded_cells > 0 else 0.0

    dialog.progress_bar.setValue(75)
    dialog.log("\n<b>===== FLOOD & INUNDATION SIMULATION REPORT =====</b>")
    dialog.log(f"Target Water Elevation: <b>{water_lvl:.2f} m</b>")
    dialog.log(f"Flooded Area: <b>{flooded_area_km2:.3f} km²</b> ({flooded_area_m2:,.0f} m²)")
    dialog.log(f"Inundated Water Volume: <span style='color:#0284c7;'><b>{inundated_vol_m3:,.1f} m³</b></span>")
    dialog.log(f"Maximum Water Depth: <b>{max_depth:.2f} m</b> | Average Depth: <b>{avg_depth:.2f} m</b>")
    dialog.log("================================================\n")

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".tif")

    driver = gdal.GetDriverByName("GTiff")
    ds_out = driver.Create(out_path, w, h, 1, gdal.GDT_Float32, ["TILED=YES", "COMPRESS=LZW"])
    ds_out.SetGeoTransform(gt)
    ds_out.SetProjection(ds_in.GetProjection())
    depth_out = np.where(flood_mask, depth_arr, -9999.0)
    b_out = ds_out.GetRasterBand(1)
    b_out.SetNoDataValue(-9999.0)
    b_out.WriteArray(depth_out)
    b_out = None
    b = None
    ds_out.FlushCache()
    ds_out = None
    ds_in = None

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        clean_name = base_layer.name().replace(" [DEM]", "").replace(" [3D Relief]", "")
        flood_layer = QgsRasterLayer(out_path, f"{clean_name}_flood_depth_{int(water_lvl)}m")
        if flood_layer.isValid():
            QgsProject.instance().addMapLayer(flood_layer)
            dialog.log(f"Added flood depth raster to project: <b>{flood_layer.name()}</b>")


def run_vector_buffer(dialog):
    """Executes native QGIS buffer on vector layers."""
    v_id = dialog.vector_combo.currentData()
    if not v_id:
        raise ValueError("Please select an input vector layer.")
    layer = QgsProject.instance().mapLayer(v_id)

    params = {
        "INPUT": layer,
        "DISTANCE": dialog.dist_spin.value(),
        "SEGMENTS": dialog.seg_spin.value(),
        "DISSOLVE": False,
        "OUTPUT": "memory:",
    }
    dialog.log(f"Input parameters:\n{params}\n")
    res = processing.run("native:buffer", params, feedback=QgsProcessingFeedback())
    out = res.get("OUTPUT")
    if out:
        if isinstance(out, str):
            out = QgsVectorLayer(out, f"{layer.name()}_buffer", "ogr")
        out.setName(f"{layer.name()}_buffer")
        if dialog.open_output_cb.isChecked():
            QgsProject.instance().addMapLayer(out)
            dialog.log(f"Loaded output layer: <b>{out.name()}</b>")


# ── 8. Forestry & Tree Metrics Runners ──

def run_forestry_detect(dialog):
    """Executes individual tree detection, apex vector generation, and summary PNG report."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    r_data = dialog.raster_combo.currentData()
    if r_data and os.path.exists(str(r_data)):
        source_path = str(r_data)
        layer_name = os.path.basename(source_path)
    elif r_data:
        layer = QgsProject.instance().mapLayer(r_data)
        if not layer or not layer.isValid():
            raise ValueError("Selected layer is invalid.")
        source_path = layer.source()
        layer_name = layer.name()
    else:
        txt = dialog.raster_combo.currentText().replace("📁 ", "").replace("☁️ ", "").replace("🗺 ", "").strip()
        if os.path.exists(txt):
            source_path = txt
            layer_name = os.path.basename(txt)
        else:
            raise ValueError("Please select or browse an input Point Cloud (.las/.laz) or CHM raster.")

    min_h = dialog.min_tree_height_spin.value() if hasattr(dialog, "min_tree_height_spin") else 2.0
    mode_idx = dialog.search_mode_combo.currentIndex() if hasattr(dialog, "search_mode_combo") else 0
    mode_map = [
        ("vwf_mixed", 5),
        ("vwf_conifer", 5),
        ("vwf_deciduous", 5),
        ("custom", 5),
        ("fixed", 5),
        ("fixed", 3),
        ("fixed", 7)
    ]
    search_mode, win_size = mode_map[min(mode_idx, len(mode_map) - 1)]

    vwf_a = dialog.vwf_a_spin.value() if hasattr(dialog, "vwf_a_spin") else 0.28
    vwf_b = dialog.vwf_b_spin.value() if hasattr(dialog, "vwf_b_spin") else 1.5
    vwf_min_win = dialog.vwf_min_win_spin.value() if hasattr(dialog, "vwf_min_win_spin") else 3
    vwf_max_win = dialog.vwf_max_win_spin.value() if hasattr(dialog, "vwf_max_win_spin") else 15

    smoothing_sigma = dialog.smoothing_spin.value() if hasattr(dialog, "smoothing_spin") else 0.8
    min_prom = dialog.min_prominence_spin.value() if hasattr(dialog, "min_prominence_spin") else 0.35
    alpha_prom = dialog.alpha_prominence_spin.value() if hasattr(dialog, "alpha_prominence_spin") else 0.10
    ground_cov = dialog.ground_coverage_spin.value() if hasattr(dialog, "ground_coverage_spin") else 15.0
    delineate_crowns = dialog.cb_delineate_crowns.isChecked() if hasattr(dialog, "cb_delineate_crowns") else False

    generate_png = dialog.cb_generate_png.isChecked() if hasattr(dialog, "cb_generate_png") else True
    png_path = dialog.png_path_edit.text().strip() if hasattr(dialog, "png_path_edit") else ""

    lbl_idx = dialog.label_style_combo.currentIndex() if hasattr(dialog, "label_style_combo") else 0
    lbl_styles = ["number", "none", "number_height"]
    label_style = lbl_styles[min(lbl_idx, len(lbl_styles) - 1)]

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".gpkg")

    dialog.log(f"Running Precision Individual Tree Detection (ITD) on <b>{layer_name}</b>...")
    dialog.log(f"Parameters: Model = <b>{search_mode.upper()}</b>, Min Height = <b>{min_h:.1f} m</b>, Prominence = <b>{min_prom:.2f} m</b> (α={alpha_prom:.2f}), Sigma = <b>{smoothing_sigma:.2f}</b>")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.detect_trees(
        chm_path=source_path,
        output_vector_path=out_path,
        min_height=min_h,
        search_mode=search_mode,
        window_size=win_size,
        smoothing_sigma=smoothing_sigma,
        min_prominence=min_prom,
        alpha_prominence=alpha_prom,
        ground_coverage_threshold_pct=ground_cov,
        vwf_a=vwf_a,
        vwf_b=vwf_b,
        vwf_min_win=vwf_min_win,
        vwf_max_win=vwf_max_win,
        delineate_crowns=delineate_crowns,
        generate_png=generate_png,
        png_path=png_path if png_path else None,
        label_style=label_style,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Forest Stand Inventory Summary:</b>")
    dialog.log(f"• Total Trees Counted: <b>{res['total_trees']:,}</b>")
    dialog.log(f"• Survey Area: <b>{res['forest_area_ha']:.2f} ha</b> (Density: <b>{res['density_per_ha']:.0f} trees/ha</b>)")
    dialog.log(f"• Height (Mean / Max): <b>{res['mean_height']:.1f} m</b> / <b>{res['max_height']:.1f} m</b>")
    if res.get("mean_crown_diam"):
        dialog.log(f"• Crown Diameter (Mean / Max): <b>{res['mean_crown_diam']:.2f} m</b> / <b>{res['max_crown_diam']:.2f} m</b>")

    if res.get("json_report_path") and os.path.exists(res["json_report_path"]):
        dialog.log(f"• Machine-Readable Report: <a href='file:///{res['json_report_path']}'>{os.path.basename(res['json_report_path'])}</a>")
    if res.get("png_path") and os.path.exists(res["png_path"]):
        dialog.log(f"• Labeled Summary Map PNG: <a href='file:///{res['png_path']}'>{os.path.basename(res['png_path'])}</a>")

    if dialog.open_output_cb.isChecked():
        clean_name = layer_name.replace(" [DEM]", "").replace(" [CHM]", "").replace(" [LiDAR]", "")
        if os.path.exists(out_path):
            vec = QgsVectorLayer(out_path, f"{clean_name}_detected_trees", "ogr")
            if vec.isValid():
                QgsProject.instance().addMapLayer(vec)
                dialog.log(f"Added detected trees layer to canvas: <b>{vec.name()}</b>")

        crowns_p = res.get("crowns_vector_path")
        if crowns_p and os.path.exists(crowns_p):
            cvec = QgsVectorLayer(crowns_p, f"{clean_name}_crown_boundaries", "ogr")
            if cvec.isValid():
                QgsProject.instance().addMapLayer(cvec)
                dialog.log(f"Added individual crown polygons layer to canvas: <b>{cvec.name()}</b>")


def run_forestry_heights(dialog):
    """Samples individual tree heights from CHM raster or point cloud onto a tree point layer."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    v_id = dialog.vector_combo.currentData()
    if not v_id:
        raise ValueError("Please select an input detected trees point layer.")
    v_layer = QgsProject.instance().mapLayer(v_id)

    r_data = dialog.raster_combo.currentData()
    if r_data and os.path.exists(str(r_data)):
        source_path = str(r_data)
    elif r_data:
        r_layer = QgsProject.instance().mapLayer(r_data)
        if not r_layer or not r_layer.isValid():
            raise ValueError("Selected canopy layer is invalid.")
        source_path = r_layer.source()
    else:
        txt = dialog.raster_combo.currentText().replace("📁 ", "").replace("☁️ ", "").replace("🗺 ", "").strip()
        if os.path.exists(txt):
            source_path = txt
        else:
            raise ValueError("Please select or browse an input Point Cloud (.las/.laz) or CHM raster.")

    radius_m = dialog.height_radius_spin.value() if hasattr(dialog, "height_radius_spin") else 1.0

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".gpkg")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.extract_tree_heights(
        trees_vector_path=v_layer.source(),
        chm_path=source_path,
        output_vector_path=out_path,
        search_radius_m=radius_m,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Extracted Tree Height Metrics:</b>")
    dialog.log(f"• Total Trees Processed: <b>{res['total_trees']:,}</b>")
    dialog.log(f"• Mean Height: <b>{res['mean_height']:.2f} m</b> (Median: <b>{res['median_height']:.2f} m</b>)")
    dialog.log(f"• Range: <b>{res['min_height']:.2f} m</b> – <b>{res['max_height']:.2f} m</b>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        vec = QgsVectorLayer(out_path, f"{v_layer.name()}_heights", "ogr")
        if vec.isValid():
            QgsProject.instance().addMapLayer(vec)
            dialog.log(f"Added updated trees height layer: <b>{vec.name()}</b>")


def run_forestry_crown(dialog):
    """Delineates crown boundary polygons and calculates crown diameter & spread."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    v_id = dialog.vector_combo.currentData()
    if not v_id:
        raise ValueError("Please select an input detected trees point layer.")
    v_layer = QgsProject.instance().mapLayer(v_id)

    r_data = dialog.raster_combo.currentData()
    if r_data and os.path.exists(str(r_data)):
        source_path = str(r_data)
    elif r_data:
        r_layer = QgsProject.instance().mapLayer(r_data)
        if not r_layer or not r_layer.isValid():
            raise ValueError("Selected canopy layer is invalid.")
        source_path = r_layer.source()
    else:
        txt = dialog.raster_combo.currentText().replace("📁 ", "").replace("☁️ ", "").replace("🗺 ", "").strip()
        if os.path.exists(txt):
            source_path = txt
        else:
            raise ValueError("Please select or browse an input Point Cloud (.las/.laz) or CHM raster.")

    max_rad = dialog.max_crown_radius_spin.value() if hasattr(dialog, "max_crown_radius_spin") else 12.0
    cutoff = (dialog.crown_base_spin.value() / 100.0) if hasattr(dialog, "crown_base_spin") else 0.35

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".gpkg")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.measure_crown_diameter(
        trees_vector_path=v_layer.source(),
        chm_path=source_path,
        output_vector_path=out_path,
        max_crown_radius_m=max_rad,
        crown_base_ratio=cutoff,
        progress_callback=_progress,
        log_callback=dialog.log
    )


    dialog.log(f"\n<b>Crown Segmentation Metrics:</b>")
    dialog.log(f"• Total Crowns Delineated: <b>{res['total_crowns']:,}</b>")
    dialog.log(f"• Mean Crown Diameter: <b>{res['mean_crown_diam']:.2f} m</b> (Max: <b>{res['max_crown_diam']:.2f} m</b>)")
    dialog.log(f"• Mean Crown Footprint Area: <b>{res['mean_crown_area']:.2f} m²</b>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        vec = QgsVectorLayer(out_path, f"{v_layer.name()}_crowns", "ogr")
        if vec.isValid():
            QgsProject.instance().addMapLayer(vec)
            dialog.log(f"Added crown polygons layer to canvas: <b>{vec.name()}</b>")


def run_forestry_dbh(dialog):
    """Calculates DBH (cm), Basal Area (m²), and Biomass (kg) using forestry allometry."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    v_id = dialog.vector_combo.currentData()
    if not v_id:
        raise ValueError("Please select an input trees vector layer.")
    v_layer = QgsProject.instance().mapLayer(v_id)

    preset_map = {
        0: "conifer",
        1: "hardwood",
        2: "tropical",
        3: "eucalyptus",
        4: "custom"
    }
    preset_idx = dialog.dbh_preset_combo.currentIndex() if hasattr(dialog, "dbh_preset_combo") else 0
    preset_key = preset_map.get(preset_idx, "conifer")

    ca = dialog.custom_a_spin.value() if hasattr(dialog, "custom_a_spin") else 0.85
    cb = dialog.custom_b_spin.value() if hasattr(dialog, "custom_b_spin") else 0.72
    cc = dialog.custom_c_spin.value() if hasattr(dialog, "custom_c_spin") else 0.38
    density = dialog.wood_density_spin.value() if hasattr(dialog, "wood_density_spin") else 0.55

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".gpkg")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.calculate_dbh(
        trees_vector_path=v_layer.source(),
        output_vector_path=out_path,
        method="allometric",
        forest_preset=preset_key,
        custom_a=ca,
        custom_b=cb,
        custom_c=cc,
        wood_density=density,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Estimated Forest Timber & Allometry Metrics:</b>")
    dialog.log(f"• DBH Source: <b>{res.get('dbh_source', 'Allometric Model')}</b> (Confidence: <b>{res.get('dbh_confidence', 'Estimated')}</b>)")
    dialog.log(f"• Allometric DBH Model: <code>{res.get('dbh_model', '')}</code>")
    dialog.log(f"• Biomass Allometry: <code>{res.get('biomass_model', '')}</code>")
    dialog.log(f"• Total Trees Analyzed: <b>{res['total_trees']:,}</b>")
    dialog.log(f"• Mean DBH: <b>{res['mean_dbh_cm']:.1f} cm</b> (Range: <b>{res['min_dbh_cm']:.1f} cm</b> – <b>{res['max_dbh_cm']:.1f} cm</b>)")
    dialog.log(f"• Total Stand Basal Area: <b>{res['total_basal_area_m2']:.2f} m²</b>")
    dialog.log(f"• Total Stand Aboveground Biomass: <b>{res['total_biomass_tons']:.2f} metric tons</b>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        vec = QgsVectorLayer(out_path, f"{v_layer.name()}_dbh_biomass", "ogr")
        if vec.isValid():
            QgsProject.instance().addMapLayer(vec)
            dialog.log(f"Added DBH & Biomass tree layer: <b>{vec.name()}</b>")


def run_forestry_validate(dialog):
    """Executes scientific ITD accuracy validation (Precision, Recall, F1, and Height RMSE)."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    # 1. Resolve detected trees source
    d_data = dialog.detected_combo.currentData() if hasattr(dialog, "detected_combo") else None
    if d_data and os.path.exists(str(d_data)):
        det_path = str(d_data)
        det_name = os.path.basename(det_path)
    elif d_data:
        d_lyr = QgsProject.instance().mapLayer(d_data)
        if not d_lyr or not d_lyr.isValid():
            raise ValueError("Selected detected trees layer is invalid.")
        det_path = d_lyr.source()
        det_name = d_lyr.name()
    else:
        txt = dialog.detected_combo.currentText().replace("🌲 ", "").replace("📁 ", "").strip()
        if os.path.exists(txt):
            det_path = txt
            det_name = os.path.basename(txt)
        else:
            raise ValueError("Please select or browse the detected trees vector layer.")

    # 2. Resolve reference ground-truth source
    r_data = dialog.reference_combo.currentData() if hasattr(dialog, "reference_combo") else None
    if r_data and os.path.exists(str(r_data)):
        ref_path = str(r_data)
        ref_name = os.path.basename(ref_path)
    elif r_data:
        r_lyr = QgsProject.instance().mapLayer(r_data)
        if not r_lyr or not r_lyr.isValid():
            raise ValueError("Selected reference ground-truth layer is invalid.")
        ref_path = r_lyr.source()
        ref_name = r_lyr.name()
    else:
        rtxt = dialog.reference_combo.currentText().replace("🎯 ", "").replace("📁 ", "").strip()
        if os.path.exists(rtxt):
            ref_path = rtxt
            ref_name = os.path.basename(rtxt)
        else:
            raise ValueError("Please select or browse the reference ground-truth vector layer.")

    match_dist = dialog.match_dist_spin.value() if hasattr(dialog, "match_dist_spin") else 2.0
    h_tol = dialog.h_tol_spin.value() if hasattr(dialog, "h_tol_spin") else 30.0

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".gpkg")

    dialog.log(f"Validating ITD Detections: <b>{det_name}</b> vs Reference: <b>{ref_name}</b>...")
    dialog.log(f"Tolerance: Match Distance = <b>{match_dist:.1f} m</b>, Height Error Tolerance = <b>{h_tol:.0f}%</b>")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.validate_accuracy(
        detected_vector_path=det_path,
        reference_vector_path=ref_path,
        output_vector_path=out_path,
        match_distance_m=match_dist,
        height_tolerance_pct=h_tol,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        val_vec = QgsVectorLayer(out_path, "itd_accuracy_validation", "ogr")
        if val_vec.isValid():
            QgsProject.instance().addMapLayer(val_vec)
            dialog.log(f"Added classified validation vector layer: <b>{val_vec.name()}</b>")


def run_forestry_report(dialog):
    """Compiles a comprehensive machine-readable GeoStudio_ITD_Report.json and 300-DPI publication chart."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    # 1. Resolve Tree Inventory Vector
    t_data = dialog.trees_combo.currentData() if hasattr(dialog, "trees_combo") else None
    if t_data and os.path.exists(str(t_data)):
        trees_path = str(t_data)
        layer_name = os.path.basename(trees_path)
    elif t_data:
        t_lyr = QgsProject.instance().mapLayer(t_data)
        if not t_lyr or not t_lyr.isValid():
            raise ValueError("Selected tree inventory layer is invalid.")
        trees_path = t_lyr.source()
        layer_name = t_lyr.name()
    else:
        txt = dialog.trees_combo.currentText().replace("🌲 ", "").replace("📁 ", "").strip()
        if os.path.exists(txt):
            trees_path = txt
            layer_name = os.path.basename(txt)
        else:
            raise ValueError("Please select or browse the tree inventory vector layer.")

    # 2. Optional validation benchmark
    val_path = None
    if hasattr(dialog, "validation_combo"):
        v_data = dialog.validation_combo.currentData()
        if v_data and os.path.exists(str(v_data)):
            val_path = str(v_data)
        else:
            v_txt = dialog.validation_combo.currentText().replace("🎯 ", "").replace("📁 ", "").strip()
            if os.path.exists(v_txt):
                val_path = v_txt

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]" or not out_path.lower().endswith(".png"):
        base_dir = os.path.dirname(trees_path) or tempfile.gettempdir()
        out_path = os.path.join(base_dir, f"{os.path.splitext(os.path.basename(trees_path))[0]}_inventory_report.png")

    dialog.log(f"Compiling Precision Forestry Inventory Report from: <b>{layer_name}</b>...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.generate_inventory_report(
        trees_vector_path=trees_path,
        output_report_path=out_path,
        validation_vector_path=val_path,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Forestry Inventory Report Generated:</b>")
    dialog.log(f"• Total Trees Census: <b>{res['total_trees']:,}</b> (Density: <b>{res['density_per_ha']:.0f} trees/ha</b>)")
    dialog.log(f"• Stand Height (Mean / Max): <b>{res['mean_height']:.1f} m</b> / <b>{res['max_height']:.1f} m</b>")
    dialog.log(f"• Machine-Readable Report: <a href='file:///{res['json_report_path']}'>{os.path.basename(res['json_report_path'])}</a>")
    dialog.log(f"• 300-DPI Publication Report: <a href='file:///{res['image_report_path']}'>{os.path.basename(res['image_report_path'])}</a>")


def run_forestry_carbon(dialog):
    """Executes Aboveground Biomass (AGB) and Carbon Stock estimation from CHM or Trees Vector."""
    from core.forestry.tree_metrics_engine import TreeMetricsEngine

    is_chm = dialog.rb_carbon_chm.isChecked() if hasattr(dialog, "rb_carbon_chm") else True

    preset_map = {
        0: "temperate_lefsky",
        1: "tropical_asner",
        2: "boreal_baccini",
        3: "plantation_fast",
        4: "custom"
    }
    p_idx = dialog.preset_combo.currentIndex() if hasattr(dialog, "preset_combo") else 0
    preset_key = preset_map.get(p_idx, "temperate_lefsky")

    w_dens = dialog.wood_density_spin.value() if hasattr(dialog, "wood_density_spin") else 0.52
    r_ratio = dialog.root_shoot_spin.value() if hasattr(dialog, "root_shoot_spin") else 0.235
    c_frac = dialog.carbon_fraction_spin.value() if hasattr(dialog, "carbon_fraction_spin") else 0.47
    c_price = dialog.carbon_price_spin.value() if hasattr(dialog, "carbon_price_spin") else 25.0

    out_path = dialog.output_edit.text().strip()
    if is_chm:
        r_id = dialog.raster_combo.currentData()
        if not r_id:
            # check raw text
            txt = dialog.raster_combo.currentText().replace("🌲 ", "").strip()
            if os.path.exists(txt):
                in_path = txt
            else:
                raise ValueError("Please select a valid Canopy Height Model (CHM) raster.")
        else:
            lyr = QgsProject.instance().mapLayer(r_id)
            if not lyr:
                raise ValueError("Selected CHM layer is invalid.")
            in_path = lyr.source()

        if not out_path or out_path == "[Create temporary layer]" or not out_path.lower().endswith(".tif"):
            out_path = tempfile.mktemp(suffix=".tif")
    else:
        v_id = dialog.vector_combo.currentData()
        if not v_id:
            txt = dialog.vector_combo.currentText().replace("📍 ", "").strip()
            if os.path.exists(txt):
                in_path = txt
            else:
                raise ValueError("Please select an input Trees Vector layer.")
        else:
            lyr = QgsProject.instance().mapLayer(v_id)
            if not lyr:
                raise ValueError("Selected trees layer is invalid.")
            in_path = lyr.source()

        if not out_path or out_path == "[Create temporary layer]":
            out_path = tempfile.mktemp(suffix=".gpkg")

    dialog.log(f"Initiating AGB & Carbon Stock Estimation Engine...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = TreeMetricsEngine.estimate_agb_and_carbon(
        input_path=in_path,
        output_path=out_path,
        is_raster_chm=is_chm,
        preset=preset_key,
        wood_density=w_dens,
        root_to_shoot_ratio=r_ratio,
        carbon_fraction=c_frac,
        carbon_price_usd=c_price,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Forest Carbon & Biomass Inventory Summary:</b>")
    dialog.log(f"• Total Aboveground Biomass (AGB): <b>{res['total_aboveground_biomass_Mg']:,.1f} metric tons (Mg)</b>")
    dialog.log(f"• Total Belowground Biomass (BGB): <b>{res['total_belowground_biomass_Mg']:,.1f} metric tons</b>")
    dialog.log(f"• Total Carbon Stock (AGC + BGC): <b>{res['total_carbon_stock_tonnes_C']:,.1f} tonnes C</b>")
    dialog.log(f"• Equivalent CO₂ Sequestered: <b>{res['total_co2_equivalent_tonnes_CO2e']:,.1f} tonnes CO₂e</b>")
    if "mean_carbon_density_tC_per_ha" in res:
        dialog.log(f"• Mean Carbon Density: <b>{res['mean_carbon_density_tC_per_ha']:.1f} t C/ha</b> (Forest Area: <b>{res['forest_area_ha']:.1f} ha</b>)")
    val = res.get("estimated_economic_value_usd", res.get("total_economic_value_usd", 0.0))
    dialog.log(f"• Estimated Carbon Credit Value: <b>${val:,.2f} USD</b> (@ ${c_price:.2f}/t CO₂e)")
    dialog.log(f"• Carbon Audit Report: <a href='file:///{res['report_path']}'>{os.path.basename(res['report_path'])}</a>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        if is_chm:
            r_layer = QgsRasterLayer(out_path, f"{os.path.splitext(os.path.basename(in_path))[0]}_agb_carbon", "gdal")
            if r_layer.isValid():
                QgsProject.instance().addMapLayer(r_layer)
                dialog.log(f"Added AGB & Carbon raster to map canvas: <b>{r_layer.name()}</b>")
        else:
            v_layer = QgsVectorLayer(out_path, f"{os.path.splitext(os.path.basename(in_path))[0]}_tree_carbon", "ogr")
            if v_layer.isValid():
                QgsProject.instance().addMapLayer(v_layer)
                dialog.log(f"Added Tree Carbon vector to map canvas: <b>{v_layer.name()}</b>")


def run_lidar_powerlines(dialog):
    """Executes powerline wire conductor (14) and transmission tower (15) classification."""
    from core.lidar.powerline_classifier import PowerlineClassifier

    las_data = dialog.las_combo.currentData() if hasattr(dialog, "las_combo") else None
    las_path = None
    if las_data:
        if isinstance(las_data, str) and os.path.exists(las_data):
            las_path = las_data
        else:
            lyr = QgsProject.instance().mapLayer(str(las_data))
            if lyr:
                las_path = lyr.customProperty("original_las_path") or lyr.customProperty("copc_path") or lyr.source()
    if not las_path or not os.path.exists(las_path):
        txt = dialog.las_combo.currentText().replace("🏛 ", "").replace("☁️ ", "").replace("☁ ", "").strip()
        if os.path.exists(txt):
            las_path = txt
        else:
            for l in QgsProject.instance().mapLayers().values():
                if l.name().strip() == txt or txt in l.name():
                    las_path = l.customProperty("original_las_path") or l.customProperty("copc_path") or l.source()
                    if las_path and os.path.exists(las_path):
                        break
    if not las_path or not os.path.exists(las_path):
        raise ValueError("Please select an input LiDAR point cloud file (LAS/LAZ).")

    min_w = dialog.min_wire_h_spin.value() if hasattr(dialog, "min_wire_h_spin") else 4.0
    max_w = dialog.max_wire_h_spin.value() if hasattr(dialog, "max_wire_h_spin") else 65.0
    lin_th = dialog.linearity_spin.value() if hasattr(dialog, "linearity_spin") else 0.70
    min_span_len = dialog.min_span_len_spin.value() if hasattr(dialog, "min_span_len_spin") else 20.0
    min_tow = dialog.min_tower_h_spin.value() if hasattr(dialog, "min_tower_h_spin") else 12.0
    exclude_veg = dialog.cb_exclude_veg.isChecked() if hasattr(dialog, "cb_exclude_veg") else True
    req_wire_conn = dialog.cb_require_tower_wire.isChecked() if hasattr(dialog, "cb_require_tower_wire") else True
    exp_vec = dialog.cb_export_vectors.isChecked() if hasattr(dialog, "cb_export_vectors") else True

    out_las = dialog.output_edit.text().strip()
    if not out_las or out_las == "[Create temporary layer]" or not (out_las.lower().endswith(".las") or out_las.lower().endswith(".laz")):
        base_dir = os.path.dirname(las_path) or tempfile.gettempdir()
        out_las = os.path.join(base_dir, f"{os.path.splitext(os.path.basename(las_path))[0]}_powerlines_classified.laz")

    dialog.log(f"Classifying Powerlines & Transmission Towers in: <b>{os.path.basename(las_path)}</b>...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = PowerlineClassifier.classify_corridor(
        input_las_path=las_path,
        output_las_path=out_las,
        min_wire_height_m=min_w,
        max_wire_height_m=max_w,
        min_linearity=lin_th,
        min_span_length_m=min_span_len,
        min_tower_height_m=min_tow,
        exclude_vegetation_classes=exclude_veg,
        require_tower_wire_connection=req_wire_conn,
        export_vectors=exp_vec,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Utility Classification Summary:</b>")
    dialog.log(f"• Classified Wire Points (ASPRS 14): <b>{res['wire_points_class_14']:,} points</b>")
    dialog.log(f"• Classified Tower Points (ASPRS 15): <b>{res['tower_points_class_15']:,} points</b>")
    dialog.log(f"• Conductor Wire Spans: <b>{res['conductor_spans_count']}</b> (Total Length: <b>{res['total_conductor_length_m']:.1f} m</b>)")
    dialog.log(f"• Transmission Towers / Pylons: <b>{res['transmission_towers_count']}</b> (Max Height: <b>{res['max_tower_height_m']:.1f} m</b>)")

    if dialog.open_output_cb.isChecked():
        if res.get("conductors_vector") and os.path.exists(res["conductors_vector"]):
            v_cond = QgsVectorLayer(res["conductors_vector"], "conductor_wires_3d", "ogr")
            if v_cond.isValid():
                QgsProject.instance().addMapLayer(v_cond)
                dialog.log(f"Added 3D Conductor Wires layer: <b>{v_cond.name()}</b>")
        if res.get("towers_vector") and os.path.exists(res["towers_vector"]):
            v_tow = QgsVectorLayer(res["towers_vector"], "transmission_towers", "ogr")
            if v_tow.isValid():
                QgsProject.instance().addMapLayer(v_tow)
                dialog.log(f"Added Transmission Towers layer: <b>{v_tow.name()}</b>")


def run_vegetation_clearance(dialog):
    """Executes 3D vegetation clearance and danger tree buffer analysis."""
    from core.lidar.vegetation_clearance_engine import VegetationClearanceEngine

    # Wire source
    w_data = dialog.wire_combo.currentData() if hasattr(dialog, "wire_combo") else None
    if not w_data:
        w_txt = dialog.wire_combo.currentText().replace("⚡ ", "").strip()
        if os.path.exists(w_txt):
            wire_src = w_txt
        else:
            raise ValueError("Please select a valid Powerline Conductors vector layer or LAS file.")
    else:
        lyr = QgsProject.instance().mapLayer(str(w_data))
        wire_src = lyr.source() if lyr else str(w_data)

    # Veg source
    v_data = dialog.veg_combo.currentData() if hasattr(dialog, "veg_combo") else None
    if not v_data:
        v_txt = dialog.veg_combo.currentText().replace("🌲 ", "").strip()
        if os.path.exists(v_txt):
            veg_src = v_txt
        else:
            raise ValueError("Please select a valid Trees / Canopy Vegetation layer or CHM.")
    else:
        lyr = QgsProject.instance().mapLayer(str(v_data))
        veg_src = lyr.source() if lyr else str(v_data)

    crit_d = dialog.crit_dist_spin.value() if hasattr(dialog, "crit_dist_spin") else 3.0
    warn_d = dialog.warn_dist_spin.value() if hasattr(dialog, "warn_dist_spin") else 5.0
    adv_d = dialog.advisory_dist_spin.value() if hasattr(dialog, "advisory_dist_spin") else 8.0
    fall_b = dialog.fall_buf_spin.value() if hasattr(dialog, "fall_buf_spin") else 1.5
    gen_buf = dialog.cb_corridor_buffers.isChecked() if hasattr(dialog, "cb_corridor_buffers") else True

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        out_path = tempfile.mktemp(suffix=".gpkg")

    dialog.log(f"Executing Vegetation Clearance & Danger Tree Risk Analysis...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = VegetationClearanceEngine.analyze_corridor(
        conductors_source=wire_src,
        vegetation_source=veg_src,
        output_vector_path=out_path,
        critical_dist_m=crit_d,
        warning_dist_m=warn_d,
        advisory_dist_m=adv_d,
        fall_buffer_m=fall_b,
        generate_corridor_buffers=gen_buf,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Vegetation Corridor Risk Audit:</b>")
    dialog.log(f"• Total Trees Evaluated: <b>{res['total_trees_inspected']:,}</b>")
    dialog.log(f"• <span style='color:#dc2626;'>Critical Encroachments (&lt;{crit_d}m): <b>{res['critical_encroachments_count']}</b></span>")
    dialog.log(f"• <span style='color:#f97316;'>Warning Encroachments (&lt;{warn_d}m): <b>{res['warning_encroachments_count']}</b></span>")
    dialog.log(f"• <span style='color:#dc2626;'>Fall-In Danger Trees (Striking Hazard): <b>{res['total_danger_trees_count']}</b></span>")
    dialog.log(f"• Emergency Pruning Work Orders: <b>{res['emergency_prune_required']}</b>")
    dialog.log(f"• Hazard Tree Removals: <b>{res['tree_removal_required']}</b>")
    dialog.log(f"• Audit Report: <a href='file:///{res['report_path']}'>{os.path.basename(res['report_path'])}</a>")

    if dialog.open_output_cb.isChecked():
        if os.path.exists(out_path):
            v_dt = QgsVectorLayer(out_path, "danger_trees_hazard", "ogr")
            if v_dt.isValid():
                QgsProject.instance().addMapLayer(v_dt)
                dialog.log(f"Added Danger Trees Hazard layer: <b>{v_dt.name()}</b>")
        if res.get("buffer_vector") and os.path.exists(res["buffer_vector"]):
            v_buf = QgsVectorLayer(res["buffer_vector"], "corridor_hazard_buffers", "ogr")
            if v_buf.isValid():
                QgsProject.instance().addMapLayer(v_buf)
                dialog.log(f"Added Corridor Hazard Buffers: <b>{v_buf.name()}</b>")


def run_building_roofs(dialog):
    """Executes building planar roof facet segmentation and solar PV potential rating."""
    from core.lidar.building_roof_engine import BuildingRoofEngine

    las_data = dialog.las_combo.currentData() if hasattr(dialog, "las_combo") else None
    las_path = None
    if las_data:
        if isinstance(las_data, str) and os.path.exists(las_data):
            las_path = las_data
        else:
            lyr = QgsProject.instance().mapLayer(str(las_data))
            if lyr:
                las_path = lyr.customProperty("original_las_path") or lyr.customProperty("copc_path") or lyr.source()
    if not las_path or not os.path.exists(las_path):
        txt = dialog.las_combo.currentText().replace("🏛 ", "").replace("☁️ ", "").replace("☁ ", "").strip()
        if os.path.exists(txt):
            las_path = txt
        else:
            for l in QgsProject.instance().mapLayers().values():
                if l.name().strip() == txt or txt in l.name():
                    las_path = l.customProperty("original_las_path") or l.customProperty("copc_path") or l.source()
                    if las_path and os.path.exists(las_path):
                        break
    if not las_path or not os.path.exists(las_path):
        raise ValueError("Please select an input LiDAR point cloud file (LAS/LAZ).")

    dist_th = dialog.dist_thresh_spin.value() if hasattr(dialog, "dist_thresh_spin") else 0.20
    ang_dev = dialog.angle_dev_spin.value() if hasattr(dialog, "angle_dev_spin") else 15.0
    min_area = dialog.min_facet_area_spin.value() if hasattr(dialog, "min_facet_area_spin") else 4.0
    min_bldg_h = dialog.min_bldg_h_spin.value() if hasattr(dialog, "min_bldg_h_spin") else 2.20

    target_class = 6
    if hasattr(dialog, "bldg_class_combo") and dialog.bldg_class_combo.currentIndex() == 1:
        target_class = -1 # elevated non-ground

    out_path = dialog.output_edit.text().strip()
    if not out_path or out_path == "[Create temporary layer]":
        base_dir = os.path.dirname(las_path) or tempfile.gettempdir()
        out_path = os.path.join(base_dir, f"{os.path.splitext(os.path.basename(las_path))[0]}_roof_facets.gpkg")

    dialog.log(f"Extracting planar roof facets from: <b>{os.path.basename(las_path)}</b>...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)

    res = BuildingRoofEngine.extract_roof_facets(
        input_las_path=las_path,
        output_vector_path=out_path,
        min_facet_area_m2=min_area,
        distance_threshold_m=dist_th,
        max_angle_dev_deg=ang_dev,
        min_building_height_m=min_bldg_h,
        target_class=target_class,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Building Roof & Solar Potential Summary:</b>")
    dialog.log(f"• Extracted Planar Roof Facets: <b>{res['extracted_facets_count']} planes</b>")
    dialog.log(f"• Total 3D Roof Surface Area: <b>{res['total_roof_3d_area_m2']:,.1f} m²</b>")
    dialog.log(f"• Total Building Footprint Area: <b>{res['total_roof_footprint_m2']:,.1f} m²</b>")
    dialog.log(f"• Solar PV Optimal / Viable Area: <b>{res['optimal_pv_solar_area_m2']:,.1f} m²</b> ({res['solar_viable_area_pct']}% of total roof area)")
    dialog.log(f"• Mean Roof Pitch / Slope: <b>{res['mean_roof_pitch_deg']:.1f}°</b>")
    dialog.log(f"• Roof Analytics Report: <a href='file:///{res['report_path']}'>{os.path.basename(res['report_path'])}</a>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_path):
        v_roof = QgsVectorLayer(out_path, "building_roof_facets", "ogr")
        if v_roof.isValid():
            QgsProject.instance().addMapLayer(v_roof)
            dialog.log(f"Added Building Roof Facets layer: <b>{v_roof.name()}</b>")


def run_lidar_road_surface(dialog):
    """Executes road surface and pavement point cloud classification (ASPRS Class 11)."""
    from core.roads.road_extraction_engine import RoadExtractionEngine

    las_data = dialog.las_combo.currentData() if hasattr(dialog, "las_combo") else None
    las_path = None
    if las_data:
        if isinstance(las_data, str) and os.path.exists(las_data):
            las_path = las_data
        else:
            lyr = QgsProject.instance().mapLayer(str(las_data))
            if lyr:
                las_path = lyr.customProperty("original_las_path") or lyr.customProperty("copc_path") or lyr.source()
    if not las_path or not os.path.exists(las_path):
        txt = dialog.las_combo.currentText().replace("🛣️ ", "").replace("☁️ ", "").replace("☁ ", "").strip()
        if os.path.exists(txt):
            las_path = txt
        else:
            for l in QgsProject.instance().mapLayers().values():
                if l.name().strip() == txt or txt in l.name():
                    las_path = l.customProperty("original_las_path") or l.customProperty("copc_path") or l.source()
                    if las_path and os.path.exists(las_path):
                        break
    if not las_path or not os.path.exists(las_path):
        raise ValueError("Please select an input LiDAR point cloud file (LAS/LAZ).")

    ref_cl = None
    if hasattr(dialog, "ref_centerline_combo"):
        data = dialog.ref_centerline_combo.currentData()
        if data and os.path.exists(data):
            ref_cl = data

    max_w = dialog.max_corridor_width_spin.value() if hasattr(dialog, "max_corridor_width_spin") else 12.0
    max_hag = dialog.max_hag_spin.value() if hasattr(dialog, "max_hag_spin") else 0.35
    min_plan = dialog.min_planarity_spin.value() if hasattr(dialog, "min_planarity_spin") else 0.65
    max_rough = dialog.max_roughness_spin.value() if hasattr(dialog, "max_roughness_spin") else 0.08
    min_vert = dialog.min_vert_spin.value() if hasattr(dialog, "min_vert_spin") else 0.85
    min_area = dialog.min_road_area_spin.value() if hasattr(dialog, "min_road_area_spin") else 20.0
    exp_vec = dialog.cb_export_corridor_vec.isChecked() if hasattr(dialog, "cb_export_corridor_vec") else True

    out_las = dialog.output_edit.text().strip()
    if not out_las or out_las == "[Create temporary layer]" or not (out_las.lower().endswith(".las") or out_las.lower().endswith(".laz")):
        base_dir = os.path.dirname(las_path) or tempfile.gettempdir()
        out_las = os.path.join(base_dir, f"{os.path.splitext(os.path.basename(las_path))[0]}_roads_classified.laz")

    dialog.log(f"Classifying Road Surface & Pavement in: <b>{os.path.basename(las_path)}</b>...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)
        app = QApplication.instance()
        if app:
            app.processEvents()

    res = RoadExtractionEngine.classify_road_surface(
        input_las_path=las_path,
        output_las_path=out_las,
        road_centerline_vector=ref_cl,
        max_corridor_width_m=max_w,
        max_hag_m=max_hag,
        min_planarity=min_plan,
        max_roughness_m=max_rough,
        min_verticality=min_vert,
        min_corridor_area_m2=min_area,
        export_footprint_polygon=exp_vec,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Road Surface Classification Summary:</b>")
    dialog.log(f"• Total Points Evaluated: <b>{res['total_points']:,}</b>")
    dialog.log(f"• Classified Road Surface Points (ASPRS 11): <b>{res['road_points_class_11']:,}</b> ({res['road_points_pct']}%)")
    dialog.log(f"• Estimated Road Pavement Area: <b>{res['estimated_pavement_area_m2']:,.1f} m²</b>")
    dialog.log(f"• Output Point Cloud: <code>{res['output_las_path']}</code>")

    if dialog.open_output_cb.isChecked() and res.get("footprint_vector") and os.path.exists(res["footprint_vector"]):
        gpkg_path = res["footprint_vector"]
        v_poly = QgsVectorLayer(f"{gpkg_path}|layername=road_corridor_boundary", "road_corridor_boundary", "ogr")
        if not v_poly.isValid():
            v_poly = QgsVectorLayer(gpkg_path, "road_corridor_boundary", "ogr")
        if v_poly.isValid():
            try:
                from qgis.core import QgsFillSymbol
                sym = QgsFillSymbol.createSimple({
                    "color": "255,160,20,70",
                    "outline_color": "230,60,0,255",
                    "outline_width": "0.6"
                })
                v_poly.renderer().setSymbol(sym)
                v_poly.triggerRepaint()
            except Exception:
                pass
            QgsProject.instance().addMapLayer(v_poly)
            dialog.log(f"Added Road Corridor Boundary layer: <b>{v_poly.name()}</b>")

        # Also load 3D road centerlines if present
        v_line = QgsVectorLayer(f"{gpkg_path}|layername=road_centerline_3d", "road_centerline_3d", "ogr")
        if v_line.isValid() and v_line.featureCount() > 0:
            try:
                from qgis.core import QgsLineSymbol
                sym_line = QgsLineSymbol.createSimple({
                    "line_color": "255,235,50,255",
                    "line_width": "0.8",
                    "line_style": "solid"
                })
                v_line.renderer().setSymbol(sym_line)
                v_line.triggerRepaint()
            except Exception:
                pass
            QgsProject.instance().addMapLayer(v_line)
            dialog.log(f"Added Road Centerlines 3D layer: <b>{v_line.name()}</b> ({v_line.featureCount()} lines)")


def run_lidar_road_corridor(dialog):
    """Executes 3D road centerline, curb line, and chainage station extraction."""
    from core.roads.road_extraction_engine import RoadExtractionEngine

    r_data = dialog.road_combo.currentData() if hasattr(dialog, "road_combo") else None
    road_src = None
    if r_data:
        if isinstance(r_data, str) and os.path.exists(r_data):
            road_src = r_data
        else:
            lyr = QgsProject.instance().mapLayer(str(r_data))
            if lyr:
                road_src = lyr.customProperty("original_las_path") or lyr.customProperty("copc_path") or lyr.source()
    if not road_src or not os.path.exists(road_src):
        txt = dialog.road_combo.currentText().replace("🛣️ ", "").replace("☁️ ", "").replace("☁ ", "").strip()
        if os.path.exists(txt):
            road_src = txt
        else:
            for l in QgsProject.instance().mapLayers().values():
                if l.name().strip() == txt or txt in l.name():
                    road_src = l.customProperty("original_las_path") or l.customProperty("copc_path") or l.source()
                    if road_src and os.path.exists(road_src):
                        break
    if not road_src or not os.path.exists(road_src):
        raise ValueError("Please select an input road point cloud or vector layer.")

    st_int = dialog.station_interval_spin.value() if hasattr(dialog, "station_interval_spin") else 25.0
    c_step = dialog.corridor_step_spin.value() if hasattr(dialog, "corridor_step_spin") else 5.0
    det_curb = dialog.cb_detect_curbs.isChecked() if hasattr(dialog, "cb_detect_curbs") else True

    out_vec = dialog.output_edit.text().strip()
    if not out_vec or out_vec == "[Create temporary layer]":
        base_dir = os.path.dirname(road_src) or tempfile.gettempdir()
        out_vec = os.path.join(base_dir, f"{os.path.splitext(os.path.basename(road_src))[0]}_corridor_alignment.gpkg")

    dialog.log(f"Extracting Road Centerline & Corridor Alignments from: <b>{os.path.basename(road_src)}</b>...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)
        app = QApplication.instance()
        if app:
            app.processEvents()

    res = RoadExtractionEngine.extract_road_corridor(
        input_source=road_src,
        output_vector_path=out_vec,
        station_interval_m=st_int,
        corridor_search_step_m=c_step,
        detect_curbs=det_curb,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Road Alignment Geometry Summary:</b>")
    dialog.log(f"• Centerline Length: <b>{res['centerline_length_m']:,.1f} m</b>")
    dialog.log(f"• Average Road Width: <b>{res['average_road_width_m']:.1f} m</b>")
    dialog.log(f"• Maximum Longitudinal Grade: <b>{res['max_longitudinal_grade_pct']:.1f}%</b>")
    dialog.log(f"• Chainage Station Markers: <b>{res['station_markers_count']} points</b> (Every {st_int:.0f}m)")
    dialog.log(f"• Curb / Edge Lines Extracted: <b>{res['curb_lines_count']} lines</b>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_vec):
        v_cl = QgsVectorLayer(f"{out_vec}|layername=road_centerline_3d", "road_centerline_3d", "ogr")
        if v_cl.isValid():
            QgsProject.instance().addMapLayer(v_cl)
            dialog.log(f"Added Road Centerline 3D layer: <b>{v_cl.name()}</b>")

        if det_curb:
            v_curb = QgsVectorLayer(f"{out_vec}|layername=road_curbs_3d", "road_curbs_3d", "ogr")
            if v_curb.isValid():
                QgsProject.instance().addMapLayer(v_curb)
                dialog.log(f"Added Road Curbs 3D layer: <b>{v_curb.name()}</b>")

        v_st = QgsVectorLayer(f"{out_vec}|layername=road_stations_3d", "road_stations_3d", "ogr")
        if v_st.isValid():
            QgsProject.instance().addMapLayer(v_st)
            dialog.log(f"Added Road Stations 3D layer: <b>{v_st.name()}</b>")


def run_lidar_road_condition(dialog):
    """Executes road longitudinal grade, surface roughness, and overhead vehicle clearance analysis."""
    from core.roads.road_extraction_engine import RoadExtractionEngine

    # Road Centerline source
    r_data = dialog.road_combo.currentData() if hasattr(dialog, "road_combo") else None
    road_src = None
    if r_data:
        if isinstance(r_data, str) and os.path.exists(r_data):
            road_src = r_data
        else:
            lyr = QgsProject.instance().mapLayer(str(r_data))
            if lyr:
                road_src = lyr.source()
    if not road_src or not os.path.exists(road_src):
        txt = dialog.road_combo.currentText().replace("🛣️ ", "").replace("☁️ ", "").replace("☁ ", "").strip()
        if os.path.exists(txt):
            road_src = txt
        else:
            for l in QgsProject.instance().mapLayers().values():
                if l.name().strip() == txt or txt in l.name():
                    road_src = l.source()
                    if road_src and os.path.exists(road_src):
                        break
    if not road_src or not os.path.exists(road_src):
        raise ValueError("Please select a road centerline vector layer.")

    # LiDAR source
    l_data = dialog.las_combo.currentData() if hasattr(dialog, "las_combo") else None
    las_src = None
    if l_data:
        if isinstance(l_data, str) and os.path.exists(l_data):
            las_src = l_data
        else:
            lyr = QgsProject.instance().mapLayer(str(l_data))
            if lyr:
                las_src = lyr.customProperty("original_las_path") or lyr.customProperty("copc_path") or lyr.source()
    if not las_src or not os.path.exists(las_src):
        txt = dialog.las_combo.currentText().replace("☁️ ", "").replace("☁ ", "").strip()
        if os.path.exists(txt):
            las_src = txt
        else:
            for l in QgsProject.instance().mapLayers().values():
                if l.name().strip() == txt or txt in l.name():
                    las_src = l.customProperty("original_las_path") or l.customProperty("copc_path") or l.source()
                    if las_src and os.path.exists(las_src):
                        break
    if not las_src or not os.path.exists(las_src):
        raise ValueError("Please select a full corridor LiDAR point cloud file (LAS/LAZ).")

    corr_w = dialog.corridor_width_spin.value() if hasattr(dialog, "corridor_width_spin") else 8.0
    clr_h = dialog.clearance_height_spin.value() if hasattr(dialog, "clearance_height_spin") else 4.80
    crit_clr = dialog.crit_clearance_spin.value() if hasattr(dialog, "crit_clearance_spin") else 4.00
    max_g = dialog.max_grade_spin.value() if hasattr(dialog, "max_grade_spin") else 8.0
    crit_g = dialog.crit_grade_spin.value() if hasattr(dialog, "crit_grade_spin") else 12.0

    out_vec = dialog.output_edit.text().strip()
    if not out_vec or out_vec == "[Create temporary layer]":
        base_dir = os.path.dirname(las_src) or tempfile.gettempdir()
        out_vec = os.path.join(base_dir, f"{os.path.splitext(os.path.basename(las_src))[0]}_road_hazards.gpkg")

    dialog.log(f"Auditing Road Condition & Overhead Vehicle Clearance Envelope...")

    def _progress(pct, msg):
        dialog.progress_bar.setValue(int(pct))
        dialog.progress_bar.setFormat(msg)
        app = QApplication.instance()
        if app:
            app.processEvents()

    res = RoadExtractionEngine.analyze_road_condition(
        road_centerline_source=road_src,
        lidar_source=las_src,
        output_vector_path=out_vec,
        max_design_grade_pct=max_g,
        critical_grade_pct=crit_g,
        vehicle_clearance_height_m=clr_h,
        critical_clearance_height_m=crit_clr,
        corridor_width_m=corr_w,
        progress_callback=_progress,
        log_callback=dialog.log
    )

    dialog.log(f"\n<b>Road Corridor Condition & Safety Audit:</b>")
    dialog.log(f"• Total Corridor Length: <b>{res['total_corridor_length_m']:,.1f} m</b>")
    dialog.log(f"• Maximum Longitudinal Slope: <b>{res['max_grade_pct']:.1f}%</b>")
    dialog.log(f"• Steep Grade Violations: <b>{res['steep_grade_count']} warnings</b> | <span style='color:#dc2626;'><b>{res['critical_grade_count']} critical (> {crit_g:.1f}%)</b></span>")
    dialog.log(f"• Pavement Roughness (IRI Proxy): <b>{res['iri_proxy_m_km']:.2f} m/km</b>")
    dialog.log(f"• Surface Depressions / Potholes: <b>{res['potholes_count']}</b>")
    dialog.log(f"• <span style='color:#dc2626;'>Critical Overhead Collision Strikes (&lt; {crit_clr:.1f}m): <b>{res['critical_clearance_count']}</b></span>")
    dialog.log(f"• <span style='color:#f97316;'>Overhead Encroachments (&lt; {clr_h:.1f}m): <b>{res['warning_clearance_count']}</b></span>")
    dialog.log(f"• Detailed Audit Report: <a href='file:///{res['report_path']}'>{os.path.basename(res['report_path'])}</a>")

    if dialog.open_output_cb.isChecked() and os.path.exists(out_vec):
        v_haz = QgsVectorLayer(out_vec, "road_hazards_audit", "ogr")
        if v_haz.isValid():
            QgsProject.instance().addMapLayer(v_haz)
            dialog.log(f"Added Road Hazards Audit layer: <b>{v_haz.name()}</b>")




