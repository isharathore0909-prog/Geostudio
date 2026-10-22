using System;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using OSGeo.GDAL;
using OSGeo.OSR;

namespace GeoStudio.Raster
{
    public static class ElevationShadedRelief
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

        // Exact Global Mapper Pro Atlas Shader stops: Blue -> Cyan -> Green -> Yellow -> Orange -> Red
        public static readonly (float frac, byte r, byte g, byte b)[] AtlasStops = new[]
        {
            (0.00f, (byte)0,   (byte)0,   (byte)255), // Min Elevation - Deep Blue
            (0.08f, (byte)0,   (byte)212, (byte)255), // Low Water - Cyan
            (0.18f, (byte)0,   (byte)184, (byte)40),  // Lowlands - Fresh Green
            (0.45f, (byte)15,  (byte)166, (byte)25),  // Dominant Plains - Lush Green
            (0.70f, (byte)96,  (byte)200, (byte)0),   // Upper Plains - Chartreuse
            (0.82f, (byte)255, (byte)214, (byte)0),   // Highland / Slope - Yellow
            (0.92f, (byte)255, (byte)102, (byte)0),   // Elevated Features - Orange
            (1.00f, (byte)204, (byte)0,   (byte)0)    // Highest Peaks - Vivid Red
        };

        // Global Mapper Terrain Shader (Earth Tones)
        public static readonly (float frac, byte r, byte g, byte b)[] TerrainStops = new[]
        {
            (0.00f, (byte)25,  (byte)104, (byte)40),
            (0.15f, (byte)63,  (byte)162, (byte)53),
            (0.30f, (byte)140, (byte)198, (byte)69),
            (0.48f, (byte)229, (byte)223, (byte)99),
            (0.65f, (byte)221, (byte)162, (byte)70),
            (0.78f, (byte)180, (byte)90,  (byte)36),
            (0.88f, (byte)125, (byte)63,  (byte)31),
            (0.96f, (byte)150, (byte)144, (byte)140),
            (1.00f, (byte)255, (byte)255, (byte)255)
        };

        // Scientific Viridis
        public static readonly (float frac, byte r, byte g, byte b)[] ViridisStops = new[]
        {
            (0.00f, (byte)68,  (byte)1,   (byte)84),
            (0.25f, (byte)59,  (byte)82,  (byte)139),
            (0.50f, (byte)33,  (byte)145, (byte)140),
            (0.75f, (byte)94,  (byte)201, (byte)98),
            (1.00f, (byte)253, (byte)231, (byte)37)
        };

        // Scientific Magma
        public static readonly (float frac, byte r, byte g, byte b)[] MagmaStops = new[]
        {
            (0.00f, (byte)0,   (byte)0,   (byte)4),
            (0.25f, (byte)81,  (byte)18,  (byte)124),
            (0.50f, (byte)183, (byte)55,  (byte)121),
            (0.75f, (byte)252, (byte)137, (byte)97),
            (1.00f, (byte)252, (byte)253, (byte)191)
        };

        // Slope gradient stops: 0° (flat green) to 45°+ (extreme cliff red)
        public static readonly (float frac, byte r, byte g, byte b)[] SlopeStops = new[]
        {
            (0.00f, (byte)34,  (byte)197, (byte)94),  // Flat: 0° (#22c55e)
            (0.15f, (byte)132, (byte)204, (byte)22),  // Gentle: 5°-10° (#84cc16)
            (0.35f, (byte)234, (byte)179, (byte)8),   // Moderate: 15°-20° (#eab308)
            (0.60f, (byte)249, (byte)115, (byte)22),  // Steep: 25°-35° (#f97316)
            (1.00f, (byte)239, (byte)68,  (byte)68)   // Extreme: 45°+ (#ef4444)
        };

