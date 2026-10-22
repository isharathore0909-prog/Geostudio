using System;
using System.IO;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using OSGeo.GDAL;
using OSGeo.OSR;

namespace GeoStudio.Raster
{
    public static class GdalWindowRenderer
    {
        private static readonly object _renderLock = new object();

        public static WindowRenderResult RenderWindow(
            string filePath,
            double reqMinLon, double reqMinLat, double reqMaxLon, double reqMaxLat,
            int screenW, int screenH,
            string? shaderMode = null,
            string? palette = null)
        {
            GdalCacheManager.Initialize();
            if (!File.Exists(filePath)) return new WindowRenderResult { Success = false };

            try
            {
                var ds = GdalCacheManager.GetOpenDataset(filePath);
                if (ds == null) return new WindowRenderResult { Success = false };

                double[] gt = new double[6];
                lock (_renderLock)
                {
                    ds.GetGeoTransform(gt);
                }
                if (gt[1] == 0 || gt[5] == 0) return new WindowRenderResult { Success = false };

                int fullW = ds.RasterXSize;
                int fullH = ds.RasterYSize;
                int bands = ds.RasterCount;

                double minX = reqMinLon;
                double minY = reqMinLat;
                double maxX = reqMaxLon;
                double maxY = reqMaxLat;

                CoordinateTransformation? ctTo4326 = null;
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
                        using var ctToRaster = new CoordinateTransformation(srs4326, srsRaster);
                        ctTo4326 = new CoordinateTransformation(srsRaster, srs4326);

                        double[] pMin = new double[] { reqMinLon, reqMinLat, 0 };
                        double[] pMax = new double[] { reqMaxLon, reqMaxLat, 0 };
                        ctToRaster.TransformPoint(pMin);
                        ctToRaster.TransformPoint(pMax);

                        minX = Math.Min(pMin[0], pMax[0]);
                        maxX = Math.Max(pMin[0], pMax[0]);
                        minY = Math.Min(pMin[1], pMax[1]);
                        maxY = Math.Max(pMin[1], pMax[1]);
                    }
                }

                double pxMinX = (minX - gt[0]) / gt[1];
                double pxMaxX = (maxX - gt[0]) / gt[1];
                double pxMinY = (maxY - gt[3]) / gt[5];
                double pxMaxY = (minY - gt[3]) / gt[5];

                int x1 = (int)Math.Floor(Math.Min(pxMinX, pxMaxX));
                int x2 = (int)Math.Ceiling(Math.Max(pxMinX, pxMaxX));
                int y1 = (int)Math.Floor(Math.Min(pxMinY, pxMaxY));
                int y2 = (int)Math.Ceiling(Math.Max(pxMinY, pxMaxY));

                int xOff = Math.Max(0, x1);
                int yOff = Math.Max(0, y1);
                int xEnd = Math.Min(fullW, x2);
                int yEnd = Math.Min(fullH, y2);

                int winW = xEnd - xOff;
                int winH = yEnd - yOff;

                if (winW <= 0 || winH <= 0)
                    return new WindowRenderResult { Success = false };

                int targetMaxW = 4096;
                int targetMaxH = 4096;

                int targetW = winW <= targetMaxW ? winW : targetMaxW;
                int targetH = (int)Math.Max(1, Math.Round((double)winH / winW * targetW));
                if (targetH > targetMaxH)
                {
                    targetH = targetMaxH;
                    targetW = Math.Max(1, (int)Math.Round((double)winW / winH * targetH));
                }

                byte[] bgra;
                bool isElevation = ElevationShadedRelief.IsElevationRaster(ds, filePath) ||
                                   (!string.IsNullOrEmpty(shaderMode) && shaderMode != "none" && ds.RasterCount == 1);

