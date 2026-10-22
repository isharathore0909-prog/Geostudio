# -*- coding: utf-8 -*-
"""
GeoStudio - Road & Transportation Vector I/O & Spatial Reference
Handles CRS preservation and GeoPackage / Shapefile serialization for road geometries:
- Road corridor boundary polygon
- Road centerline 3D
- Road curbs / edge lines 3D
- Station chainage 3D points
- Corridor hazard points
"""

import os
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
from scipy.spatial import ConvexHull
from osgeo import gdal, ogr, osr

from .road_models import StationMarker, CorridorHazard, CorridorGeometryResult


class RoadSpatialReference:
    """Extracts and harmonizes Spatial Reference Systems across point clouds and vector files."""

    @staticmethod
    def from_las(las) -> osr.SpatialReference:
        srs = osr.SpatialReference()
        try:
            if hasattr(las.header, "parse_crs"):
                crs = las.header.parse_crs()
                if crs:
                    srs.ImportFromWkt(crs.to_wkt())
        except Exception:
            pass
        return srs

    @staticmethod
    def from_vector(source_path: str) -> osr.SpatialReference:
        srs = osr.SpatialReference()
        try:
            ds = ogr.Open(source_path)
            if ds:
                lyr = ds.GetLayer(0)
                if lyr and lyr.GetSpatialRef():
                    srs = lyr.GetSpatialRef().Clone()
                ds = None
        except Exception:
            pass
        return srs

    @staticmethod
    def is_valid(srs: Optional[osr.SpatialReference]) -> bool:
        if srs is None:
            return False
        try:
            wkt = srs.ExportToWkt()
            return bool(wkt and wkt.strip())
        except Exception:
            return False


