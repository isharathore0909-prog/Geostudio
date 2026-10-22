using System;
using System.IO;
using System.Threading.Tasks;
using System.Collections.Concurrent;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using OSGeo.GDAL;
using OSGeo.OSR;

namespace GeoStudio.Raster
{
    public static class GdalOverviewGenerator
    {
        public static event Action<string, string>? OverviewReady;
        private static readonly ConcurrentDictionary<string, bool> _overviewGeneratingPaths = new();

        public static void QueueOverviewGeneration(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath)) return;
            string normPath = Path.GetFullPath(filePath);
            if (!_overviewGeneratingPaths.TryAdd(normPath, true)) return;

            Task.Run(() =>
            {
                try
                {
                    var meta = InspectAndGeneratePreview(normPath, previewWidth: 2048);
                    if (!string.IsNullOrEmpty(meta.PreviewUrl))
                    {
                        OverviewReady?.Invoke(normPath, meta.PreviewUrl);
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Background overview generation error: {ex.Message}");
                }
                finally
                {
                    _overviewGeneratingPaths.TryRemove(normPath, out _);
                }
            });
        }

        public static GdalRasterMetadata InspectAndGeneratePreview(string filePath, int previewWidth = 2048, string shaderMode = "atlas", string palette = "GLOBAL_MAPPER_ATLAS")
        {
            GdalCacheManager.Initialize();

            if (!File.Exists(filePath))
                throw new FileNotFoundException("Raster file not found", filePath);

            using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
            if (ds == null)
                throw new Exception($"GDAL failed to open file: {Gdal.GetLastErrorMsg()}");

            int width = ds.RasterXSize;
            int height = ds.RasterYSize;
            int bands = ds.RasterCount;

            var meta = GdalMetadataReader.InspectMetadata(filePath);

            string cacheDir = GdalCacheManager.GetCacheDirectory();
            string cachePngName = GdalCacheManager.GetOverviewCacheFileName(filePath, meta.IsElevation, shaderMode, palette);
            string outPngPath = Path.Combine(cacheDir, cachePngName);

            // Instant cache hit: If overview already generated with valid size, return in < 1ms
            if (File.Exists(outPngPath) && new FileInfo(outPngPath).Length > 1000)
            {
                meta.PreviewImagePath = outPngPath;
                meta.PreviewUrl = $"http://cache.geostudio.local/{cachePngName}";
                return meta;
            }

            bool shouldRenderShader = meta.IsElevation || (!string.IsNullOrEmpty(shaderMode) && shaderMode != "none" && ds.RasterCount == 1);

            if (shouldRenderShader)
            {
                try
                {
                    int pW = previewWidth;
                    int pH = (int)Math.Max(1, Math.Round((double)height / width * pW));

                    var band = ds.GetRasterBand(1);
                    band.GetNoDataValue(out double noDataVal, out int hasNoData);

                    float[] floatBuf = new float[pW * pH];
                    band.ReadRaster(0, 0, width, height, floatBuf, pW, pH, 0, 0);

                    double[] gt = new double[6];
                    ds.GetGeoTransform(gt);

                    string projWkt = ds.GetProjectionRef();
                    bool isGeographic = false;
                    if (!string.IsNullOrWhiteSpace(projWkt))
                    {
                        using var srs = new SpatialReference(projWkt);
                        isGeographic = (srs.IsGeographic() == 1) && (srs.IsProjected() == 0);
                    }
                    else
                    {
                        isGeographic = Math.Abs(gt[1]) < 0.005;
                    }

                    double cellX = Math.Abs(gt[1]) * ((double)width / pW);
                    double cellY = Math.Abs(gt[5]) * ((double)height / pH);
                    if (isGeographic)
                    {
                        double midLat = gt[3] + (height / 2.0) * gt[5];
                        double latRad = midLat * Math.PI / 180.0;
                        cellX *= 111320.0 * Math.Max(0.1, Math.Cos(latRad));
                        cellY *= 111320.0;
                    }

                    double minElev = meta.MinElevation;
                    double maxElev = meta.MaxElevation;
                    if (minElev >= maxElev)
                    {
                        var stats = ElevationShadedRelief.GetElevationStats(ds);
                        minElev = stats.minElev;
                        maxElev = stats.maxElev;
                    }

                    byte[] bgra = ElevationShadedRelief.Render3DShadedReliefBgra(
                        floatBuf, pW, pH,
                        minElev, maxElev,
                        cellX, cellY,
                        hasNoData != 0 ? noDataVal : null,
                        palette,
                        shaderMode);

                    int stride = pW * 4;
                    var bmpSource = BitmapSource.Create(pW, pH, 96, 96, PixelFormats.Bgra32, null, bgra, stride);
                    bmpSource.Freeze();

                    string tmpPath = Path.Combine(cacheDir, $"tmp_{Guid.NewGuid():N}.png");
                    using (var fileStream = new FileStream(tmpPath, FileMode.Create, FileAccess.Write, FileShare.ReadWrite, 65536))
                    {
                        var encoder = new PngBitmapEncoder();
                        encoder.Frames.Add(BitmapFrame.Create(bmpSource));
                        encoder.Save(fileStream);
                        fileStream.Flush(true);
                    }
                    try { File.Move(tmpPath, outPngPath, overwrite: true); } catch { }
                    try { if (File.Exists(tmpPath)) File.Delete(tmpPath); } catch { }

                    GdalCacheManager.PruneCache();

                    meta.PreviewImagePath = outPngPath;
                    meta.PreviewUrl = $"http://cache.geostudio.local/{cachePngName}";
                    return meta;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"ELEVATION_EX: {ex.GetType().Name}: {ex.Message}\n{ex.StackTrace}");
                }
            }

