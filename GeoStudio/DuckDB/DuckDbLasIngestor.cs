using System;
using System.IO;
using System.Collections.Generic;
using DuckDB.NET.Data;
using OSGeo.OSR;
using GeoStudio.Raster;

namespace GeoStudio.DuckDB
{
    internal static class DuckDbLasIngestor
    {
        public static PointCloudStats IngestLasFile(string filePath, Action<int>? progressCallback = null, int maxPointsToIngest = 1000000)
        {
            DuckDbConnectionManager.Initialize();

            string actualPath = LasPointCloudService.EnsureUncompressedLas(filePath, (p, m) => progressCallback?.Invoke(p));
            var header = LasPointCloudService.InspectLasHeader(actualPath);
            if (header.TotalPointCount == 0) return new PointCloudStats();

            lock (DuckDbConnectionManager.DbLock)
            {
                var conn = DuckDbConnectionManager.Connection;
                if (conn == null) return new PointCloudStats();

                DuckDbConnectionManager.RecreateTable();

                int recordLen = header.PointDataRecordLength;
                ulong total = header.TotalPointCount;

                var fi = new FileInfo(actualPath);
                ulong availableRecords = (ulong)((fi.Length - header.OffsetToPointData) / recordLen);
                if (total == 0 || total > availableRecords) total = availableRecords;

                ulong step = Math.Max(1, total / (ulong)maxPointsToIngest);

                int rgbOffset = -1;
                if (header.PointDataRecordFormat == 2 && recordLen >= 26) rgbOffset = 20;
                else if (header.PointDataRecordFormat == 3 && recordLen >= 34) rgbOffset = 28;
                else if ((header.PointDataRecordFormat == 7 || header.PointDataRecordFormat == 8) && recordLen >= 36) rgbOffset = 30;

                bool hasRgb = rgbOffset > 0;

                SpatialReference? srcSrs = null;
                CoordinateTransformation? ct = null;
                try
                {
                    GdalRasterService.Initialize();
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
                    else if (header.IsProjected || Math.Abs(header.MinX) > 180 || Math.Abs(header.MaxY) > 90)
                    {
                        srcSrs = new SpatialReference("");
                        srcSrs.ImportFromEPSG(32643);
                        srcSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                    }
                    else
                    {
                        srcSrs = new SpatialReference("");
                        srcSrs.ImportFromEPSG(4326);
                        srcSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);
                    }

                    if (srcSrs != null)
                    {
                        using var dstSrs = new SpatialReference("");
                        dstSrs.ImportFromEPSG(3857);
                        dstSrs.SetAxisMappingStrategy(AxisMappingStrategy.OAMS_TRADITIONAL_GIS_ORDER);

                        if (srcSrs.IsSame(dstSrs, null) == 0)
                        {
                            ct = new CoordinateTransformation(srcSrs, dstSrs);
                        }
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"CRS setup warning: {ex.Message}");
                }

                using (var fs = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304))
                {
                    float cMin = 0f;
                    float cMax = 255f;
                    if (hasRgb)
                    {
                        var sampleVals = new List<ushort>(3000);
                        int sampleStep = Math.Max(1, (int)(total / 1000));
                        byte[] sBuf = new byte[recordLen];
                        for (int s = 0; s < 1000; s++)
                        {
                            long sPos = (long)header.OffsetToPointData + ((long)s * sampleStep * recordLen);
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
                            ushort pMax = sampleVals[^1];
                            if (pMax > 255)
                            {
                                int idx1 = (int)(sampleVals.Count * 0.01);
                                int idx99 = (int)(sampleVals.Count * 0.99);
                                ushort p1 = sampleVals[Math.Clamp(idx1, 0, sampleVals.Count - 1)];
                                ushort p99 = sampleVals[Math.Clamp(idx99, 0, sampleVals.Count - 1)];
                                if (p99 - p1 > 100)
                                {
                                    cMin = p1;
                                    cMax = p99;
                                }
                                else
                                {
                                    cMin = 0;
                                    cMax = 65535;
                                }
                            }
                        }
                    }

                    using (var appender = conn.CreateAppender("pointcloud"))
                    {
                        double[] ptBuf = new double[3];
                        float cRange = Math.Max(1f, cMax - cMin);

                        if (step == 1)
                        {
                            fs.Seek(header.OffsetToPointData, SeekOrigin.Begin);
                            int batchPoints = 32768;
                            byte[] chunkBuf = new byte[batchPoints * recordLen];
                            ulong pointsRead = 0;
                            while (pointsRead < total)
                            {
                                int toRead = (int)Math.Min((ulong)batchPoints, total - pointsRead);
                                int bytesToRead = toRead * recordLen;
                                int bytesRead = 0;
                                while (bytesRead < bytesToRead)
                                {
                                    int n = fs.Read(chunkBuf, bytesRead, bytesToRead - bytesRead);
                                    if (n <= 0) break;
                                    bytesRead += n;
                                }
                                int recordsInChunk = bytesRead / recordLen;
                                if (recordsInChunk == 0) break;

                                for (int k = 0; k < recordsInChunk; k++)
                                {
                                    int p = k * recordLen;
                                    AppendRecord(appender, chunkBuf, p, header, hasRgb, rgbOffset, cMin, cRange, cMax, ct, ptBuf);
                                }

                                pointsRead += (ulong)recordsInChunk;
                                progressCallback?.Invoke((int)((pointsRead * 100) / total));
                            }
                        }
                        else
                        {
                            ulong targetCount = total / step;
                            ulong countIngested = 0;
                            using var mmf = System.IO.MemoryMappedFiles.MemoryMappedFile.CreateFromFile(actualPath, FileMode.Open, null, 0, System.IO.MemoryMappedFiles.MemoryMappedFileAccess.Read);
                            using var accessor = mmf.CreateViewAccessor(0, 0, System.IO.MemoryMappedFiles.MemoryMappedFileAccess.Read);
                            unsafe
                            {
                                byte* ptr = null;
                                accessor.SafeMemoryMappedViewHandle.AcquirePointer(ref ptr);
                                try
                                {
                                    byte* basePtr = ptr + header.OffsetToPointData;
                                    byte[] recordBuf = new byte[recordLen];
                                    for (ulong i = 0; i < total; i += step)
                                    {
                                        byte* p = basePtr + ((long)i * (long)recordLen);
                                        System.Runtime.InteropServices.Marshal.Copy((IntPtr)p, recordBuf, 0, recordLen);
                                        AppendRecord(appender, recordBuf, 0, header, hasRgb, rgbOffset, cMin, cRange, cMax, ct, ptBuf);
                                        countIngested++;
                                        if (countIngested % 50000 == 0 && targetCount > 0)
                                        {
                                            progressCallback?.Invoke((int)((countIngested * 100) / targetCount));
                                        }
                                    }
                                }
                                finally
                                {
                                    accessor.SafeMemoryMappedViewHandle.ReleasePointer();
                                }
                            }
                        }
                    }
                }