class RoadVectorWriter:
    """Writes OGR vector layers (curbs, centerlines, stations, boundaries, hazards)."""

    @staticmethod
    def _create_datasource(path: str) -> ogr.DataSource:
        driver = ogr.GetDriverByName("GPKG")
        if os.path.exists(path):
            driver.DeleteDataSource(path)
        return driver.CreateDataSource(path)

    @classmethod
    def write_pavement_boundary(
        cls,
        points: np.ndarray,
        out_path: str,
        srs: Optional[osr.SpatialReference] = None,
        road_grid: Optional[np.ndarray] = None,
        grid_meta: Optional[Dict[str, Any]] = None,
        centerlines: Optional[List[Dict[str, Any]]] = None
    ):
        """Writes contoured polygon boundaries and 3D centerlines of road pavement corridor ribbons."""
        ds = cls._create_datasource(out_path)
        target_srs = srs if RoadSpatialReference.is_valid(srs) else osr.SpatialReference()
        lyr = ds.CreateLayer("road_corridor_boundary", target_srs, ogr.wkbPolygon)

        lyr.CreateField(ogr.FieldDefn("Corridor_ID", ogr.OFTInteger))
        lyr.CreateField(ogr.FieldDefn("Area_m2", ogr.OFTReal))
        lyr.CreateField(ogr.FieldDefn("Min_Z_m", ogr.OFTReal))
        lyr.CreateField(ogr.FieldDefn("Max_Z_m", ogr.OFTReal))

        written = False

        # Option A: Direct polygonization from high-resolution road raster grid
        if road_grid is not None and grid_meta is not None and np.any(road_grid):
            try:
                x_min = float(grid_meta["x_min"])
                y_min = float(grid_meta["y_min"])
                res = float(grid_meta["res"])
                nx = int(grid_meta["nx"])
                ny = int(grid_meta["ny"])
                y_max = y_min + ny * res
                dtm = grid_meta.get("dtm")

                u8_grid = road_grid.astype(np.uint8)

                drv_mem = gdal.GetDriverByName("MEM")
                ds_mem = drv_mem.Create("", nx, ny, 1, gdal.GDT_Byte)
                ds_mem.SetGeoTransform([x_min, res, 0.0, y_max, 0.0, -res])
                band = ds_mem.GetRasterBand(1)
                band.WriteArray(u8_grid)

                drv_ogr = ogr.GetDriverByName("MEM")
                ds_poly = drv_ogr.CreateDataSource("")
                poly_lyr = ds_poly.CreateLayer("poly", target_srs, ogr.wkbPolygon)
                poly_fld = ogr.FieldDefn("val", ogr.OFTInteger)
                poly_lyr.CreateField(poly_fld)

                gdal.Polygonize(band, band, poly_lyr, 0, [])

                cid = 1
                for f in poly_lyr:
                    geom = f.GetGeometryRef()
                    if geom and geom.GetArea() >= 15.0:
                        feat = ogr.Feature(lyr.GetLayerDefn())
                        feat.SetField("Corridor_ID", cid)
                        feat.SetField("Area_m2", round(float(geom.GetArea()), 1))
                        if dtm is not None:
                            feat.SetField("Min_Z_m", round(float(np.nanmin(dtm)), 2))
                            feat.SetField("Max_Z_m", round(float(np.nanmax(dtm)), 2))
                        elif len(points) > 0:
                            feat.SetField("Min_Z_m", round(float(np.min(points[:, 2])), 2))
                            feat.SetField("Max_Z_m", round(float(np.max(points[:, 2])), 2))
                        feat.SetGeometry(geom.Clone())
                        lyr.CreateFeature(feat)
                        cid += 1
                        written = True
                ds_poly = None
                ds_mem = None
            except Exception as e:
                print(f"[RoadVectorWriter] Direct polygonize notice: {e}")

        # Option B: Polygonize from point cloud coordinates if direct grid not supplied
        if not written and len(points) >= 10:
            try:
                x_min, y_min = float(np.min(points[:, 0])), float(np.min(points[:, 1]))
                x_max, y_max = float(np.max(points[:, 0])), float(np.max(points[:, 1]))
                res = 2.0
                nx = max(1, int(np.ceil((x_max - x_min) / res)) + 1)
                ny = max(1, int(np.ceil((y_max - y_min) / res)) + 1)

                if nx > 4 and ny > 4 and len(points) >= 30:
                    gx = np.clip(((points[:, 0] - x_min) / res).astype(np.int32), 0, nx - 1)
                    gy = np.clip(((points[:, 1] - y_min) / res).astype(np.int32), 0, ny - 1)

                    grid = np.zeros((ny, nx), dtype=np.uint8)
                    grid[ny - 1 - gy, gx] = 1

                    from scipy import ndimage
                    grid = ndimage.binary_closing(grid, structure=np.ones((3, 3))).astype(np.uint8)

                    drv_mem = gdal.GetDriverByName("MEM")
                    ds_mem = drv_mem.Create("", nx, ny, 1, gdal.GDT_Byte)
                    ds_mem.SetGeoTransform([x_min, res, 0.0, y_max, 0.0, -res])
                    band = ds_mem.GetRasterBand(1)
                    band.WriteArray(grid)

                    drv_ogr = ogr.GetDriverByName("MEM")
                    ds_poly = drv_ogr.CreateDataSource("")
                    poly_lyr = ds_poly.CreateLayer("poly", target_srs, ogr.wkbPolygon)
                    poly_fld = ogr.FieldDefn("val", ogr.OFTInteger)
                    poly_lyr.CreateField(poly_fld)

                    gdal.Polygonize(band, band, poly_lyr, 0, [])

                    cid = 1
                    for f in poly_lyr:
                        geom = f.GetGeometryRef()
                        if geom and geom.GetArea() >= 20.0:
                            feat = ogr.Feature(lyr.GetLayerDefn())
                            feat.SetField("Corridor_ID", cid)
                            feat.SetField("Area_m2", round(float(geom.GetArea()), 1))
                            feat.SetField("Min_Z_m", round(float(np.min(points[:, 2])), 2))
                            feat.SetField("Max_Z_m", round(float(np.max(points[:, 2])), 2))
                            feat.SetGeometry(geom.Clone())
                            lyr.CreateFeature(feat)
                            cid += 1
                            written = True
                    ds_poly = None
                    ds_mem = None
            except Exception as e:
                print(f"[RoadVectorWriter] Polygonize notice: {e}")

        # Fallback for simple small corridors if polygonize yielded nothing
        if not written and len(points) >= 3:
            try:
                hull = ConvexHull(points[:, :2])
                hull_pts = points[hull.vertices, :2]
                ring = ogr.Geometry(ogr.wkbLinearRing)
                for pt in hull_pts:
                    ring.AddPoint_2D(float(pt[0]), float(pt[1]))
                ring.AddPoint_2D(float(hull_pts[0][0]), float(hull_pts[0][1]))
                poly = ogr.Geometry(ogr.wkbPolygon)
                poly.AddGeometry(ring)
                feat = ogr.Feature(lyr.GetLayerDefn())
                feat.SetField("Corridor_ID", 1)
                feat.SetField("Area_m2", float(poly.GetArea()))
                feat.SetField("Min_Z_m", float(np.min(points[:, 2])))
                feat.SetField("Max_Z_m", float(np.max(points[:, 2])))
                feat.SetGeometry(poly)
                lyr.CreateFeature(feat)
            except Exception as e:
                print(f"[RoadVectorWriter] Fallback hull notice: {e}")

        # 3. Write 3D Road Centerline LineStrings layer if centerlines are provided
        if centerlines and len(centerlines) > 0:
            lyr_cl = ds.CreateLayer("road_centerline_3d", target_srs, ogr.wkbLineString25D)
            lyr_cl.CreateField(ogr.FieldDefn("Line_ID", ogr.OFTInteger))
            lyr_cl.CreateField(ogr.FieldDefn("Length_m", ogr.OFTReal))
            lyr_cl.CreateField(ogr.FieldDefn("Avg_Width_m", ogr.OFTReal))
            lyr_cl.CreateField(ogr.FieldDefn("Start_Z_m", ogr.OFTReal))
            lyr_cl.CreateField(ogr.FieldDefn("End_Z_m", ogr.OFTReal))
            lyr_cl.CreateField(ogr.FieldDefn("Slope_%", ogr.OFTReal))

            for lid, linfo in enumerate(centerlines, 1):
                geom_l = ogr.Geometry(ogr.wkbLineString25D)
                for pt in linfo["coords"]:
                    geom_l.AddPoint(float(pt[0]), float(pt[1]), float(pt[2]))

                f_cl = ogr.Feature(lyr_cl.GetLayerDefn())
                f_cl.SetField("Line_ID", lid)
                f_cl.SetField("Length_m", float(linfo.get("length_m", round(geom_l.Length(), 1))))
                f_cl.SetField("Avg_Width_m", float(linfo.get("mean_width_m", 6.0)))
                f_cl.SetField("Start_Z_m", float(linfo.get("start_z_m", 0.0)))
                f_cl.SetField("End_Z_m", float(linfo.get("end_z_m", 0.0)))
                f_cl.SetField("Slope_%", float(linfo.get("slope_pct", 0.0)))
                f_cl.SetGeometry(geom_l)
                lyr_cl.CreateFeature(f_cl)
                f_cl = None

        ds.FlushCache()
        ds = None

    @classmethod
    def write_corridor_layers(
        cls,
        geom_res: CorridorGeometryResult,
        out_path: str,
        detect_curbs: bool = True,
        srs: Optional[osr.SpatialReference] = None
    ) -> int:
        """Serializes centerline, curb lines, and station chainage into GeoPackage."""
        ds = cls._create_datasource(out_path)
        target_srs = srs if RoadSpatialReference.is_valid(srs) else osr.SpatialReference()

        # 1. Road Centerline (3D LineString)
        lyr_cl = ds.CreateLayer("road_centerline_3d", target_srs, ogr.wkbLineString25D)
        lyr_cl.CreateField(ogr.FieldDefn("Road_ID", ogr.OFTInteger))
        lyr_cl.CreateField(ogr.FieldDefn("Length_m", ogr.OFTReal))
        lyr_cl.CreateField(ogr.FieldDefn("Avg_Width_m", ogr.OFTReal))
        lyr_cl.CreateField(ogr.FieldDefn("Min_Elev_m", ogr.OFTReal))
        lyr_cl.CreateField(ogr.FieldDefn("Max_Elev_m", ogr.OFTReal))
        lyr_cl.CreateField(ogr.FieldDefn("Max_Grade_%", ogr.OFTReal))

        geom_cl = ogr.Geometry(ogr.wkbLineString25D)
        for pt in geom_res.centerline_points:
            geom_cl.AddPoint(float(pt[0]), float(pt[1]), float(pt[2]))

        feat_cl = ogr.Feature(lyr_cl.GetLayerDefn())
        feat_cl.SetField("Road_ID", 1)
        feat_cl.SetField("Length_m", round(geom_res.total_length_m, 1))
        feat_cl.SetField("Avg_Width_m", round(geom_res.average_width_m, 1))
        feat_cl.SetField("Min_Elev_m", round(float(np.min(geom_res.centerline_points[:, 2])), 2))
        feat_cl.SetField("Max_Elev_m", round(float(np.max(geom_res.centerline_points[:, 2])), 2))
        feat_cl.SetField("Max_Grade_%", round(geom_res.max_grade_pct, 2))
        feat_cl.SetGeometry(geom_cl)
        lyr_cl.CreateFeature(feat_cl)
        feat_cl = None

        # 2. Road Curbs / Edges
        curbs_written = 0
        if detect_curbs and len(geom_res.curb_left_points) >= 2 and len(geom_res.curb_right_points) >= 2:
            lyr_curb = ds.CreateLayer("road_curbs_3d", target_srs, ogr.wkbLineString25D)
            lyr_curb.CreateField(ogr.FieldDefn("Curb_ID", ogr.OFTInteger))
            lyr_curb.CreateField(ogr.FieldDefn("Side", ogr.OFTString))
            lyr_curb.CreateField(ogr.FieldDefn("Length_m", ogr.OFTReal))

            for cid, (side, pts) in enumerate([("Left", geom_res.curb_left_points), ("Right", geom_res.curb_right_points)], 1):
                g_c = ogr.Geometry(ogr.wkbLineString25D)
                for pt in pts:
                    g_c.AddPoint(float(pt[0]), float(pt[1]), float(pt[2]))
                f_c = ogr.Feature(lyr_curb.GetLayerDefn())
                f_c.SetField("Curb_ID", cid)
                f_c.SetField("Side", side)
                f_c.SetField("Length_m", round(float(g_c.Length()), 1))
                f_c.SetGeometry(g_c)
                lyr_curb.CreateFeature(f_c)
                f_c = None
            curbs_written = 2

        # 3. Station Chainage Points
        lyr_st = ds.CreateLayer("road_stations_3d", target_srs, ogr.wkbPoint25D)
        lyr_st.CreateField(ogr.FieldDefn("Station", ogr.OFTString))
        lyr_st.CreateField(ogr.FieldDefn("Chainage_m", ogr.OFTReal))
        lyr_st.CreateField(ogr.FieldDefn("Elevation_m", ogr.OFTReal))
        lyr_st.CreateField(ogr.FieldDefn("Grade_%", ogr.OFTReal))
        lyr_st.CreateField(ogr.FieldDefn("Width_m", ogr.OFTReal))

        for st in geom_res.station_markers:
            g_pt = ogr.Geometry(ogr.wkbPoint25D)
            g_pt.AddPoint(st.x, st.y, st.z)
            f_st = ogr.Feature(lyr_st.GetLayerDefn())
            f_st.SetField("Station", st.station)
            f_st.SetField("Chainage_m", st.chainage_m)
            f_st.SetField("Elevation_m", st.z)
            f_st.SetField("Grade_%", st.grade_pct)
            f_st.SetField("Width_m", st.width_m)
            f_st.SetGeometry(g_pt)
            lyr_st.CreateFeature(f_st)
            f_st = None

        ds.FlushCache()
        ds = None
        return curbs_written

    @classmethod
    def write_hazard_layers(
        cls,
        hazards: List[CorridorHazard],
        out_path: str,
        srs: Optional[osr.SpatialReference] = None
    ):
        """Serializes corridor inspection hazard points into GeoPackage."""
        ds = cls._create_datasource(out_path)
        target_srs = srs if RoadSpatialReference.is_valid(srs) else osr.SpatialReference()
        lyr = ds.CreateLayer("road_hazards_audit", target_srs, ogr.wkbPoint25D)

        for f_name, f_type in [
            ("Hazard_ID", ogr.OFTInteger),
            ("Type", ogr.OFTString),
            ("Severity", ogr.OFTString),
            ("Chainage_m", ogr.OFTReal),
            ("Metric_Val", ogr.OFTReal),
            ("Description", ogr.OFTString),
        ]:
            lyr.CreateField(ogr.FieldDefn(f_name, f_type))

        for hid, h in enumerate(hazards, 1):
            geom = ogr.Geometry(ogr.wkbPoint25D)
            geom.AddPoint(h.x, h.y, h.z)
            feat = ogr.Feature(lyr.GetLayerDefn())
            feat.SetField("Hazard_ID", hid)
            feat.SetField("Type", h.hazard_type)
            feat.SetField("Severity", h.severity)
            feat.SetField("Chainage_m", h.chainage_m)
            feat.SetField("Metric_Val", h.metric_val)
            feat.SetField("Description", h.description)
            feat.SetGeometry(geom)
            lyr.CreateFeature(feat)
            feat = None

        ds.FlushCache()
        ds = None


