using System;
using System.Threading.Tasks;

namespace GeoStudio.Raster
{
    public static partial class ElevationShadedRelief
    {
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
            else if (pMode.Contains("inferno") || sMode.Contains("thermal") || sMode.Contains("lst")) stops = InfernoStops;
            else if (sMode.Contains("ndwi") || pMode.Contains("ndwi")) stops = NdwiStops;
            else if (sMode.Contains("ndvi") || sMode.Contains("evi") || pMode.Contains("ndvi") || pMode.Contains("evi")) stops = NdviStops;
            else if (sMode.Contains("ndbi") || pMode.Contains("ndbi")) stops = NdbiStops;
            else if (sMode.Contains("nbr") || pMode.Contains("nbr")) stops = NbrStops;
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

                    // Multi-directional Lambertian 3D illumination
                    double hs1 = Math.Max(0.0, sinAlt * cosSlope + cosAlt * sinSlope * Math.Cos(az1Rad - aspect));
                    double hs2 = Math.Max(0.0, sinAlt * cosSlope + cosAlt * sinSlope * Math.Cos(az2Rad - aspect));
                    double hs3 = Math.Max(0.0, sinAlt * cosSlope + cosAlt * sinSlope * Math.Cos(az3Rad - aspect));

                    double rawShade = 0.55 * hs1 + 0.30 * hs2 + 0.15 * hs3;
                    double shaded = Math.Clamp(rawShade, 0.0, 1.0);

                    // MODE-SPECIFIC RENDERING:
                    if (sMode.Contains("hillshade"))
                    {
                        byte gray = (byte)Math.Clamp((int)(shaded * 255.0), 0, 255);
                        bgra[dstIdx] = gray;
                        bgra[dstIdx + 1] = gray;
                        bgra[dstIdx + 2] = gray;
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }
                    else if (sMode.Contains("slope"))
                    {
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

                    if (sMode.Contains("thermal") || sMode.Contains("lst") || pMode.Contains("inferno") ||
                        sMode.Contains("ndwi") || sMode.Contains("ndvi") || sMode.Contains("evi") ||
                        sMode.Contains("ndbi") || sMode.Contains("nbr"))
                    {
                        bgra[dstIdx] = baseB;
                        bgra[dstIdx + 1] = baseG;
                        bgra[dstIdx + 2] = baseR;
                        bgra[dstIdx + 3] = 255;
                        continue;
                    }

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
                    bgra[dstIdx + 3] = 255;
                }
            });

            return bgra;
        }
    }
}