        // Aspect compass direction stops: 0° to 360°
        public static readonly (float frac, byte r, byte g, byte b)[] AspectStops = new[]
        {
            (0.0000f, (byte)227, (byte)26,  (byte)28),  // North (0°)
            (0.0625f, (byte)255, (byte)127, (byte)0),   // North-East (22.5°)
            (0.1875f, (byte)255, (byte)255, (byte)51),  // East (67.5°)
            (0.3125f, (byte)77,  (byte)175, (byte)74),  // South-East (112.5°)
            (0.4375f, (byte)55,  (byte)126, (byte)184), // South (157.5°)
            (0.5625f, (byte)152, (byte)78,  (byte)163), // South-West (202.5°)
            (0.6875f, (byte)247, (byte)129, (byte)191), // West (247.5°)
            (0.8125f, (byte)166, (byte)86,  (byte)40),  // North-West (292.5°)
            (0.9375f, (byte)227, (byte)26,  (byte)28),  // North (337.5°)
            (1.0000f, (byte)227, (byte)26,  (byte)28)   // North (360°)
        };

        // Topographic Wetness Index stops: Dry Ridge (Buff/Tan) to Saturated Riverbed (Deep Blue)
        public static readonly (float frac, byte r, byte g, byte b)[] TwiStops = new[]
        {
            (0.00f, (byte)245, (byte)235, (byte)200), // Very dry ridge (Tan)
            (0.20f, (byte)210, (byte)225, (byte)170), // Dry slope (Pale green)
            (0.40f, (byte)120, (byte)198, (byte)121), // Moderate moisture (Green)
            (0.65f, (byte)65,  (byte)182, (byte)196), // Wet (Cyan)
            (0.85f, (byte)34,  (byte)94,  (byte)168), // High wetness (Blue)
            (1.00f, (byte)8,   (byte)29,  (byte)88)   // Drainage / River (Deep Blue)
        };

