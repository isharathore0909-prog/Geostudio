using System;
using System.IO;
using OSGeo.GDAL;
using OSGeo.OSR;

namespace GeoStudio.Raster
{
    public static partial class ElevationShadedRelief
    {
        private static readonly string[] ElevationKeywords = new[]
        {
            "dem", "dtm", "dsm", "elevation", "elev", "hgt", "srtm", "alos",
            "copernicus", "lidar", "las", "bathymetry", "bathy", "height",
            "terrain", "relief", "topo", "surface", "altitude", "chm"
        };

        private static readonly string[] ImageryKeywords = new[]
        {
            "ortho", "orthomosaic", "mosaic", "aerial", "satellite", "imagery",
            "photo", "rgb", "rgba", "truecolor", "uav", "drone"
        };

        public static bool IsElevationRaster(Dataset ds, string filePath)
        {
            if (ds == null) return false;
            int bands = ds.RasterCount;
            if (bands != 1) return false;

            string name = Path.GetFileName(filePath).ToLowerInvariant();
            foreach (var imgKw in ImageryKeywords)
            {
                if (name.Contains(imgKw)) return false;
            }

            foreach (var elevKw in ElevationKeywords)
            {
                if (name.Contains(elevKw)) return true;
            }

            var band = ds.GetRasterBand(1);
            if (band != null)
            {
                var dt = band.DataType;
                if (dt == DataType.GDT_Float32 || dt == DataType.GDT_Float64 ||
                    dt == DataType.GDT_Int16 || dt == DataType.GDT_Int32 || dt == DataType.GDT_UInt16)
                {
                    return true;
                }
            }

            return false;
        }

        public static (double minElev, double maxElev) GetElevationStats(Dataset ds, int sampleW = 512, int sampleH = 512)
        {
            try
            {
                var band = ds.GetRasterBand(1);
                band.GetNoDataValue(out double noData, out int hasNoData);

                int fullW = ds.RasterXSize;
                int fullH = ds.RasterYSize;
                int sW = Math.Min(fullW, sampleW);
                int sH = Math.Min(fullH, sampleH);

                float[] buf = new float[sW * sH];
                band.ReadRaster(0, 0, fullW, fullH, buf, sW, sH, 0, 0);

                double minVal = double.MaxValue;
                double maxVal = double.MinValue;

                for (int i = 0; i < buf.Length; i++)
                {
                    float v = buf[i];
                    if (float.IsNaN(v) || float.IsInfinity(v)) continue;
                    if (hasNoData != 0 && Math.Abs(v - noData) < 1e-4) continue;
                    if (v < -10000 || v > 50000) continue;

                    if (v < minVal) minVal = v;
                    if (v > maxVal) maxVal = v;
                }

                if (minVal >= maxVal)
                {
                    minVal = 0;
                    maxVal = 100;
                }

                return (minVal, maxVal);
            }
            catch
            {
                return (0, 100);
            }
        }

        public static (double[] distances, double[] elevations) SampleProfileLine(string filePath, double lon1, double lat1, double lon2, double lat2, int numSamples = 100)
        {
            if (!File.Exists(filePath)) return (Array.Empty<double>(), Array.Empty<double>());
            using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
            if (ds == null) return (Array.Empty<double>(), Array.Empty<double>());

            double[] gt = new double[6];
            ds.GetGeoTransform(gt);
            int w = ds.RasterXSize;
            int h = ds.RasterYSize;

            double p1X = lon1, p1Y = lat1;
            double p2X = lon2, p2Y = lat2;

            string projWkt = ds.GetProjectionRef();
            if (!string.IsNullOrWhiteSpace(projWkt))
            {
                using var srsRaster = new SpatialReference(projWkt);
                srsRaster.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                using var srs4326 = new SpatialReference("");
                srs4326.ImportFromEPSG(4326);
                srs4326.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);

                if (srsRaster.IsSame(srs4326, null) == 0 && srsRaster.IsProjected() == 1)
                {
                    using var ct = new CoordinateTransformation(srs4326, srsRaster);
                    double[] ptA = new double[] { lon1, lat1, 0 };
                    double[] ptB = new double[] { lon2, lat2, 0 };
                    ct.TransformPoint(ptA);
                    ct.TransformPoint(ptB);
                    p1X = ptA[0]; p1Y = ptA[1];
                    p2X = ptB[0]; p2Y = ptB[1];
                }
            }

            double totalDist = Math.Sqrt(Math.Pow(p2X - p1X, 2) + Math.Pow(p2Y - p1Y, 2));
            var distances = new double[numSamples];
            var elevations = new double[numSamples];

            var band = ds.GetRasterBand(1);
            band.GetNoDataValue(out double noData, out int hasNoData);

            for (int i = 0; i < numSamples; i++)
            {
                double t = (double)i / (numSamples - 1);
                double curX = p1X + t * (p2X - p1X);
                double curY = p1Y + t * (p2Y - p1Y);

                distances[i] = t * totalDist;

                int px = (int)Math.Round((curX - gt[0]) / gt[1]);
                int py = (int)Math.Round((curY - gt[3]) / gt[5]);

                if (px >= 0 && px < w && py >= 0 && py < h)
                {
                    float[] buf = new float[1];
                    band.ReadRaster(px, py, 1, 1, buf, 1, 1, 0, 0);
                    float v = buf[0];
                    if (!float.IsNaN(v) && !float.IsInfinity(v) && (hasNoData == 0 || Math.Abs(v - noData) >= 1e-4))
                    {
                        elevations[i] = v;
                    }
                    else
                    {
                        elevations[i] = i > 0 ? elevations[i - 1] : 0;
                    }
                }
                else
                {
                    elevations[i] = i > 0 ? elevations[i - 1] : 0;
                }
            }

            return (distances, elevations);
        }
    }
}
