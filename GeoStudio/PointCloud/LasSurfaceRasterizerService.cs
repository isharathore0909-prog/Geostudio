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

        public static string GenerateDtmRaster(string lasFilePath, int targetResolution = 2048, Action<int, string>? progress = null)
        {
            GdalRasterService.Initialize();
            if (!File.Exists(lasFilePath))
                throw new FileNotFoundException("Point cloud file not found", lasFilePath);

            progress?.Invoke(10, "Inspecting LiDAR ground returns for Bare-Earth DTM...");
            string actualPath = LasPointCloudService.EnsureUncompressedLas(lasFilePath, (p, m) => progress?.Invoke(p, m));
            var header = LasPointCloudService.InspectLasHeader(actualPath);
            if (header.TotalPointCount == 0)
                throw new InvalidOperationException("Invalid or empty LAS point cloud file");

            double minX = header.MinX, maxX = header.MaxX;
            double minY = header.MinY, maxY = header.MaxY;

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
            catch { }

            double spanX = Math.Max(1e-9, maxX - minX);
            double spanY = Math.Max(1e-9, maxY - minY);
            double aspect = spanX / spanY;

            int gridW = aspect >= 1.0 ? targetResolution : Math.Max(256, (int)(targetResolution * aspect));
            int gridH = aspect >= 1.0 ? Math.Max(256, (int)(targetResolution / aspect)) : targetResolution;
            gridW = Math.Min(4096, Math.Max(256, gridW));
            gridH = Math.Min(4096, Math.Max(256, gridH));

            int totalPixels = gridW * gridH;
            float[] dtmGrid = new float[totalPixels];
            bool[] validGrid = new bool[totalPixels];
            Array.Fill(dtmGrid, float.MaxValue);

            int recordLen = header.PointDataRecordLength;
            ulong total = header.TotalPointCount;
            ulong step = Math.Max(1, total / 20_000_000UL);

            // Pre-scan a sample to detect if the point cloud contains ASPRS Ground (Class 2 / Class 8)
            bool hasGroundClass = false;
            ulong checkCount = Math.Min(total, 50_000UL);
            ulong checkStep = Math.Max(1, total / checkCount);
            using (var fsCheck = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 1048576))
            {
                byte[] checkBuf = new byte[recordLen];
                long startPos = (long)header.OffsetToPointData;
                int groundCount = 0;
                for (ulong i = 0; i < total && groundCount < 30; i += checkStep)
                {
                    long pos = startPos + ((long)i * recordLen);
                    if (pos + recordLen > fsCheck.Length) break;
                    fsCheck.Seek(pos, SeekOrigin.Begin);
                    if (fsCheck.Read(checkBuf, 0, recordLen) < recordLen) break;
                    byte c = header.PointDataRecordFormat >= 6 ? checkBuf[16] : (byte)(checkBuf[15] & 0x1F);
                    if (c == 2 || c == 8) groundCount++;
                }
                hasGroundClass = groundCount >= 10;
            }

            progress?.Invoke(30, hasGroundClass
                ? "Extracting ASPRS Class 2 Ground returns for bare-earth DTM..."
                : "Filtering minimum returns for bare-earth terrain surface...");

            using (var fs = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304))
            {
                byte[] buf = new byte[recordLen];
                long startPos = (long)header.OffsetToPointData;
                double[] ptBuf = new double[3];

                for (ulong i = 0; i < total; i += step)
                {
                    long pos = startPos + ((long)i * recordLen);
                    if (pos + recordLen > fs.Length) break;
                    fs.Seek(pos, SeekOrigin.Begin);
                    if (fs.Read(buf, 0, recordLen) < recordLen) break;

                    byte cls = header.PointDataRecordFormat >= 6 ? buf[16] : (byte)(buf[15] & 0x1F);

                    // Reject noise (ASPRS Class 7 = Low Noise, Class 18 = High Noise)
                    if (cls == 7 || cls == 18) continue;

                    if (hasGroundClass)
                    {
                        // STRICT ASPRS Ground filtering: only Class 2 (Ground) and Class 8 (Model Key Point)
                        // This prevents canopy, bushes, roofs (Class 1, 3, 4, 5, 6) from inflating the DTM!
                        if (cls != 2 && cls != 8) continue;
                    }
                    else
                    {
                        // Unclassified: skip vegetation and building classes if labeled
                        if (cls > 1 && cls != 2 && cls != 8) continue;
                    }

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

                    int idx = py * gridW + px;
                    if (z < dtmGrid[idx])
                    {
                        dtmGrid[idx] = z;
                        validGrid[idx] = true;
                    }
                }
            }

            // 1. Establish interior bounding envelope of measured ground points (prevents bleeding into outer blank corners)
            int[] minX_row = new int[gridH];
            int[] maxX_row = new int[gridH];
            Array.Fill(minX_row, gridW);
            Array.Fill(maxX_row, -1);

            int[] minY_col = new int[gridW];
            int[] maxY_col = new int[gridW];
            Array.Fill(minY_col, gridH);
            Array.Fill(maxY_col, -1);

            for (int y = 0; y < gridH; y++)
            {
                int row = y * gridW;
                for (int x = 0; x < gridW; x++)
                {
                    if (validGrid[row + x])
                    {
                        if (x < minX_row[y]) minX_row[y] = x;
                        if (x > maxX_row[y]) maxX_row[y] = x;
                        if (y < minY_col[x]) minY_col[x] = y;
                        if (y > maxY_col[x]) maxY_col[x] = y;
                    }
                }
            }

            // 2. Infill void holes strictly bounded inside the surveyed footprint using double-buffered interpolation.
            // Double-buffering prevents in-place directional cascading (which causes diagonal streaks and border smears).
            progress?.Invoke(70, "Infilling bare-earth gaps under canopy and buildings...");
            for (int pass = 0; pass < 25; pass++)
            {
                bool filledAny = false;
                bool[] readValid = (bool[])validGrid.Clone();
                float[] readDtm = (float[])dtmGrid.Clone();

                for (int y = 1; y < gridH - 1; y++)
                {
                    int rowMinX = Math.Max(1, minX_row[y]);
                    int rowMaxX = Math.Min(gridW - 2, maxX_row[y]);
                    if (rowMinX > rowMaxX) continue;

                    int row = y * gridW;
                    for (int x = rowMinX; x <= rowMaxX; x++)
                    {
                        if (y < minY_col[x] || y > maxY_col[x]) continue;

                        int idx = row + x;
                        if (!readValid[idx])
                        {
                            float sumZ = 0; int count = 0;
                            if (readValid[idx - 1]) { sumZ += readDtm[idx - 1]; count++; }
                            if (readValid[idx + 1]) { sumZ += readDtm[idx + 1]; count++; }
                            if (readValid[idx - gridW]) { sumZ += readDtm[idx - gridW]; count++; }
                            if (readValid[idx + gridW]) { sumZ += readDtm[idx + gridW]; count++; }

                            // Require at least 2 neighbors to smoothly bridge interior gaps without expanding outward
                            if (count >= 2)
                            {
                                dtmGrid[idx] = sumZ / count;
                                validGrid[idx] = true;
                                filledAny = true;
                            }
                        }
                    }
                }
                if (!filledAny) break;
            }

            // CRITICAL: Out-of-bounds / unmeasured cells MUST be set to NoData (-9999.0f), NEVER header.MinZ!
            // Setting this to NoData keeps the background 100% transparent and preserves accurate terrain elevation stretch.
            for (int i = 0; i < totalPixels; i++)
            {
                if (!validGrid[i]) dtmGrid[i] = -9999.0f;
            }

            progress?.Invoke(85, "Writing high-resolution Bare-Earth DTM GeoTIFF...");
            string outDir = Path.Combine(Path.GetTempPath(), "GeoStudio", "Surfaces");
            Directory.CreateDirectory(outDir);
            string baseName = Path.GetFileNameWithoutExtension(lasFilePath);
            string outTif = Path.Combine(outDir, $"{baseName}_DTM.tif");
            if (File.Exists(outTif)) { try { File.Delete(outTif); } catch { } }

            var drv = Gdal.GetDriverByName("GTiff");
            string[] options = new string[] { "COMPRESS=DEFLATE", "TILED=YES", "PREDICTOR=3" };
            using (var ds = drv.Create(outTif, gridW, gridH, 1, DataType.GDT_Float32, options))
            {
                double resX = spanX / gridW;
                double resY = spanY / gridH;
                ds.SetGeoTransform(new double[] { minX, resX, 0, maxY, 0, -resY });

                using var srs = new SpatialReference("");
                srs.ImportFromEPSG(4326);
                srs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                srs.ExportToWkt(out string wkt, null);
                ds.SetProjection(wkt);

                var band = ds.GetRasterBand(1);
                band.SetNoDataValue(-9999.0);
                band.WriteRaster(0, 0, gridW, gridH, dtmGrid, gridW, gridH, 0, 0);
                band.FlushCache();
                ds.FlushCache();
            }

            progress?.Invoke(100, "Bare-Earth DTM generation complete!");
            return outTif;
        }

        public static string GenerateChmRaster(string lasFilePath, int targetResolution = 2048, Action<int, string>? progress = null)
        {
            GdalRasterService.Initialize();
            if (!File.Exists(lasFilePath))
                throw new FileNotFoundException("Point cloud file not found", lasFilePath);

            progress?.Invoke(10, "Extracting DSM and DTM surfaces for Canopy Height Model...");
            string actualPath = LasPointCloudService.EnsureUncompressedLas(lasFilePath, (p, m) => progress?.Invoke(p, m));
            var header = LasPointCloudService.InspectLasHeader(actualPath);
            if (header.TotalPointCount == 0)
                throw new InvalidOperationException("Invalid or empty LAS point cloud file");

            double minX = header.MinX, maxX = header.MaxX;
            double minY = header.MinY, maxY = header.MaxY;

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
            catch { }

            double spanX = Math.Max(1e-9, maxX - minX);
            double spanY = Math.Max(1e-9, maxY - minY);
            double aspect = spanX / spanY;

            int gridW = aspect >= 1.0 ? targetResolution : Math.Max(256, (int)(targetResolution * aspect));
            int gridH = aspect >= 1.0 ? Math.Max(256, (int)(targetResolution / aspect)) : targetResolution;
            gridW = Math.Min(4096, Math.Max(256, gridW));
            gridH = Math.Min(4096, Math.Max(256, gridH));

            int totalPixels = gridW * gridH;
            float[] dsmGrid = new float[totalPixels];
            float[] dtmGrid = new float[totalPixels];
            bool[] validDsm = new bool[totalPixels];
            bool[] validDtm = new bool[totalPixels];
            Array.Fill(dsmGrid, float.MinValue);
            Array.Fill(dtmGrid, float.MaxValue);

            int recordLen = header.PointDataRecordLength;
            ulong total = header.TotalPointCount;
            ulong step = Math.Max(1, total / 20_000_000UL);

            progress?.Invoke(30, "Calculating tree crown DSM and bare-earth DTM heights...");
            using (var fs = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304))
            {
                byte[] buf = new byte[recordLen];
                long startPos = (long)header.OffsetToPointData;
                double[] ptBuf = new double[3];

                for (ulong i = 0; i < total; i += step)
                {
                    long pos = startPos + ((long)i * recordLen);
                    if (pos + recordLen > fs.Length) break;
                    fs.Seek(pos, SeekOrigin.Begin);
                    if (fs.Read(buf, 0, recordLen) < recordLen) break;

                    byte cls = header.PointDataRecordFormat >= 6 ? buf[16] : (byte)(buf[15] & 0x1F);
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

                    int idx = py * gridW + px;
                    if (z > dsmGrid[idx]) { dsmGrid[idx] = z; validDsm[idx] = true; }
                    if (cls == 2 || z < dtmGrid[idx]) { dtmGrid[idx] = z; validDtm[idx] = true; }
                }
            }

            // Infill gaps
            for (int pass = 0; pass < 2; pass++)
            {
                for (int y = 1; y < gridH - 1; y++)
                {
                    int row = y * gridW;
                    for (int x = 1; x < gridW - 1; x++)
                    {
                        int idx = row + x;
                        if (!validDtm[idx] && validDtm[idx - 1] && validDtm[idx + 1])
                        {
                            dtmGrid[idx] = (dtmGrid[idx - 1] + dtmGrid[idx + 1]) * 0.5f;
                            validDtm[idx] = true;
                        }
                        if (!validDsm[idx] && validDsm[idx - 1] && validDsm[idx + 1])
                        {
                            dsmGrid[idx] = (dsmGrid[idx - 1] + dsmGrid[idx + 1]) * 0.5f;
                            validDsm[idx] = true;
                        }
                    }
                }
            }

            progress?.Invoke(70, "Computing Canopy Height Model: CHM = DSM - DTM...");
            float[] chmGrid = new float[totalPixels];
            for (int i = 0; i < totalPixels; i++)
            {
                if (validDsm[i] && validDtm[i])
                {
                    float chm = dsmGrid[i] - dtmGrid[i];
                    chmGrid[i] = Math.Clamp(chm, 0f, 150f);
                }
                else
                {
                    chmGrid[i] = -9999.0f;
                }
            }

            progress?.Invoke(85, "Writing Canopy Height Model (CHM) GeoTIFF...");
            string outDir = Path.Combine(Path.GetTempPath(), "GeoStudio", "Surfaces");
            Directory.CreateDirectory(outDir);
            string baseName = Path.GetFileNameWithoutExtension(lasFilePath);
            string outTif = Path.Combine(outDir, $"{baseName}_CHM.tif");
            if (File.Exists(outTif)) { try { File.Delete(outTif); } catch { } }

            var drv = Gdal.GetDriverByName("GTiff");
            string[] options = new string[] { "COMPRESS=DEFLATE", "TILED=YES", "PREDICTOR=3" };
            using (var ds = drv.Create(outTif, gridW, gridH, 1, DataType.GDT_Float32, options))
            {
                double resX = spanX / gridW;
                double resY = spanY / gridH;
                ds.SetGeoTransform(new double[] { minX, resX, 0, maxY, 0, -resY });

                using var srs = new SpatialReference("");
                srs.ImportFromEPSG(4326);
                srs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                srs.ExportToWkt(out string wkt, null);
                ds.SetProjection(wkt);

                var band = ds.GetRasterBand(1);
                band.SetNoDataValue(-9999.0);
                band.WriteRaster(0, 0, gridW, gridH, chmGrid, gridW, gridH, 0, 0);
                band.FlushCache();
                ds.FlushCache();
            }

            progress?.Invoke(100, "Canopy Height Model (CHM) complete!");
            return outTif;
        }

        public static string ThinLasFile(string lasFilePath, string outFilePath, int step = 2, Action<int, string>? progress = null)
        {
            if (!File.Exists(lasFilePath)) throw new FileNotFoundException("File not found", lasFilePath);
            step = Math.Max(2, step);

            progress?.Invoke(15, $"Thinning point cloud by decimation factor {step}...");
            string actualPath = LasPointCloudService.EnsureUncompressedLas(lasFilePath, (p, m) => progress?.Invoke(p, m));
            var header = LasPointCloudService.InspectLasHeader(actualPath);

            using var fsIn = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304);
            using var fsOut = new FileStream(outFilePath, FileMode.Create, FileAccess.Write, FileShare.None, 4194304);

            byte[] headerBuf = new byte[header.OffsetToPointData];
            fsIn.Read(headerBuf, 0, headerBuf.Length);

            ulong origTotal = header.TotalPointCount;
            ulong thinnedTotal = origTotal / (ulong)step;

            // Update point count in LAS header
            if (header.VersionMajor == 1 && header.VersionMinor >= 4 && headerBuf.Length >= 255)
            {
                byte[] thinnedBytes = BitConverter.GetBytes(thinnedTotal);
                Array.Copy(thinnedBytes, 0, headerBuf, 247, 8);
            }
            byte[] legacyBytes = BitConverter.GetBytes((uint)Math.Min((ulong)uint.MaxValue, thinnedTotal));
            Array.Copy(legacyBytes, 0, headerBuf, 107, 4);

            fsOut.Write(headerBuf, 0, headerBuf.Length);

            int recLen = header.PointDataRecordLength;
            byte[] recBuf = new byte[recLen];
            long startPos = (long)header.OffsetToPointData;
            ulong written = 0;

            for (ulong i = 0; i < origTotal; i += (ulong)step)
            {
                long pos = startPos + ((long)i * recLen);
                if (pos + recLen > fsIn.Length) break;
                fsIn.Seek(pos, SeekOrigin.Begin);
                int n = fsIn.Read(recBuf, 0, recLen);
                if (n < recLen) break;

                fsOut.Write(recBuf, 0, recLen);
                written++;
                if (written % 50000 == 0 && thinnedTotal > 0)
                {
                    progress?.Invoke(15 + (int)((written * 80) / thinnedTotal), $"Writing decimated points ({written:N0}/{thinnedTotal:N0})...");
                }
            }

            fsOut.Flush();
            progress?.Invoke(100, $"Point cloud decimation complete: {written:N0} points written.");
            return outFilePath;
        }

        public static (string outPath, ulong writtenCount) ExportClassifiedLas(
            string lasFilePath,
            string outFilePath,
            ISet<byte> allowedClasses,
            Action<int, string>? progress = null)
        {
            if (!File.Exists(lasFilePath)) throw new FileNotFoundException("Point cloud file not found", lasFilePath);
            if (allowedClasses == null || allowedClasses.Count == 0)
                throw new InvalidOperationException("At least one classification must be selected for export.");

            progress?.Invoke(5, "Preparing point cloud for class filtering...");
            string actualPath = LasPointCloudService.EnsureUncompressedLas(lasFilePath, (p, m) => progress?.Invoke(p, m));
            var header = LasPointCloudService.InspectLasHeader(actualPath);

            string ext = Path.GetExtension(outFilePath).ToLowerInvariant();
            bool isCsv = ext == ".csv" || ext == ".txt" || ext == ".xyz";

            int recLen = header.PointDataRecordLength;
            ulong origTotal = header.TotalPointCount;
            long startPos = (long)header.OffsetToPointData;
            int fmt = header.PointDataRecordFormat;

            using var fsIn = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304);

            if (isCsv)
            {
                using var sw = new StreamWriter(outFilePath, false, System.Text.Encoding.UTF8, 65536);
                sw.WriteLine("X,Y,Z,Intensity,Classification,ReturnNumber");
                byte[] recBuf = new byte[recLen];
                ulong written = 0;

                for (ulong i = 0; i < origTotal; i++)
                {
                    long pos = startPos + ((long)i * recLen);
                    if (pos + recLen > fsIn.Length) break;
                    fsIn.Seek(pos, SeekOrigin.Begin);
                    if (fsIn.Read(recBuf, 0, recLen) < recLen) break;

                    byte cls = fmt >= 6 ? recBuf[16] : (byte)(recBuf[15] & 0x1F);
                    if (!allowedClasses.Contains(cls)) continue;

                    int rawX = BitConverter.ToInt32(recBuf, 0);
                    int rawY = BitConverter.ToInt32(recBuf, 4);
                    int rawZ = BitConverter.ToInt32(recBuf, 8);
                    ushort intensity = BitConverter.ToUInt16(recBuf, 12);
                    byte retByte = recBuf[14];
                    byte rn = fmt >= 6 ? (byte)(retByte & 0x0F) : (byte)(retByte & 0x07);

                    double x = (rawX * header.ScaleX) + header.OffsetX;
                    double y = (rawY * header.ScaleY) + header.OffsetY;
                    double z = (rawZ * header.ScaleZ) + header.OffsetZ;

                    sw.WriteLine($"{x:F3},{y:F3},{z:F3},{intensity},{cls},{rn}");
                    written++;
                    if (written % 50000 == 0 && origTotal > 0)
                    {
                        progress?.Invoke(10 + (int)((i * 85) / origTotal), $"Exporting points ({written:N0} selected)...");
                    }
                }
                progress?.Invoke(100, $"Export complete: {written:N0} points saved to text file.");
                return (outFilePath, written);
            }
            else
            {
                // Standard ASPRS Binary LAS Export
                using var fsOut = new FileStream(outFilePath, FileMode.Create, FileAccess.ReadWrite, FileShare.None, 4194304);

                // Copy original header buffer & all VLRs
                byte[] headerBuf = new byte[header.OffsetToPointData];
                fsIn.Seek(0, SeekOrigin.Begin);
                fsIn.Read(headerBuf, 0, headerBuf.Length);
                fsOut.Write(headerBuf, 0, headerBuf.Length);

                byte[] recBuf = new byte[recLen];
                ulong written = 0;

                double minX = double.MaxValue, maxX = double.MinValue;
                double minY = double.MaxValue, maxY = double.MinValue;
                double minZ = double.MaxValue, maxZ = double.MinValue;

                for (ulong i = 0; i < origTotal; i++)
                {
                    long pos = startPos + ((long)i * recLen);
                    if (pos + recLen > fsIn.Length) break;
                    fsIn.Seek(pos, SeekOrigin.Begin);
                    if (fsIn.Read(recBuf, 0, recLen) < recLen) break;

                    byte cls = fmt >= 6 ? recBuf[16] : (byte)(recBuf[15] & 0x1F);
                    if (!allowedClasses.Contains(cls)) continue;

                    int rawX = BitConverter.ToInt32(recBuf, 0);
                    int rawY = BitConverter.ToInt32(recBuf, 4);
                    int rawZ = BitConverter.ToInt32(recBuf, 8);
                    double x = (rawX * header.ScaleX) + header.OffsetX;
                    double y = (rawY * header.ScaleY) + header.OffsetY;
                    double z = (rawZ * header.ScaleZ) + header.OffsetZ;

                    if (x < minX) minX = x; if (x > maxX) maxX = x;
                    if (y < minY) minY = y; if (y > maxY) maxY = y;
                    if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;

                    fsOut.Write(recBuf, 0, recLen);
                    written++;

                    if (written % 50000 == 0 && origTotal > 0)
                    {
                        progress?.Invoke(10 + (int)((i * 80) / origTotal), $"Filtering & writing ASPRS points ({written:N0} selected)...");
                    }
                }

                // Update point count in LAS header
                fsOut.Seek(107, SeekOrigin.Begin);
                fsOut.Write(BitConverter.GetBytes((uint)Math.Min((ulong)uint.MaxValue, written)), 0, 4);

                if (header.VersionMajor == 1 && header.VersionMinor >= 4 && fsOut.Length >= 255)
                {
                    fsOut.Seek(247, SeekOrigin.Begin);
                    fsOut.Write(BitConverter.GetBytes(written), 0, 8);
                }

                if (written > 0)
                {
                    fsOut.Seek(179, SeekOrigin.Begin);
                    fsOut.Write(BitConverter.GetBytes(maxX), 0, 8);
                    fsOut.Write(BitConverter.GetBytes(minX), 0, 8);
                    fsOut.Write(BitConverter.GetBytes(maxY), 0, 8);
                    fsOut.Write(BitConverter.GetBytes(minY), 0, 8);
                    fsOut.Write(BitConverter.GetBytes(maxZ), 0, 8);
                    fsOut.Write(BitConverter.GetBytes(minZ), 0, 8);
                }

                fsOut.Flush();
                progress?.Invoke(100, $"ASPRS LAS export complete: {written:N0} points written.");
                return (outFilePath, written);
            }
        }

        public static (string outPath, ulong writtenCount) ExportClassifiedRaster(
            string lasFilePath,
            string outFilePath,
            ISet<byte> allowedClasses,
            string format,
            Action<int, string>? progress = null)
        {
            if (!File.Exists(lasFilePath)) throw new FileNotFoundException("Point cloud file not found", lasFilePath);
            if (allowedClasses == null || allowedClasses.Count == 0)
                throw new InvalidOperationException("At least one classification must be selected for export.");

            GdalRasterService.Initialize();
            progress?.Invoke(5, "Preparing point cloud for raster export...");
            string actualPath = LasPointCloudService.EnsureUncompressedLas(lasFilePath, (p, m) => progress?.Invoke(p, m));
            var header = LasPointCloudService.InspectLasHeader(actualPath);

            double minX = header.MinX;
            double maxX = header.MaxX;
            double minY = header.MinY;
            double maxY = header.MaxY;

            SpatialReference? srcSrs = null;
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
            }
            catch { }

            double spanX = Math.Max(1e-9, maxX - minX);
            double spanY = Math.Max(1e-9, maxY - minY);
            double aspect = spanX / spanY;

            int targetResolution = 2048;
            int gridW = aspect >= 1.0 ? targetResolution : Math.Max(256, (int)(targetResolution * aspect));
            int gridH = aspect >= 1.0 ? Math.Max(256, (int)(targetResolution / aspect)) : targetResolution;
            gridW = Math.Min(4096, Math.Max(256, gridW));
            gridH = Math.Min(4096, Math.Max(256, gridH));

            double cellX = spanX / gridW;
            double cellY = spanY / gridH;

            int totalPixels = gridW * gridH;
            bool isTiff = format.ToLowerInvariant().Contains("tif");

            float[] elevGrid = isTiff ? new float[totalPixels] : Array.Empty<float>();
            if (isTiff) Array.Fill(elevGrid, -9999.0f);

            byte[] rgba = !isTiff ? new byte[totalPixels * 4] : Array.Empty<byte>();

            int recLen = header.PointDataRecordLength;
            ulong origTotal = header.TotalPointCount;
            long startPos = (long)header.OffsetToPointData;
            int fmt = header.PointDataRecordFormat;

            using var fsIn = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304);
            byte[] recBuf = new byte[recLen];
            ulong written = 0;

            progress?.Invoke(20, "Rasterizing selected LiDAR classes...");

            for (ulong i = 0; i < origTotal; i++)
            {
                long pos = startPos + ((long)i * recLen);
                if (pos + recLen > fsIn.Length) break;
                fsIn.Seek(pos, SeekOrigin.Begin);
                if (fsIn.Read(recBuf, 0, recLen) < recLen) break;

                byte cls = fmt >= 6 ? recBuf[16] : (byte)(recBuf[15] & 0x1F);
                if (!allowedClasses.Contains(cls)) continue;

                int rawX = BitConverter.ToInt32(recBuf, 0);
                int rawY = BitConverter.ToInt32(recBuf, 4);
                int rawZ = BitConverter.ToInt32(recBuf, 8);
                double x = (rawX * header.ScaleX) + header.OffsetX;
                double y = (rawY * header.ScaleY) + header.OffsetY;
                double z = (rawZ * header.ScaleZ) + header.OffsetZ;

                int col = (int)((x - minX) / cellX);
                int row = (int)((maxY - y) / cellY);

                if (col >= 0 && col < gridW && row >= 0 && row < gridH)
                {
                    int idx = row * gridW + col;
                    if (isTiff)
                    {
                        if (elevGrid[idx] == -9999.0f || (float)z > elevGrid[idx])
                        {
                            elevGrid[idx] = (float)z;
                        }
                    }
                    else
                    {
                        var meta = LasPointCloudService.GetClassMeta(cls);
                        byte r = 128, g = 128, b = 128;
                        try
                        {
                            var c = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(meta.ColorHex);
                            r = c.R; g = c.G; b = c.B;
                        }
                        catch { }

                        int pixelOffset = idx * 4;
                        rgba[pixelOffset + 0] = b; // Blue
                        rgba[pixelOffset + 1] = g; // Green
                        rgba[pixelOffset + 2] = r; // Red
                        rgba[pixelOffset + 3] = 255; // Alpha
                    }
                }

                written++;
                if (written % 100000 == 0 && origTotal > 0)
                {
                    progress?.Invoke(20 + (int)((i * 65) / origTotal), $"Rasterizing points ({written:N0} processed)...");
                }
            }

            progress?.Invoke(88, $"Encoding {format.ToUpperInvariant()} raster file...");

            if (isTiff)
            {
                var drv = Gdal.GetDriverByName("GTiff");
                string[] options = new string[] { "COMPRESS=DEFLATE", "TILED=YES", "PREDICTOR=3" };
                using var ds = drv.Create(outFilePath, gridW, gridH, 1, DataType.GDT_Float32, options);
                double[] gt = new double[] { minX, cellX, 0, maxY, 0, -cellY };
                ds.SetGeoTransform(gt);
                if (srcSrs != null)
                {
                    srcSrs.ExportToWkt(out string wkt, null);
                    ds.SetProjection(wkt);
                }
                var band = ds.GetRasterBand(1);
                band.SetNoDataValue(-9999.0);
                band.WriteRaster(0, 0, gridW, gridH, elevGrid, gridW, gridH, 0, 0);
                band.FlushCache();
                ds.FlushCache();
            }
            else
            {
                var bmp = System.Windows.Media.Imaging.BitmapSource.Create(
                    gridW, gridH, 96, 96,
                    System.Windows.Media.PixelFormats.Bgra32,
                    null, rgba, gridW * 4);

                using var fsOut = new FileStream(outFilePath, FileMode.Create, FileAccess.Write);
                var encoder = new System.Windows.Media.Imaging.PngBitmapEncoder();
                encoder.Frames.Add(System.Windows.Media.Imaging.BitmapFrame.Create(bmp));
                encoder.Save(fsOut);
            }

            progress?.Invoke(100, $"Raster export complete: {Path.GetFileName(outFilePath)} saved ({written:N0} points).");
            return (outFilePath, written);
        }
    }
}
