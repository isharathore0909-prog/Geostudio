# -*- coding: utf-8 -*-
"""
GeoStudio - Forestry Vector I/O Module
Handles GIS vector serialization (GeoPackage & ESRI Shapefile) for tree points,
crown boundary polygons, and DBH inventory data.
"""

import os
from typing import List, Dict, Any
from osgeo import ogr, osr


def write_tree_points_vector(path: str, records: List[Dict[str, Any]], wkt: str) -> str:
    """Exports detected tree point markers (Tree_ID, Height_m, X, Y) to GPKG or SHP."""
    ext = os.path.splitext(path)[1].lower()
    driver_name = "GPKG" if ext == ".gpkg" else "ESRI Shapefile"
    driver = ogr.GetDriverByName(driver_name)
    if not driver:
        driver = ogr.GetDriverByName("ESRI Shapefile")
        path = os.path.splitext(path)[0] + ".shp"

    if os.path.exists(path):
        driver.DeleteDataSource(path)

    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    if wkt:
        srs.ImportFromWkt(wkt)
    lyr = ds.CreateLayer("detected_trees", srs, ogr.wkbPoint)

    lyr.CreateField(ogr.FieldDefn("Tree_ID", ogr.OFTInteger))
    lyr.CreateField(ogr.FieldDefn("Height_m", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("X", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("Y", ogr.OFTReal))

    for r in records:
        feat = ogr.Feature(lyr.GetLayerDefn())
        feat.SetField("Tree_ID", int(r["id"]))
        feat.SetField("Height_m", float(r.get("height", 0.0)))
        feat.SetField("X", float(r["x"]))
        feat.SetField("Y", float(r["y"]))

        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint_2D(float(r["x"]), float(r["y"]))
        feat.SetGeometry(pt)
        lyr.CreateFeature(feat)
        feat = None

    ds.FlushCache()
    ds = None
    return path


def write_crown_polygons_vector(path: str, polygons: List[Dict[str, Any]], wkt: str) -> str:
    """Exports crown boundary polygon geometries and dimensions to GPKG or SHP."""
    ext = os.path.splitext(path)[1].lower()
    driver_name = "GPKG" if ext == ".gpkg" else "ESRI Shapefile"
    driver = ogr.GetDriverByName(driver_name)
    if not driver:
        driver = ogr.GetDriverByName("ESRI Shapefile")
        path = os.path.splitext(path)[0] + ".shp"

    if os.path.exists(path):
        driver.DeleteDataSource(path)

    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    if wkt:
        srs.ImportFromWkt(wkt)
    lyr = ds.CreateLayer("crown_polygons", srs, ogr.wkbPolygon)

    lyr.CreateField(ogr.FieldDefn("Tree_ID", ogr.OFTInteger))
    lyr.CreateField(ogr.FieldDefn("Height_m", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("Crown_Diam_m", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("Crown_Area_m2", ogr.OFTReal))

    for cp in polygons:
        pts = cp.get("pts", [])
        if len(pts) < 4:
            continue

        ring = ogr.Geometry(ogr.wkbLinearRing)
        for x, y in pts:
            ring.AddPoint_2D(float(x), float(y))
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        feat = ogr.Feature(lyr.GetLayerDefn())
        feat.SetField("Tree_ID", int(cp["id"]))
        feat.SetField("Height_m", float(cp["height"]))
        feat.SetField("Crown_Diam_m", float(cp["crown_diam"]))
        feat.SetField("Crown_Area_m2", float(cp["crown_area"]))
        feat.SetGeometry(poly)
        lyr.CreateFeature(feat)
        feat = None

    ds.FlushCache()
    ds = None
    return path


def write_dbh_points_vector(path: str, records: List[Dict[str, Any]], wkt: str) -> str:
    """Exports DBH, Basal Area, and Biomass tree point layer to GPKG or SHP."""
    ext = os.path.splitext(path)[1].lower()
    driver_name = "GPKG" if ext == ".gpkg" else "ESRI Shapefile"
    driver = ogr.GetDriverByName(driver_name)
    if not driver:
        driver = ogr.GetDriverByName("ESRI Shapefile")
        path = os.path.splitext(path)[0] + ".shp"

    if os.path.exists(path):
        driver.DeleteDataSource(path)

    ds = driver.CreateDataSource(path)
    srs = osr.SpatialReference()
    if wkt:
        srs.ImportFromWkt(wkt)
    lyr = ds.CreateLayer("trees_with_dbh", srs, ogr.wkbPoint)

    lyr.CreateField(ogr.FieldDefn("Tree_ID", ogr.OFTInteger))
    lyr.CreateField(ogr.FieldDefn("Height_m", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("Crown_Diam_m", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("DBH_cm", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("BasalArea_m2", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("Biomass_kg", ogr.OFTReal))
    lyr.CreateField(ogr.FieldDefn("DBH_Source", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("DBH_Model", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("DBH_Confidence", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("Biomass_Model", ogr.OFTString))

    for r in records:
        feat = ogr.Feature(lyr.GetLayerDefn())
        feat.SetField("Tree_ID", int(r["id"]))
        feat.SetField("Height_m", float(r["height"]))
        feat.SetField("Crown_Diam_m", float(r["crown_diam"]))
        feat.SetField("DBH_cm", float(r["dbh_cm"]))
        feat.SetField("BasalArea_m2", float(r["basal_area"]))
        feat.SetField("Biomass_kg", float(r["biomass_kg"]))
        feat.SetField("DBH_Source", str(r.get("dbh_source", "Allometric Model")))
        feat.SetField("DBH_Model", str(r.get("dbh_model", "Calibrated Allometry")))
        feat.SetField("DBH_Confidence", str(r.get("dbh_confidence", "Estimated (Aerial CHM)")))
        feat.SetField("Biomass_Model", str(r.get("biomass_model", "Chave et al. (2014) Allometric AGB")))

        pt = ogr.Geometry(ogr.wkbPoint)
        pt.AddPoint_2D(float(r["x"]), float(r["y"]))
        feat.SetGeometry(pt)
        lyr.CreateFeature(feat)
        feat = None

    ds.FlushCache()
    ds = None
    return path

