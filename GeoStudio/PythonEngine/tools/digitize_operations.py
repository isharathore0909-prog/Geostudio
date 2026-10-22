# -*- coding: utf-8 -*-
"""
GeoStudio - Vector Digitizing Geometric Operations & Snapping
Snapping algorithms, feature finding, vertex search, feature insertion, transformations, and scratch layer creation.
"""

import math
from qgis.core import (
    QgsProject, QgsMapLayer, QgsGeometry, QgsPointXY, QgsPoint,
    QgsRectangle, QgsFeature, QgsField, QgsVectorLayer,
    QgsCoordinateTransform, QgsSnappingConfig
)


def snap_point(canvas, pt: QgsPointXY, active_layer) -> QgsPointXY:
    """Snaps map coordinate to nearest vertex or segment if snapping is enabled."""
    cfg = QgsProject.instance().snappingConfig()
    if not cfg.enabled():
        return pt

    tol = canvas.mapUnitsPerPixel() * 15
    rect = QgsRectangle(pt.x() - tol, pt.y() - tol, pt.x() + tol, pt.y() + tol)

    layers_to_check = [active_layer] if active_layer else []
    for l in QgsProject.instance().mapLayers().values():
        if l.type() == QgsMapLayer.VectorLayer and l.isValid() and l not in layers_to_check:
            layers_to_check.append(l)

    best_pt = pt
    min_dist_sq = tol * tol

    for l in layers_to_check:
        for feat in l.getFeatures(rect):
            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue

            if cfg.typeFlag() & QgsSnappingConfig.VertexFlag:
                closest_pt, vidx, prev_idx, next_idx, dsq = geom.closestVertex(pt)
                if dsq < min_dist_sq:
                    min_dist_sq = dsq
                    best_pt = closest_pt

            if cfg.typeFlag() & QgsSnappingConfig.SegmentFlag and min_dist_sq == tol * tol:
                res, seg_pt, after_idx, left_of = geom.closestSegmentWithContext(pt)
                if res >= 0:
                    dsq = seg_pt.distanceSquared(pt)
                    if dsq < min_dist_sq:
                        min_dist_sq = dsq
                        best_pt = seg_pt

    return best_pt


def find_feature_at(canvas, layer, pt: QgsPointXY):
    tol = canvas.mapUnitsPerPixel() * 12
    rect = QgsRectangle(pt.x() - tol, pt.y() - tol, pt.x() + tol, pt.y() + tol)
    for feat in layer.getFeatures(rect):
        if feat.geometry() and feat.geometry().intersects(rect):
            return feat
    return None


def find_vertex_at(canvas, layer, pt: QgsPointXY):
    tol = canvas.mapUnitsPerPixel() * 12
    rect = QgsRectangle(pt.x() - tol, pt.y() - tol, pt.x() + tol, pt.y() + tol)
    tol_sq = tol * tol
    for feat in layer.getFeatures(rect):
        geom = feat.geometry()
        if not geom or geom.isEmpty():
            continue
        closest_pt, vidx, _, _, dsq = geom.closestVertex(pt)
        if dsq <= tol_sq:
            return feat, vidx, closest_pt
    return None, -1, None


def find_segment_at(canvas, layer, pt: QgsPointXY):
    tol = canvas.mapUnitsPerPixel() * 10
    rect = QgsRectangle(pt.x() - tol, pt.y() - tol, pt.x() + tol, pt.y() + tol)
    tol_sq = tol * tol
    for feat in layer.getFeatures(rect):
        geom = feat.geometry()
        if not geom or geom.isEmpty():
            continue
        res, seg_pt, after_idx, _ = geom.closestSegmentWithContext(pt)
        if res >= 0 and seg_pt.distanceSquared(pt) <= tol_sq:
            return feat, seg_pt, after_idx
    return None, None, -1