class RoadDataLoader:
    """Loads 3D road points and centerline coordinates from LAS or vector files."""

    @staticmethod
    def load_road_points_with_srs(source_path: str) -> Tuple[np.ndarray, osr.SpatialReference]:
        ext = os.path.splitext(source_path)[1].lower()
        if ext in (".las", ".laz", ".copc.laz"):
            import laspy
            las = laspy.read(source_path)
            srs = RoadSpatialReference.from_las(las)
            classes = np.array(las.classification)
            idx_11 = np.where(classes == 11)[0]
            if len(idx_11) >= 10:
                return np.vstack((las.x[idx_11], las.y[idx_11], las.z[idx_11])).T, srs
            idx_2 = np.where(classes == 2)[0]
            if len(idx_2) >= 10:
                return np.vstack((las.x[idx_2], las.y[idx_2], las.z[idx_2])).T, srs
            return np.vstack((las.x, las.y, las.z)).T, srs

        ds = ogr.Open(source_path)
        if not ds:
            raise ValueError(f"Could not open road vector source: {source_path}")
        lyr = ds.GetLayer(0)
        srs = lyr.GetSpatialRef().Clone() if lyr.GetSpatialRef() else osr.SpatialReference()
        pts = []
        for feat in lyr:
            geom = feat.GetGeometryRef()
            if not geom:
                continue
            g_type = geom.GetGeometryType()
            if g_type in (ogr.wkbPoint, ogr.wkbPoint25D):
                pts.append([geom.GetX(), geom.GetY(), geom.GetZ() if geom.Is3D() else 0.0])
            elif g_type in (ogr.wkbLineString, ogr.wkbLineString25D):
                for i in range(geom.GetPointCount()):
                    pts.append([geom.GetX(i), geom.GetY(i), geom.GetZ(i) if geom.Is3D() else 0.0])
            elif g_type in (ogr.wkbPolygon, ogr.wkbPolygon25D):
                ring = geom.GetGeometryRef(0)
                if ring:
                    for i in range(ring.GetPointCount()):
                        pts.append([ring.GetX(i), ring.GetY(i), ring.GetZ(i) if ring.Is3D() else 0.0])
        ds = None
        return (np.array(pts, dtype=np.float32) if pts else np.empty((0, 3), dtype=np.float32)), srs

    @staticmethod
    def load_centerline_coords_with_srs(source_path: str) -> Tuple[np.ndarray, osr.SpatialReference]:
        ds = ogr.Open(source_path)
        if not ds:
            raise ValueError(f"Could not open centerline vector layer: {source_path}")
        lyr = ds.GetLayer(0)
        srs = lyr.GetSpatialRef().Clone() if lyr.GetSpatialRef() else osr.SpatialReference()
        pts = []
        for feat in lyr:
            geom = feat.GetGeometryRef()
            if not geom:
                continue
            g_type = geom.GetGeometryType()
            if g_type in (ogr.wkbLineString, ogr.wkbLineString25D):
                for i in range(geom.GetPointCount()):
                    pts.append([geom.GetX(i), geom.GetY(i), geom.GetZ(i) if geom.Is3D() else 0.0])
            elif g_type in (ogr.wkbMultiLineString, ogr.wkbMultiLineString25D):
                for j in range(geom.GetGeometryCount()):
                    sub_g = geom.GetGeometryRef(j)
                    for i in range(sub_g.GetPointCount()):
                        pts.append([sub_g.GetX(i), sub_g.GetY(i), sub_g.GetZ(i) if sub_g.Is3D() else 0.0])
        ds = None
        if len(pts) == 0:
            raise ValueError(f"No LineString geometry vertices found in {source_path}")
        return np.array(pts, dtype=np.float32), srs