            try
            {
                int pW = previewWidth;
                int pH = (int)Math.Max(1, Math.Round((double)height / width * pW));

                byte[] rData;
                byte[] gData;
                byte[] bData;
                byte[]? aData = bands >= 4 ? new byte[pW * pH] : null;

                int rBand = 1;
                int gBand = Math.Min(2, bands);
                int bBand = Math.Min(3, bands);

                var b1 = ds.GetRasterBand(1);
                int ovrCount = b1 != null ? b1.GetOverviewCount() : 0;
                int bestIdx = -1;
                if (ovrCount > 0)
                {
                    for (int o = 0; o < ovrCount; o++)
                    {
                        var ovr = b1!.GetOverview(o);
                        if (ovr != null && ovr.XSize >= pW)
                        {
                            bestIdx = o;
                        }
                    }
                    if (bestIdx == -1) bestIdx = 0;
                }

                if (bestIdx >= 0)
                {
                    rData = new byte[pW * pH];
                    gData = new byte[pW * pH];
                    bData = new byte[pW * pH];
                    if (aData != null) aData = new byte[pW * pH];

                    var ovrR = ds.GetRasterBand(rBand).GetOverview(bestIdx);
                    var ovrG = ds.GetRasterBand(gBand).GetOverview(bestIdx);
                    var ovrB = ds.GetRasterBand(bBand).GetOverview(bestIdx);
                    var ovrA = aData != null && bands >= 4 ? ds.GetRasterBand(4).GetOverview(bestIdx) : null;

                    ovrR.ReadRaster(0, 0, ovrR.XSize, ovrR.YSize, rData, pW, pH, 0, 0);
                    ovrG.ReadRaster(0, 0, ovrG.XSize, ovrG.YSize, gData, pW, pH, 0, 0);
                    ovrB.ReadRaster(0, 0, ovrB.XSize, ovrB.YSize, bData, pW, pH, 0, 0);
                    if (ovrA != null && aData != null)
                        ovrA.ReadRaster(0, 0, ovrA.XSize, ovrA.YSize, aData, pW, pH, 0, 0);
                }
                else
                {
                    rData = new byte[pW * pH];
                    gData = new byte[pW * pH];
                    bData = new byte[pW * pH];
                    if (aData != null) aData = new byte[pW * pH];

                    Parallel.Invoke(
                        () =>
                        {
                            using var ds1 = Gdal.Open(filePath, Access.GA_ReadOnly);
                            ds1.GetRasterBand(rBand).ReadRaster(0, 0, width, height, rData, pW, pH, 0, 0);
                        },
                        () =>
                        {
                            using var ds2 = Gdal.Open(filePath, Access.GA_ReadOnly);
                            ds2.GetRasterBand(gBand).ReadRaster(0, 0, width, height, gData, pW, pH, 0, 0);
                        },
                        () =>
                        {
                            using var ds3 = Gdal.Open(filePath, Access.GA_ReadOnly);
                            ds3.GetRasterBand(bBand).ReadRaster(0, 0, width, height, bData, pW, pH, 0, 0);
                        },
                        () =>
                        {
                            if (aData != null && bands >= 4)
                            {
                                using var ds4 = Gdal.Open(filePath, Access.GA_ReadOnly);
                                ds4.GetRasterBand(4).ReadRaster(0, 0, width, height, aData, pW, pH, 0, 0);
                            }
                        }
                    );
                }

                byte[] bgra = new byte[pW * pH * 4];
                unsafe
                {
                    fixed (byte* pBgra = bgra, pR = rData, pG = gData, pB = bData)
                    {
                        byte* pDst = pBgra;
                        byte* pEnd = pBgra + (pW * pH * 4);
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

                int stride = pW * 4;
                var bmpSource = BitmapSource.Create(pW, pH, 96, 96, PixelFormats.Bgra32, null, bgra, stride);
                bmpSource.Freeze();

                string tmpPathRgb = Path.Combine(cacheDir, $"tmp_{Guid.NewGuid():N}.png");
                using (var fileStream = new FileStream(tmpPathRgb, FileMode.Create, FileAccess.Write, FileShare.ReadWrite, 65536))
                {
                    var encoder = new PngBitmapEncoder();
                    encoder.Frames.Add(BitmapFrame.Create(bmpSource));
                    encoder.Save(fileStream);
                    fileStream.Flush(true);
                }
                try { File.Move(tmpPathRgb, outPngPath, overwrite: true); } catch { }
                try { if (File.Exists(tmpPathRgb)) File.Delete(tmpPathRgb); } catch { }

                GdalCacheManager.PruneCache();

                meta.PreviewImagePath = outPngPath;
                meta.PreviewUrl = $"http://cache.geostudio.local/{cachePngName}";
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Overview extraction warning: {ex.Message}");
            }

            return meta;
        }
    }
}