        // Surface Curvature stops: Convex / Ridge (Red) -> Planar (Light Gray) -> Concave / Valley (Blue)
        public static readonly (float frac, byte r, byte g, byte b)[] CurvatureStops = new[]
        {
            (0.00f, (byte)215, (byte)48,  (byte)39),  // Convex / Ridge (Red)
            (0.25f, (byte)252, (byte)141, (byte)89),  // Moderately convex (Orange)
            (0.50f, (byte)240, (byte)240, (byte)240), // Planar / Flat (Light Gray)
            (0.75f, (byte)145, (byte)191, (byte)219), // Moderately concave (Cyan/Blue)
            (1.00f, (byte)69,  (byte)117, (byte)180)  // Concave / Valley (Deep Blue)
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

        public static byte[] Render3DShadedReliefBgra(
            float[] data,
            int width,
            int height,
            double minElev,
            double maxElev,
            double cellX,
            double cellY,
            double? noDataVal = null,
            string palette = "GLOBAL_MAPPER_ATLAS",
            string shaderMode = "atlas")
        {
            byte[] bgra = new byte[width * height * 4];
            double dz = maxElev - minElev;
            if (dz <= 0.001) dz = 1.0;

            // Intelligent vertical exaggeration factor
            double zFactor = dz <= 5.0  ? 6.0 :
                             dz <= 25.0 ? 3.5 :
                             dz <= 60.0 ? 2.5 :
                             dz <= 150.0 ? 1.8 : 1.2;

            double dx_m = Math.Abs(cellX) > 0 ? Math.Abs(cellX) : 1.0;
            double dy_m = Math.Abs(cellY) > 0 ? Math.Abs(cellY) : 1.0;

            // Multi-directional hillshade setup: NW 315° (0.60), SW 225° (0.25), NE 45° (0.15)
            const double altRad = 45.0 * Math.PI / 180.0;
            const double az1Rad = 315.0 * Math.PI / 180.0;
            const double az2Rad = 225.0 * Math.PI / 180.0;
            const double az3Rad = 45.0 * Math.PI / 180.0;

            double sinAlt = Math.Sin(altRad);
            double cosAlt = Math.Cos(altRad);

            string sMode = (shaderMode ?? "atlas").ToLowerInvariant();
            string pMode = (palette ?? "GLOBAL_MAPPER_ATLAS").ToLowerInvariant();

            (float frac, byte r, byte g, byte b)[] stops;
            if (sMode.Contains("slope")) stops = SlopeStops;
            else if (sMode.Contains("aspect")) stops = AspectStops;
            else if (sMode.Contains("twi")) stops = TwiStops;
            else if (sMode.Contains("curvature")) stops = CurvatureStops;
            else if (pMode.Contains("terrain") || sMode.Contains("terrain")) stops = TerrainStops;
            else if (pMode.Contains("viridis") || sMode.Contains("viridis")) stops = ViridisStops;
            else if (pMode.Contains("magma") || sMode.Contains("magma")) stops = MagmaStops;
            else stops = AtlasStops;

            Parallel.For(0, height, y =>
            {
                int yOff = y * width;
                int yAbove = Math.Max(0, y - 1) * width;
                int yBelow = Math.Min(height - 1, y + 1) * width;

                for (int x = 0; x < width; x++)
                {
                    int idx = yOff + x;
                    float val = data[idx];

                    // Check validity
                    bool isValid = !float.IsNaN(val) && !float.IsInfinity(val) &&
                                   val > -10000 && val < 50000;
                    if (isValid && noDataVal.HasValue && Math.Abs(val - noDataVal.Value) < 1e-4)
                    {
                        isValid = false;
                    }

                    int dstIdx = idx * 4;
                    if (!isValid)
                    {
                        bgra[dstIdx] = 0;
                        bgra[dstIdx + 1] = 0;
                        bgra[dstIdx + 2] = 0;
                        bgra[dstIdx + 3] = 0; // Transparent
                        continue;
                    }

                    // Central difference gradient
                    int xLeft = Math.Max(0, x - 1);
                    int xRight = Math.Min(width - 1, x + 1);

                    float zL = data[yOff + xLeft];
                    float zR = data[yOff + xRight];
                    float zT = data[yAbove + x];
                    float zB = data[yBelow + x];

                    double dx = (zR - zL) / (2.0 * dx_m);
                    double dy = (zB - zT) / (2.0 * dy_m);

                    double hyp = Math.Sqrt(dx * dx + dy * dy) * zFactor;
                    double slope = Math.Atan(hyp); // 0 = horizontal plane, pi/2 = vertical cliff
                    double aspect = Math.Atan2(-dx, dy);

                    double sinSlope = Math.Sin(slope);
                    double cosSlope = Math.Cos(slope);

                    // Multi-directional Lambertian 3D illumination:
                    // cos(i) = sin(alt)*cos(slope) + cos(alt)*sin(slope)*cos(az - aspect)
                    double hs1 = Math.Max(0.0, sinAlt * cosSlope + cosAlt * sinSlope * Math.Cos(az1Rad - aspect));
                    double hs2 = Math.Max(0.0, sinAlt * cosSlope + cosAlt * sinSlope * Math.Cos(az2Rad - aspect));
                    double hs3 = Math.Max(0.0, sinAlt * cosSlope + cosAlt * sinSlope * Math.Cos(az3Rad - aspect));

                    double rawShade = 0.55 * hs1 + 0.30 * hs2 + 0.15 * hs3;
                    double shaded = Math.Clamp(rawShade, 0.0, 1.0);

                    // MODE-SPECIFIC RENDERING:
                    if (sMode.Contains("hillshade"))
                    {
                        // Pure monochrome 3D hillshade
                        byte gray = (byte)Math.Clamp((int)(shaded * 255.0), 0, 255);
                        bgra[dstIdx] = gray;
                        bgra[dstIdx + 1] = gray;
                        bgra[dstIdx + 2] = gray;
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("slope"))
                    {
                        // True slope angle in degrees
                        double slopeDeg = (Math.PI / 2.0 - slope) * (180.0 / Math.PI);
                        float normVal = (float)Math.Clamp(slopeDeg / 45.0, 0.0, 1.0);
                        byte bR, bG, bB;
                        InterpolateColor(stops, normVal, out bR, out bG, out bB);

                        double shadeMod = 0.35 + 0.65 * shaded;
                        bgra[dstIdx] = (byte)Math.Clamp((int)(bB * shadeMod), 0, 255);
                        bgra[dstIdx + 1] = (byte)Math.Clamp((int)(bG * shadeMod), 0, 255);
                        bgra[dstIdx + 2] = (byte)Math.Clamp((int)(bR * shadeMod), 0, 255);
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("aspect"))
                    {
                        // Compass aspect (0° - 360°)
                        double aspectDeg = (aspect * 180.0 / Math.PI + 360.0) % 360.0;
                        float normVal = (float)(aspectDeg / 360.0);
                        byte bR, bG, bB;
                        InterpolateColor(stops, normVal, out bR, out bG, out bB);

                        double shadeMod = 0.50 + 0.50 * shaded;
                        bgra[dstIdx] = (byte)Math.Clamp((int)(bB * shadeMod), 0, 255);
                        bgra[dstIdx + 1] = (byte)Math.Clamp((int)(bG * shadeMod), 0, 255);
                        bgra[dstIdx + 2] = (byte)Math.Clamp((int)(bR * shadeMod), 0, 255);
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("tri"))
                    {
                        // Terrain Ruggedness Index: difference between center and 8 neighbors
                        float sumDiff = Math.Abs(val - zL) + Math.Abs(val - zR) + Math.Abs(val - zT) + Math.Abs(val - zB);
                        float normVal = (float)Math.Clamp(sumDiff / (dz * 0.15 + 1e-4), 0.0, 1.0);
                        byte bR, bG, bB;
                        InterpolateColor(MagmaStops, normVal, out bR, out bG, out bB);

                        bgra[dstIdx] = bB;
                        bgra[dstIdx + 1] = bG;
                        bgra[dstIdx + 2] = bR;
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("tpi"))
                    {
                        // Topographic Position Index: cell minus neighborhood mean
                        float mean = (zL + zR + zT + zB) * 0.25f;
                        float tpi = val - mean;
                        float normVal = (float)Math.Clamp(0.5f + (tpi / (dz * 0.08f + 1e-4f)) * 0.5f, 0.0f, 1.0f);
                        byte bR, bG, bB;
                        InterpolateColor(AtlasStops, normVal, out bR, out bG, out bB);

                        double shadeMod = 0.40 + 0.60 * shaded;
                        bgra[dstIdx] = (byte)Math.Clamp((int)(bB * shadeMod), 0, 255);
                        bgra[dstIdx + 1] = (byte)Math.Clamp((int)(bG * shadeMod), 0, 255);
                        bgra[dstIdx + 2] = (byte)Math.Clamp((int)(bR * shadeMod), 0, 255);
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("twi"))
                    {
                        // Topographic Wetness Index (TWI proxy): ln(area / tan(slope))
                        double slopeRad = Math.Atan(Math.Sqrt(dx * dx + dy * dy));
                        double tanSlope = Math.Max(Math.Tan(slopeRad), 0.005);
                        float laplacian = (zL + zR + zT + zB) - 4.0f * val;
                        double areaProxy = dx_m * (1.0 + Math.Max(0.0f, laplacian));
                        double twi = Math.Log(Math.Max(1e-4, areaProxy / tanSlope));
                        float normVal = (float)Math.Clamp((twi - 1.0) / 9.0, 0.0, 1.0);
                        byte bR, bG, bB;
                        InterpolateColor(stops, normVal, out bR, out bG, out bB);

                        double shadeMod = 0.50 + 0.50 * shaded;
                        bgra[dstIdx] = (byte)Math.Clamp((int)(bB * shadeMod), 0, 255);
                        bgra[dstIdx + 1] = (byte)Math.Clamp((int)(bG * shadeMod), 0, 255);
                        bgra[dstIdx + 2] = (byte)Math.Clamp((int)(bR * shadeMod), 0, 255);
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("curvature"))
                    {
                        // Surface Curvature (Laplacian of elevation)
                        double d2z_dx2 = (zR - 2.0 * val + zL) / (dx_m * dx_m);
                        double d2z_dy2 = (zB - 2.0 * val + zT) / (dy_m * dy_m);
                        double curv = -100.0 * (d2z_dx2 + d2z_dy2);
                        float normVal = (float)Math.Clamp(0.5 + curv * 2.5, 0.0, 1.0);
                        byte bR, bG, bB;
                        InterpolateColor(stops, normVal, out bR, out bG, out bB);

                        double shadeMod = 0.40 + 0.60 * shaded;
                        bgra[dstIdx] = (byte)Math.Clamp((int)(bB * shadeMod), 0, 255);
                        bgra[dstIdx + 1] = (byte)Math.Clamp((int)(bG * shadeMod), 0, 255);
                        bgra[dstIdx + 2] = (byte)Math.Clamp((int)(bR * shadeMod), 0, 255);
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }

                    // Default: 3D Shaded Relief with selected palette
                    float normElev = (float)Math.Clamp((val - minElev) / dz, 0.0, 1.0);
                    byte baseR, baseG, baseB;
                    InterpolateColor(stops, normElev, out baseR, out baseG, out baseB);

                    // Global Mapper 3D shaded relief soft-light compositing:
                    // Flat ground (shaded ≈ 0.7071) remains true palette color.
                    // Sun-facing slopes (shaded > 0.7071) get bright 3D highlights.
                    // Shadow slopes (shaded < 0.7071) get deep 3D relief shadows.
                    double normShade = Math.Clamp((shaded - 0.7071) * 1.5 + 0.5, 0.0, 1.0);
                    double factor = (normShade - 0.5) * 1.5;

                    byte finalB, finalG, finalR;
                    if (factor >= 0)
                    {
                        finalB = (byte)Math.Clamp((int)(baseB + factor * (255 - baseB)), 0, 255);
                        finalG = (byte)Math.Clamp((int)(baseG + factor * (255 - baseG)), 0, 255);
                        finalR = (byte)Math.Clamp((int)(baseR + factor * (255 - baseR)), 0, 255);
                    }
                    else
                    {
                        double darkScale = 1.0 + factor;
                        finalB = (byte)Math.Clamp((int)(baseB * darkScale), 0, 255);
                        finalG = (byte)Math.Clamp((int)(baseG * darkScale), 0, 255);
                        finalR = (byte)Math.Clamp((int)(baseR * darkScale), 0, 255);
                    }

                    bgra[dstIdx] = finalB;
                    bgra[dstIdx + 1] = finalG;
                    bgra[dstIdx + 2] = finalR;
                    bgra[dstIdx + 3] = 255;                                             // Alpha
                }
            });

            return bgra;
        }

        private static void InterpolateColor((float frac, byte r, byte g, byte b)[] stops, float normVal, out byte outR, out byte outG, out byte outB)
        {
            outR = 255; outG = 255; outB = 255;
            for (int s = 0; s < stops.Length - 1; s++)
            {
                var s0 = stops[s];
                var s1 = stops[s + 1];
                if (normVal >= s0.frac && (normVal <= s1.frac || s == stops.Length - 2))
                {
                    float t = (normVal - s0.frac) / (s1.frac - s0.frac + 1e-6f);
                    t = Math.Clamp(t, 0.0f, 1.0f);
                    outR = (byte)(s0.r + t * (s1.r - s0.r));
                    outG = (byte)(s0.g + t * (s1.g - s0.g));
                    outB = (byte)(s0.b + t * (s1.b - s0.b));
                    return;
                }
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