def create_scratch_vector_layer(canvas, tool_type: str):
    dest_crs = canvas.mapSettings().destinationCrs()
    crs_str = dest_crs.authid() if dest_crs.isValid() else "EPSG:4326"
    geom_type = "Polygon" if tool_type in ("polygon", "rotate") else ("LineString" if tool_type in ("line", "split") else "Point")
    layer_name = f"Digitized {geom_type}s"
    layer = QgsVectorLayer(f"{geom_type}?crs={crs_str}", layer_name, "memory")
    if layer.isValid():
        pr = layer.dataProvider()
        pr.addAttributes([QgsField("name")])
        layer.updateFields()
        layer.startEditing()
        QgsProject.instance().addMapLayer(layer)
        return layer
    return None


def insert_point_feature(canvas, layer, pt: QgsPointXY):
    feat = QgsFeature(layer.fields())
    dest_crs = canvas.mapSettings().destinationCrs()
    if dest_crs.isValid() and layer.crs().isValid() and dest_crs != layer.crs():
        tr = QgsCoordinateTransform(dest_crs, layer.crs(), QgsProject.instance())
        pt = tr.transform(pt)
    feat.setGeometry(QgsGeometry.fromPointXY(pt))
    if layer.addFeature(feat):
        layer.updateExtents()
        canvas.refresh()
        return feat.id()
    return None


def insert_line_feature(canvas, layer, pts: list):
    feat = QgsFeature(layer.fields())
    dest_crs = canvas.mapSettings().destinationCrs()
    target_pts = list(pts)
    if dest_crs.isValid() and layer.crs().isValid() and dest_crs != layer.crs():
        tr = QgsCoordinateTransform(dest_crs, layer.crs(), QgsProject.instance())
        target_pts = [tr.transform(p) for p in target_pts]
    feat.setGeometry(QgsGeometry.fromPolylineXY(target_pts))
    if layer.addFeature(feat):
        layer.updateExtents()
        canvas.refresh()
        return feat.id()
    return None


def insert_polygon_feature(canvas, layer, pts: list):
    feat = QgsFeature(layer.fields())
    dest_crs = canvas.mapSettings().destinationCrs()
    target_pts = list(pts)
    if dest_crs.isValid() and layer.crs().isValid() and dest_crs != layer.crs():
        tr = QgsCoordinateTransform(dest_crs, layer.crs(), QgsProject.instance())
        target_pts = [tr.transform(p) for p in target_pts]
    feat.setGeometry(QgsGeometry.fromPolygonXY([target_pts]))
    if layer.addFeature(feat):
        layer.updateExtents()
        canvas.refresh()
        return feat.id()
    return None


def execute_split_feature(canvas, layer, pts: list):
    dest_crs = canvas.mapSettings().destinationCrs()
    target_pts = list(pts)
    if dest_crs.isValid() and layer.crs().isValid() and dest_crs != layer.crs():
        tr = QgsCoordinateTransform(dest_crs, layer.crs(), QgsProject.instance())
        target_pts = [tr.transform(p) for p in target_pts]
    split_geom = [QgsPoint(p.x(), p.y()) for p in target_pts]
    res, new_geoms, topo_points = layer.splitFeatures(split_geom, 0)
    if res == 0 and new_geoms:
        layer.updateExtents()
        canvas.refresh()
        return len(new_geoms) + 1
    return 0


def calculate_rotation_geom(feature_geom: QgsGeometry, start_pt: QgsPointXY, curr_pt: QgsPointXY):
    """Compute rotated preview geometry and angle delta in degrees."""
    center = feature_geom.centroid().asPoint()
    a1 = math.atan2(start_pt.y() - center.y(), start_pt.x() - center.x())
    a2 = math.atan2(curr_pt.y() - center.y(), curr_pt.x() - center.x())
    diff_deg = math.degrees(a2 - a1)
    geom = QgsGeometry(feature_geom)
    geom.rotate(diff_deg, center)
    return geom, diff_deg
