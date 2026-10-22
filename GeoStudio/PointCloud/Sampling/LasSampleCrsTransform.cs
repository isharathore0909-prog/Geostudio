using System;
using OSGeo.OSR;

namespace GeoStudio.PointCloud
{
    internal sealed class Worker : IDisposable
    {
        public readonly double[] Pt = new double[3];
        public readonly CrsTransform? T;

        public Worker(LasCrsInfo? crs, double minX, double maxX, double minY, double maxY)
        {
            if (crs.HasValue) T = CrsTransform.Create(crs.Value, minX, maxX, minY, maxY);
        }
        public void Dispose() => T?.Dispose();
    }

    internal sealed class CrsTransform : IDisposable
    {
        public SpatialReference Src = null!, Dst = null!;
        public CoordinateTransformation Ct = null!;
        public bool Assumed;

        public static CrsTransform? Create(LasCrsInfo crs, double minX, double maxX, double minY, double maxY)
        {
            SpatialReference? src = null;
            bool assumed = false;
            if (!string.IsNullOrWhiteSpace(crs.Wkt)) src = new SpatialReference(crs.Wkt);
            else if (crs.Epsg is > 0) { src = new SpatialReference(""); src.ImportFromEPSG(crs.Epsg.Value); }
            else if (crs.IsProjected || Math.Abs(minX) > 180 || Math.Abs(maxY) > 90)
            {
                src = new SpatialReference(""); src.ImportFromEPSG(32643); assumed = true;
            }
            if (src == null) return null;
            src.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);

            var dst = new SpatialReference("");
            dst.ImportFromEPSG(4326);
            dst.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);

            if (src.IsSame(dst, null) != 0 || !(src.IsProjected() == 1 || crs.IsProjected))
            {
                src.Dispose(); dst.Dispose();
                return null;
            }
            return new CrsTransform { Src = src, Dst = dst, Ct = new CoordinateTransformation(src, dst), Assumed = assumed };
        }

        public void Dispose() { Ct?.Dispose(); Src?.Dispose(); Dst?.Dispose(); }
    }
}
