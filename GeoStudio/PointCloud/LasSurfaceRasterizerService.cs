using System;
using System.IO;
using System.Collections.Generic;
using OSGeo.GDAL;
using OSGeo.OSR;
using GeoStudio.Raster;

namespace GeoStudio.PointCloud
{
    public static class LasSurfaceRasterizerService
    {
        public static string GenerateSurfaceRaster(string lasFilePath, int targetResolution = 4096, Action<int, string>? progress = null)
        {
            GdalRasterService.Initialize();

            if (!File.Exists(lasFilePath))
                throw new FileNotFoundException("Point cloud file not found", lasFilePath);

            progress?.Invoke(10, "Inspecting LiDAR header and coordinate system...");
            var header = LasPointCloudService.InspectLasHeader(lasFilePath);
            if (header.TotalPointCount == 0)
                throw new InvalidOperationException("Invalid or empty LAS point cloud file");

            double minX = header.MinX;
            double maxX = header.MaxX;
            double minY = header.MinY;
            double maxY = header.MaxY;

            SpatialReference? srcSrs = null;
            CoordinateTransformation? ct = null;
            try
            {
                if (!string.IsNullOrEmpty(header.CrsWkt))
                {
                    srcSrs = new SpatialReference(header.CrsWkt);
                    srcSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                }
                else if (header.EpsgCode.HasValue && header.EpsgCode.Value > 0)
                {
                    srcSrs = new SpatialReference("");
                    srcSrs.ImportFromEPSG(header.EpsgCode.Value);
                    srcSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                }
                else if (header.IsProjected || Math.Abs(minX) > 180 || Math.Abs(maxY) > 90)
                {
                    srcSrs = new SpatialReference("");
                    srcSrs.ImportFromEPSG(32643);
                    srcSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                }

                if (srcSrs != null)
                {
                    using var dstSrs = new SpatialReference("");
                    dstSrs.ImportFromEPSG(4326);
                    dstSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);

                    if (srcSrs.IsSame(dstSrs, null) == 0 && (srcSrs.IsProjected() == 1 || header.IsProjected))
                    {
                        ct = new CoordinateTransformation(srcSrs, dstSrs);
                        double[] pMin = new double[] { minX, minY, header.MinZ };
                        double[] pMax = new double[] { maxX, maxY, header.MaxZ };
                        ct.TransformPoint(pMin);
                        ct.TransformPoint(pMax);
                        minX = Math.Min(pMin[0], pMax[0]);
                        maxX = Math.Max(pMin[0], pMax[0]);
                        minY = Math.Min(pMin[1], pMax[1]);
                        maxY = Math.Max(pMin[1], pMax[1]);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"CRS setup warning in surface rasterizer: {ex.Message}");
            }

            double spanX = Math.Max(1e-9, maxX - minX);
            double spanY = Math.Max(1e-9, maxY - minY);
            double aspect = spanX / spanY;

            int gridW = aspect >= 1.0 ? targetResolution : Math.Max(512, (int)(targetResolution * aspect));
            int gridH = aspect >= 1.0 ? Math.Max(512, (int)(targetResolution / aspect)) : targetResolution;

            gridW = Math.Min(6144, Math.Max(512, gridW));
            gridH = Math.Min(6144, Math.Max(512, gridH));

            int totalPixels = gridW * gridH;
            byte[] rGrid = new byte[totalPixels];
            byte[] gGrid = new byte[totalPixels];
            byte[] bGrid = new byte[totalPixels];
            byte[] aGrid = new byte[totalPixels];
            float[] zGrid = new float[totalPixels];

            int recordLen = header.PointDataRecordLength;
            ulong total = header.TotalPointCount;
            int maxPointsToSample = 30000000;
            ulong step = Math.Max(1, total / (ulong)maxPointsToSample);

            int rgbOffset = -1;
            if (header.PointDataRecordFormat == 2 && recordLen >= 26) rgbOffset = 20;
            else if (header.PointDataRecordFormat == 3 && recordLen >= 34) rgbOffset = 28;
            else if ((header.PointDataRecordFormat == 7 || header.PointDataRecordFormat == 8) && recordLen >= 36) rgbOffset = 30;

            bool hasRgb = rgbOffset > 0;
            progress?.Invoke(25, "Streaming & binning LiDAR points into surface grid...");

            using (var fs = new FileStream(lasFilePath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304))
            {
                byte[] buf = new byte[recordLen];
                long startPos = (long)header.OffsetToPointData;

                float cMin = 0f;
                float cMax = 255f;
                if (hasRgb)
                {
                    var sampleVals = new List<ushort>(3000);
                    int sampleStep = Math.Max(1, (int)(total / 1000));
                    byte[] sBuf = new byte[recordLen];
                    for (int s = 0; s < 1000; s++)
                    {
                        long sPos = startPos + ((long)s * sampleStep * recordLen);
                        if (sPos + recordLen > fs.Length) break;
                        fs.Seek(sPos, SeekOrigin.Begin);
                        if (fs.Read(sBuf, 0, recordLen) < recordLen) break;
                        ushort sr = BitConverter.ToUInt16(sBuf, rgbOffset);
                        ushort sg = BitConverter.ToUInt16(sBuf, rgbOffset + 2);
                        ushort sb = BitConverter.ToUInt16(sBuf, rgbOffset + 4);
                        if (sr > 0 || sg > 0 || sb > 0)
                        {
                            sampleVals.Add(sr);
                            sampleVals.Add(sg);
                            sampleVals.Add(sb);
                        }
                    }

                    if (sampleVals.Count > 60)
                    {
                        sampleVals.Sort();
                        if (sampleVals[^1] > 255)
                        {
                            int idx1 = (int)(sampleVals.Count * 0.01);
                            int idx99 = (int)(sampleVals.Count * 0.99);
                            ushort p1 = sampleVals[Math.Clamp(idx1, 0, sampleVals.Count - 1)];
                            ushort p99 = sampleVals[Math.Clamp(idx99, 0, sampleVals.Count - 1)];
                            if (p99 - p1 > 100) { cMin = p1; cMax = p99; } else { cMin = 0; cMax = 65535; }
                        }
                    }
                }

                float cRange = Math.Max(1f, cMax - cMin);
                double[] ptBuf = new double[3];

                for (ulong i = 0; i < total; i += step)
                {
                    long pos = startPos + ((long)i * recordLen);
                    if (pos + recordLen > fs.Length) break;
                    fs.Seek(pos, SeekOrigin.Begin);
                    if (fs.Read(buf, 0, recordLen) < recordLen) break;

                    int rawX = BitConverter.ToInt32(buf, 0);
                    int rawY = BitConverter.ToInt32(buf, 4);
                    int rawZ = BitConverter.ToInt32(buf, 8);

                    double x = (rawX * header.ScaleX) + header.OffsetX;
                    double y = (rawY * header.ScaleY) + header.OffsetY;
                    float z = (float)((rawZ * header.ScaleZ) + header.OffsetZ);

                    if (ct != null)
                    {
                        ptBuf[0] = x; ptBuf[1] = y; ptBuf[2] = z;
                        ct.TransformPoint(ptBuf);
                        x = ptBuf[0]; y = ptBuf[1];
                    }

                    int px = (int)((x - minX) / spanX * (gridW - 1));
                    int py = (int)((maxY - y) / spanY * (gridH - 1));
                    if (px < 0 || px >= gridW || py < 0 || py >= gridH) continue;

                    byte r = 180, g = 180, b = 180;
                    if (hasRgb)
                    {
                        ushort r16 = BitConverter.ToUInt16(buf, rgbOffset);
                        ushort g16 = BitConverter.ToUInt16(buf, rgbOffset + 2);
                        ushort b16 = BitConverter.ToUInt16(buf, rgbOffset + 4);

                        if (cMax > 255f)
                        {
                            r = (byte)Math.Clamp((int)(((r16 - cMin) / cRange) * 255f), 0, 255);
                            g = (byte)Math.Clamp((int)(((g16 - cMin) / cRange) * 255f), 0, 255);
                            b = (byte)Math.Clamp((int)(((b16 - cMin) / cRange) * 255f), 0, 255);
                        }
                        else
                        {
                            r = (byte)Math.Clamp((int)r16, 0, 255);
                            g = (byte)Math.Clamp((int)g16, 0, 255);
                            b = (byte)Math.Clamp((int)b16, 0, 255);
                        }
                    }

                    int idx = py * gridW + px;
                    rGrid[idx] = r;
                    gGrid[idx] = g;
                    bGrid[idx] = b;
                    aGrid[idx] = 255;
                    zGrid[idx] = z;
                }
            }

            progress?.Invoke(65, "Infilling surface void holes with neighborhood interpolation...");
            byte[] aCopy = (byte[])aGrid.Clone();
            for (int pass = 0; pass < 2; pass++)
            {
                for (int y = 1; y < gridH - 1; y++)
                {
                    int row = y * gridW;
                    for (int x = 1; x < gridW - 1; x++)
                    {
                        int idx = row + x;
                        if (aCopy[idx] == 0)
                        {
                            int sumR = 0, sumG = 0, sumB = 0, count = 0;
                            if (aCopy[idx - 1] > 0) { sumR += rGrid[idx - 1]; sumG += gGrid[idx - 1]; sumB += bGrid[idx - 1]; count++; }
                            if (aCopy[idx + 1] > 0) { sumR += rGrid[idx + 1]; sumG += gGrid[idx + 1]; sumB += bGrid[idx + 1]; count++; }
                            if (aCopy[idx - gridW] > 0) { sumR += rGrid[idx - gridW]; sumG += gGrid[idx - gridW]; sumB += bGrid[idx - gridW]; count++; }
                            if (aCopy[idx + gridW] > 0) { sumR += rGrid[idx + gridW]; sumG += gGrid[idx + gridW]; sumB += bGrid[idx + gridW]; count++; }

                            if (count >= 2)
                            {
                                rGrid[idx] = (byte)(sumR / count);
                                gGrid[idx] = (byte)(sumG / count);
                                bGrid[idx] = (byte)(sumB / count);
                                aGrid[idx] = 255;
                            }
                        }
                    }
                }
                aCopy = (byte[])aGrid.Clone();
            }

            progress?.Invoke(85, "Writing GeoTIFF surface raster...");
            string outDir = Path.Combine(Path.GetTempPath(), "GeoStudio", "Surfaces");
            Directory.CreateDirectory(outDir);
            string baseName = Path.GetFileNameWithoutExtension(lasFilePath);
            string outTif = Path.Combine(outDir, $"{baseName}_surface.tif");

            if (File.Exists(outTif))
            {
                try { File.Delete(outTif); } catch { }
            }

            var drv = Gdal.GetDriverByName("GTiff");
            string[] options = new string[] { "COMPRESS=DEFLATE", "TILED=YES", "PREDICTOR=2" };
            using (var ds = drv.Create(outTif, gridW, gridH, 4, DataType.GDT_Byte, options))
            {
                double resX = spanX / gridW;
                double resY = spanY / gridH;
                double[] geoTransform = new double[] { minX, resX, 0, maxY, 0, -resY };
                ds.SetGeoTransform(geoTransform);

                using var srs = new SpatialReference("");
                srs.ImportFromEPSG(4326);
                srs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                srs.ExportToWkt(out string wkt, null);
                ds.SetProjection(wkt);

                ds.GetRasterBand(1).WriteRaster(0, 0, gridW, gridH, rGrid, gridW, gridH, 0, 0);
                ds.GetRasterBand(2).WriteRaster(0, 0, gridW, gridH, gGrid, gridW, gridH, 0, 0);
                ds.GetRasterBand(3).WriteRaster(0, 0, gridW, gridH, bGrid, gridW, gridH, 0, 0);
                ds.GetRasterBand(4).WriteRaster(0, 0, gridW, gridH, aGrid, gridW, gridH, 0, 0);
                ds.FlushCache();
            }

            progress?.Invoke(100, "Surface generation complete!");
            return outTif;
        }
    }
}
