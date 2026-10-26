# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - Vector Geoprocessing Tasks
Executes Shapely & OGR vector geometric operations:
buffer, convex hull, centroids, dissolve, Voronoi/Thiessen diagrams, vector clipping,
and launches the standalone PyQt Transpose Fields dialog.
"""

import os
import sys
import json

from common import report_progress, report_result


def task_transpose_fields(args):
    """Launches standalone Transpose / Pivot Fields tool dialog."""
    report_progress(10, "Initializing Transpose Fields tool...")
    from PyQt5.QtWidgets import QApplication
    from ui.dialogs.transpose_fields_dialog import TransposeFieldsDialog

    app = QApplication.instance() or QApplication([sys.argv[0]])
    dlg = TransposeFieldsDialog()
    dlg.show()
    report_progress(100, "Transpose Fields tool active")
    app.exec_()


def task_vector_geoprocessing(args):
    """High-throughput vector geoprocessing via Shapely & OGR:
    buffer, convex_hull, centroids, dissolve, voronoi, clip.
    """
    mode = (args.mode or "buffer").lower()
    report_progress(10, f"Initializing Vector {mode.capitalize()}...")
    from osgeo import ogr, osr
    import shapely
    import shapely.geometry
    import shapely.ops
    ogr.UseExceptions()

    in_file = args.input
    if not in_file or not os.path.exists(in_file):
        raise ValueError(f"Input vector file not found: {in_file}")

    out_file = args.output
    if not out_file:
        base, ext = os.path.splitext(in_file)
        out_file = f"{base}_{mode}.geojson"

    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)

    in_ds = ogr.Open(in_file)
    in_layer = in_ds.GetLayer(0)
    in_srs = in_layer.GetSpatialRef()
    is_geographic = in_srs.IsGeographic() if in_srs else False

    features_data = []
    geometries = []

    report_progress(20, "Reading vector geometries...")
    for feat in in_layer:
        geom_ref = feat.GetGeometryRef()
        if not geom_ref:
            continue
        geom_json = json.loads(geom_ref.ExportToJson())
        shp_geom = shapely.geometry.shape(geom_json)
        if not shp_geom.is_valid:
            shp_geom = shp_geom.buffer(0)

        props = {}
        for i in range(feat.GetFieldCount()):
            fld_defn = feat.GetFieldDefnRef(i)
            props[fld_defn.GetName()] = feat.GetField(i)

        features_data.append((shp_geom, props))
        geometries.append(shp_geom)

    out_features = []
    report_progress(40, f"Executing {mode} algorithm...")

    if mode == "buffer":
        dist = float(args.param1 or 100.0)
        segments = 16
        dissolve = False
        if args.param2:
            try:
                opts = json.loads(args.param2) if args.param2.startswith("{") else {}
                segments = int(opts.get("segments", 16))
                dissolve = bool(opts.get("dissolve", False))
            except Exception:
                pass

        effective_dist = dist
        if is_geographic and dist > 0.05:
            effective_dist = dist / 111320.0

        buffered_geoms = []
        for i, (geom, props) in enumerate(features_data):
            b_geom = geom.buffer(effective_dist, quad_segs=segments)
            buffered_geoms.append(b_geom)
            if not dissolve:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(b_geom),
                    "properties": dict(props, buffer_distance=dist)
                })

        if dissolve and buffered_geoms:
            dissolved = shapely.ops.unary_union(buffered_geoms)
            if dissolved.geom_type == "Polygon":
                dissolved_list = [dissolved]
            elif dissolved.geom_type == "MultiPolygon":
                dissolved_list = list(dissolved.geoms)
            else:
                dissolved_list = [dissolved]
            for poly in dissolved_list:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(poly),
                    "properties": {"buffer_distance": dist, "dissolved": True}
                })

    elif mode == "convex_hull":
        target = (args.param1 or "all").lower()
        if target == "per_feature":
            for geom, props in features_data:
                hull = geom.convex_hull
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(hull),
                    "properties": dict(props, is_convex_hull=True)
                })
        else:
            union_all = shapely.ops.unary_union(geometries)
            hull = union_all.convex_hull
            out_features.append({
                "type": "Feature",
                "geometry": shapely.geometry.mapping(hull),
                "properties": {"name": "Convex Hull", "feature_count": len(geometries)}
            })

    elif mode == "centroids":
        for geom, props in features_data:
            centroid = geom.centroid
            out_features.append({
                "type": "Feature",
                "geometry": shapely.geometry.mapping(centroid),
                "properties": dict(props, centroid_x=round(centroid.x, 6), centroid_y=round(centroid.y, 6))
            })

    elif mode == "dissolve":
        dissolve_field = args.param1.strip() if args.param1 else ""
        if dissolve_field and dissolve_field.lower() != "all":
            from collections import defaultdict
            groups = defaultdict(list)
            for geom, props in features_data:
                key = str(props.get(dissolve_field, "Unknown"))
                groups[key].append(geom)

            for key, group_geoms in groups.items():
                dissolved = shapely.ops.unary_union(group_geoms)
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(dissolved),
                    "properties": {dissolve_field: key, "dissolved_count": len(group_geoms)}
                })
        else:
            dissolved = shapely.ops.unary_union(geometries)
            if dissolved.geom_type in ("Polygon", "MultiPolygon", "MultiLineString"):
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(dissolved),
                    "properties": {"name": "Dissolved Layer", "feature_count": len(geometries)}
                })
            else:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(dissolved),
                    "properties": {"name": "Dissolved Layer"}
                })

    elif mode == "voronoi":
        all_pts = []
        for geom in geometries:
            if geom.geom_type == "Point":
                all_pts.append(geom)
            elif geom.geom_type == "MultiPoint":
                all_pts.extend(geom.geoms)
            elif hasattr(geom, 'coords'):
                for coord in geom.coords:
                    all_pts.append(shapely.geometry.Point(coord[0], coord[1]))
            elif hasattr(geom, 'exterior') and geom.exterior:
                for coord in geom.exterior.coords:
                    all_pts.append(shapely.geometry.Point(coord[0], coord[1]))

        if len(all_pts) < 3:
            raise ValueError("Voronoi requires at least 3 points to construct polygons.")

        mp = shapely.geometry.MultiPoint(all_pts)
        vor = shapely.ops.voronoi_diagram(mp)
        env = mp.envelope.buffer(0.05 if is_geographic else 200)
        for i, poly in enumerate(vor.geoms):
            clipped_cell = poly.intersection(env)
            if not clipped_cell.is_empty:
                out_features.append({
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(clipped_cell),
                    "properties": {"voronoi_id": i + 1}
                })

    elif mode == "clip":
        mask_file = args.param1
        if not mask_file or not os.path.exists(mask_file):
            raise ValueError(f"Clipping mask vector layer not found: {mask_file}")
        mask_ds = ogr.Open(mask_file)
        mask_layer = mask_ds.GetLayer(0)
        mask_geoms = []
        for feat in mask_layer:
            g_ref = feat.GetGeometryRef()
            if g_ref:
                m_shp = shapely.geometry.shape(json.loads(g_ref.ExportToJson()))
                if not m_shp.is_valid:
                    m_shp = m_shp.buffer(0)
                mask_geoms.append(m_shp)
        mask_union = shapely.ops.unary_union(mask_geoms)

        for geom, props in features_data:
            if geom.intersects(mask_union):
                clipped_geom = geom.intersection(mask_union)
                if not clipped_geom.is_empty:
                    out_features.append({
                        "type": "Feature",
                        "geometry": shapely.geometry.mapping(clipped_geom),
                        "properties": props
                    })

    else:
        raise ValueError(f"Unknown geoprocessing mode: {mode}")

    report_progress(85, "Writing output GeoJSON...")
    geojson_doc = {
        "type": "FeatureCollection",
        "name": os.path.splitext(os.path.basename(out_file))[0],
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84" if is_geographic else "EPSG:3857"}
        },
        "features": out_features
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2)

    report_progress(100, f"Completed {mode}: {len(out_features)} features created")
    report_result(True, {
        "output_file": out_file,
        "feature_count": len(out_features),
        "mode": mode
    })