                DuckDbConnectionManager.BuildSpatialIndex();
                DuckDbConnectionManager.HasData = true;

                return DuckDbStatsReader.ReadIngestedStats(conn, total, header);
            }
        }

        private static void AppendRecord(DuckDBAppender appender, byte[] buf, int p, LasHeaderInfo header, bool hasRgb, int rgbOffset, float cMin, float cRange, float cMax, CoordinateTransformation? ct, double[] ptBuf)
        {
            int rawX = BitConverter.ToInt32(buf, p);
            int rawY = BitConverter.ToInt32(buf, p + 4);
            int rawZ = BitConverter.ToInt32(buf, p + 8);
            ushort intensity = BitConverter.ToUInt16(buf, p + 12);
            byte classification = buf[p + 15];

            byte r = 180, g = 180, b = 180;
            if (hasRgb && p + rgbOffset + 6 <= buf.Length)
            {
                ushort r16 = BitConverter.ToUInt16(buf, p + rgbOffset);
                ushort g16 = BitConverter.ToUInt16(buf, p + rgbOffset + 2);
                ushort b16 = BitConverter.ToUInt16(buf, p + rgbOffset + 4);

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

            double x = (rawX * header.ScaleX) + header.OffsetX;
            double y = (rawY * header.ScaleY) + header.OffsetY;
            float z = (float)((rawZ * header.ScaleZ) + header.OffsetZ);

            if (ct != null)
            {
                ptBuf[0] = x;
                ptBuf[1] = y;
                ptBuf[2] = z;
                ct.TransformPoint(ptBuf);
                x = ptBuf[0];
                y = ptBuf[1];
            }

            var row = appender.CreateRow();
            row.AppendValue(x);
            row.AppendValue(y);
            row.AppendValue(z);
            row.AppendValue(intensity);
            row.AppendValue(classification);
            row.AppendValue(r);
            row.AppendValue(g);
            row.AppendValue(b);
            row.EndRow();
        }
    }
}