                if (isElevation)
                {
                    float[] floatBuf = new float[targetW * targetH];
                    lock (_renderLock)
                    {
                        var b1 = ds.GetRasterBand(1);
                        int safeWinW = Math.Min(winW, fullW - xOff);
                        int safeWinH = Math.Min(winH, fullH - yOff);
                        b1.ReadRaster(xOff, yOff, safeWinW, safeWinH, floatBuf, targetW, targetH, 0, 0);
                        b1.GetNoDataValue(out double noDataVal, out int hasNoData);

                        var (minElev, maxElev) = ElevationShadedRelief.GetElevationStats(ds);
                        double cellX = Math.Abs(gt[1]) * ((double)winW / targetW);
                        double cellY = Math.Abs(gt[5]) * ((double)winH / targetH);
                        if (ctTo4326 == null && Math.Abs(gt[1]) < 0.005)
                        {
                            double midLat = (reqMinLat + reqMaxLat) / 2.0;
                            double latRad = midLat * Math.PI / 180.0;
                            cellX *= 111320.0 * Math.Max(0.1, Math.Cos(latRad));
                            cellY *= 111320.0;
                        }

                        string effectiveShader = string.IsNullOrEmpty(shaderMode) ? "atlas" : shaderMode;
                        string effectivePalette = string.IsNullOrEmpty(palette) ? "GLOBAL_MAPPER_ATLAS" : palette;

                        bgra = ElevationShadedRelief.Render3DShadedReliefBgra(
                            floatBuf, targetW, targetH,
                            minElev, maxElev,
                            cellX, cellY,
                            hasNoData != 0 ? noDataVal : null,
                            effectivePalette,
                            effectiveShader);
                    }
                }
                else
                {
                    byte[] rData = new byte[targetW * targetH];
                    byte[] gData = new byte[targetW * targetH];
                    byte[] bData = new byte[targetW * targetH];
                    byte[]? aData = bands >= 4 ? new byte[targetW * targetH] : null;

                    int rBand = 1;
                    int gBand = Math.Min(2, bands);
                    int bBand = Math.Min(3, bands);

                    lock (_renderLock)
                    {
                        var b1 = ds.GetRasterBand(rBand);
                        int ovrCount = b1 != null ? b1.GetOverviewCount() : 0;
                        Band rBandObj = ds.GetRasterBand(rBand);
                        Band gBandObj = ds.GetRasterBand(gBand);
                        Band bBandObj = ds.GetRasterBand(bBand);
                        Band? aBandObj = aData != null && bands >= 4 ? ds.GetRasterBand(4) : null;

                        if (ovrCount > 0 && winW > targetW * 2)
                        {
                            int bestIdx = -1;
                            for (int o = 0; o < ovrCount; o++)
                            {
                                var ovr = b1!.GetOverview(o);
                                if (ovr != null && (ovr.XSize * ((double)winW / fullW)) >= targetW)
                                {
                                    bestIdx = o;
                                }
                            }
                            if (bestIdx == -1) bestIdx = 0;

                            if (bestIdx >= 0)
                            {
                                rBandObj = ds.GetRasterBand(rBand).GetOverview(bestIdx);
                                gBandObj = ds.GetRasterBand(gBand).GetOverview(bestIdx);
                                bBandObj = ds.GetRasterBand(bBand).GetOverview(bestIdx);
                                if (aBandObj != null) aBandObj = ds.GetRasterBand(4).GetOverview(bestIdx);

                                int ovrFullW = rBandObj.XSize;
                                int ovrFullH = rBandObj.YSize;
                                int ovrXOff = Math.Clamp((int)Math.Floor((double)xOff / fullW * ovrFullW), 0, Math.Max(0, ovrFullW - 1));
                                int ovrYOff = Math.Clamp((int)Math.Floor((double)yOff / fullH * ovrFullH), 0, Math.Max(0, ovrFullH - 1));
                                int ovrWinW = Math.Clamp((int)Math.Ceiling((double)winW / fullW * ovrFullW), 1, ovrFullW - ovrXOff);
                                int ovrWinH = Math.Clamp((int)Math.Ceiling((double)winH / fullH * ovrFullH), 1, ovrFullH - ovrYOff);

                                rBandObj.ReadRaster(ovrXOff, ovrYOff, ovrWinW, ovrWinH, rData, targetW, targetH, 0, 0);
                                gBandObj.ReadRaster(ovrXOff, ovrYOff, ovrWinW, ovrWinH, gData, targetW, targetH, 0, 0);
                                bBandObj.ReadRaster(ovrXOff, ovrYOff, ovrWinW, ovrWinH, bData, targetW, targetH, 0, 0);
                                if (aBandObj != null && aData != null)
                                    aBandObj.ReadRaster(ovrXOff, ovrYOff, ovrWinW, ovrWinH, aData, targetW, targetH, 0, 0);
                            }
                            else
                            {
                                int safeWinW = Math.Min(winW, fullW - xOff);
                                int safeWinH = Math.Min(winH, fullH - yOff);
                                rBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, rData, targetW, targetH, 0, 0);
                                gBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, gData, targetW, targetH, 0, 0);
                                bBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, bData, targetW, targetH, 0, 0);
                                if (aBandObj != null && aData != null)
                                    aBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, aData, targetW, targetH, 0, 0);
                            }
                        }
                        else
                        {
                            if (winW > 8192)
                            {
                                return new WindowRenderResult { Success = false };
                            }

                            int safeWinW = Math.Min(winW, fullW - xOff);
                            int safeWinH = Math.Min(winH, fullH - yOff);
                            rBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, rData, targetW, targetH, 0, 0);
                            gBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, gData, targetW, targetH, 0, 0);
                            bBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, bData, targetW, targetH, 0, 0);
                            if (aBandObj != null && aData != null)
                                aBandObj.ReadRaster(xOff, yOff, safeWinW, safeWinH, aData, targetW, targetH, 0, 0);
                        }
                    }

                    bgra = new byte[targetW * targetH * 4];
                    unsafe
                    {
                        fixed (byte* pBgra = bgra, pR = rData, pG = gData, pB = bData)
                        {
                            byte* pDst = pBgra;
                            byte* pEnd = pBgra + (targetW * targetH * 4);
                            byte* pSrcR = pR;
                            byte* pSrcG = pG;
                            byte* pSrcB = pB;

                            if (aData != null)
                            {
                                fixed (byte* pA = aData)
                                {
                                    byte* pSrcA = pA;
                                    while (pDst < pEnd)
                                    {
                                        byte b = *pSrcB++;
                                        byte g = *pSrcG++;
                                        byte r = *pSrcR++;
                                        byte a = *pSrcA++;
                                        if (a == 0 && (r != 0 || g != 0 || b != 0)) a = 255;
                                        *pDst++ = b;
                                        *pDst++ = g;
                                        *pDst++ = r;
                                        *pDst++ = a;
                                    }
                                }
                            }
                            else
                            {
                                while (pDst < pEnd)
                                {
                                    byte b = *pSrcB++;
                                    byte g = *pSrcG++;
                                    byte r = *pSrcR++;
                                    *pDst++ = b;
                                    *pDst++ = g;
                                    *pDst++ = r;
                                    *pDst++ = (byte)((r == 0 && g == 0 && b == 0) ? 0 : 255);
                                }
                            }
                        }
                    }
                }

                string cacheDir = GdalCacheManager.GetCacheDirectory();
                string cacheFile = $"win_{Guid.NewGuid():N}.png";
                string outPath = Path.Combine(cacheDir, cacheFile);

                GdalCacheManager.PruneCache();

                var bmp = BitmapSource.Create(targetW, targetH, 96, 96, PixelFormats.Bgra32, null, bgra, targetW * 4);
                bmp.Freeze();

                using (var fs = new FileStream(outPath, FileMode.Create, FileAccess.Write, FileShare.None, 65536))
                {
                    var enc = new PngBitmapEncoder();
                    enc.Frames.Add(BitmapFrame.Create(bmp));
                    enc.Save(fs);
                    fs.Flush(true);
                }

                double exactMinX = gt[0] + (xOff * gt[1]);
                double exactMaxX = gt[0] + (xEnd * gt[1]);
                double exactMaxY = gt[3] + (yOff * gt[5]);
                double exactMinY = gt[3] + (yEnd * gt[5]);

                if (ctTo4326 != null)
                {
                    double[] p1 = new double[] { exactMinX, exactMinY, 0 };
                    double[] p2 = new double[] { exactMaxX, exactMaxY, 0 };
                    ctTo4326.TransformPoint(p1);
                    ctTo4326.TransformPoint(p2);
                    exactMinX = Math.Min(p1[0], p2[0]);
                    exactMinY = Math.Min(p1[1], p2[1]);
                    exactMaxX = Math.Max(p1[0], p2[0]);
                    exactMaxY = Math.Max(p1[1], p2[1]);
                    ctTo4326.Dispose();
                }

                return new WindowRenderResult
                {
                    Success = true,
                    ImageUrl = $"http://cache.geostudio.local/{cacheFile}",
                    Extent = new double[]
                    {
                        Math.Min(exactMinX, exactMaxX),
                        Math.Min(exactMinY, exactMaxY),
                        Math.Max(exactMinX, exactMaxX),
                        Math.Max(exactMinY, exactMaxY)
                    }
                };
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Window render warning: {ex.Message}");
                return new WindowRenderResult { Success = false };
            }
        }
    }
}
