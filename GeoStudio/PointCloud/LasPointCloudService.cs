using System;
using System.IO;
using System.Collections.Generic;

namespace GeoStudio.PointCloud
{
    public static class LasPointCloudService
    {
        public static LasHeaderInfo InspectLasHeader(string filePath)
        {
            var fileInfo = new FileInfo(filePath);
            if (!fileInfo.Exists)
                throw new FileNotFoundException("LAS file not found", filePath);

            using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
            using var reader = new BinaryReader(fs);

            var info = new LasHeaderInfo { FileSizeBytes = fileInfo.Length };

            byte[] sigBytes = reader.ReadBytes(4);
            info.FileSignature = System.Text.Encoding.ASCII.GetString(sigBytes);

            fs.Seek(24, SeekOrigin.Begin);
            info.VersionMajor = reader.ReadByte();
            info.VersionMinor = reader.ReadByte();

            fs.Seek(94, SeekOrigin.Begin);
            info.HeaderSize = reader.ReadUInt16();
            info.OffsetToPointData = reader.ReadUInt32();
            uint numVlrs = reader.ReadUInt32();
            info.PointDataRecordFormat = reader.ReadByte();
            info.PointDataRecordLength = reader.ReadUInt16();
            info.LegacyPointCount = reader.ReadUInt32();
            info.TotalPointCount = info.LegacyPointCount;

            fs.Seek(131, SeekOrigin.Begin);
            info.ScaleX = reader.ReadDouble();
            info.ScaleY = reader.ReadDouble();
            info.ScaleZ = reader.ReadDouble();
            info.OffsetX = reader.ReadDouble();
            info.OffsetY = reader.ReadDouble();
            info.OffsetZ = reader.ReadDouble();
            info.MaxX = reader.ReadDouble();
            info.MinX = reader.ReadDouble();
            info.MaxY = reader.ReadDouble();
            info.MinY = reader.ReadDouble();
            info.MaxZ = reader.ReadDouble();
            info.MinZ = reader.ReadDouble();

            // LAS 1.4 64-bit point count and EVLR support
            ulong offsetToFirstEvlr = 0;
            uint numEvlrs = 0;
            if (info.VersionMajor == 1 && info.VersionMinor >= 4 && fs.Length >= 247)
            {
                fs.Seek(235, SeekOrigin.Begin);
                offsetToFirstEvlr = reader.ReadUInt64();
                numEvlrs = reader.ReadUInt32();

                fs.Seek(247, SeekOrigin.Begin);
                ulong extendedPointCount = reader.ReadUInt64();
                if (extendedPointCount > 0)
                {
                    info.TotalPointCount = extendedPointCount;
                }
            }

            try
            {
                fs.Seek(info.HeaderSize, SeekOrigin.Begin);
                for (int v = 0; v < numVlrs && fs.Position + 54 <= fs.Length; v++)
                {
                    long vlrStart = fs.Position;
                    fs.Seek(vlrStart + 18, SeekOrigin.Begin);
                    ushort recordId = reader.ReadUInt16();
                    ushort recordLen = reader.ReadUInt16();
                    fs.Seek(vlrStart + 54, SeekOrigin.Begin);

                    if (recordId == 2112 && recordLen > 0 && fs.Position + recordLen <= fs.Length)
                    {
                        byte[] wktBytes = reader.ReadBytes(recordLen);
                        info.CrsWkt = System.Text.Encoding.ASCII.GetString(wktBytes).Trim('\0', ' ');
                    }
                    else if (recordId == 34735 && recordLen >= 8 && fs.Position + recordLen <= fs.Length)
                    {
                        byte[] keyBytes = reader.ReadBytes(recordLen);
                        if (keyBytes.Length >= 8)
                        {
                            ushort numKeys = BitConverter.ToUInt16(keyBytes, 6);
                            for (int k = 0; k < numKeys; k++)
                            {
                                int offset = 8 + (k * 8);
                                if (offset + 8 > keyBytes.Length) break;
                                ushort keyId = BitConverter.ToUInt16(keyBytes, offset);
                                ushort val = BitConverter.ToUInt16(keyBytes, offset + 6);
                                if ((keyId == 3072 || keyId == 2048) && val > 0)
                                {
                                    info.EpsgCode = val;
                                    break;
                                }
                            }
                        }
                    }
                    else
                    {
                        fs.Seek(vlrStart + 54 + recordLen, SeekOrigin.Begin);
                    }
                }

                if (string.IsNullOrEmpty(info.CrsWkt) && numEvlrs > 0 && offsetToFirstEvlr > 0 && (long)offsetToFirstEvlr + 60 <= fs.Length)
                {
                    fs.Seek((long)offsetToFirstEvlr, SeekOrigin.Begin);
                    for (uint e = 0; e < numEvlrs && fs.Position + 60 <= fs.Length; e++)
                    {
                        long evlrStart = fs.Position;
                        fs.Seek(evlrStart + 18, SeekOrigin.Begin);
                        ushort evlrRecordId = reader.ReadUInt16();
                        ulong evlrRecordLen = reader.ReadUInt64();
                        fs.Seek(evlrStart + 60, SeekOrigin.Begin);

                        if (evlrRecordId == 2112 && evlrRecordLen > 0 && fs.Position + (long)evlrRecordLen <= fs.Length)
                        {
                            byte[] wktBytes = reader.ReadBytes((int)evlrRecordLen);
                            info.CrsWkt = System.Text.Encoding.ASCII.GetString(wktBytes).Trim('\0', ' ');
                            break;
                        }
                        else
                        {
                            fs.Seek(evlrStart + 60 + (long)evlrRecordLen, SeekOrigin.Begin);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"VLR CRS extraction warning: {ex.Message}");
            }

            return info;
        }

        public static string EnsureUncompressedLas(string filePath, Action<int, string>? progress = null) =>
            LasDecompressor.EnsureUncompressedLas(filePath, progress);

        public static List<PointRecord> ReadSubsampledPoints(string filePath, int maxPointsToReturn = 50000)
        {
            var header = InspectLasHeader(filePath);
            var points = new List<PointRecord>();

            if (header.TotalPointCount == 0 || header.PointDataRecordLength == 0)
                return points;

            using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
            using var reader = new BinaryReader(fs);

            fs.Seek(header.OffsetToPointData, SeekOrigin.Begin);

            ulong step = Math.Max(1, header.TotalPointCount / (ulong)maxPointsToReturn);
            int recordLen = header.PointDataRecordLength;

            for (ulong i = 0; i < header.TotalPointCount && points.Count < maxPointsToReturn; i += step)
            {
                long pos = header.OffsetToPointData + (long)(i * (ulong)recordLen);
                if (pos + recordLen > fs.Length) break;

                fs.Seek(pos, SeekOrigin.Begin);

                int rawX = reader.ReadInt32();
                int rawY = reader.ReadInt32();
                int rawZ = reader.ReadInt32();
                ushort intensity = reader.ReadUInt16();
                byte flags = reader.ReadByte();
                byte classification = reader.ReadByte();

                double x = (rawX * header.ScaleX) + header.OffsetX;
                double y = (rawY * header.ScaleY) + header.OffsetY;
                double z = (rawZ * header.ScaleZ) + header.OffsetZ;

                byte r = 0, g = 0, b = 0;
                int rgbOffset = -1;
                if (header.PointDataRecordFormat == 2 && recordLen >= 26) rgbOffset = 20;
                else if (header.PointDataRecordFormat == 3 && recordLen >= 34) rgbOffset = 28;
                else if ((header.PointDataRecordFormat == 7 || header.PointDataRecordFormat == 8) && recordLen >= 36) rgbOffset = 30;

                if (rgbOffset > 0 && pos + rgbOffset + 6 <= fs.Length)
                {
                    fs.Seek(pos + rgbOffset, SeekOrigin.Begin);
                    ushort r16 = reader.ReadUInt16();
                    ushort g16 = reader.ReadUInt16();
                    ushort b16 = reader.ReadUInt16();
                    r = (byte)(r16 > 255 ? (r16 >> 8) : r16);
                    g = (byte)(g16 > 255 ? (g16 >> 8) : g16);
                    b = (byte)(b16 > 255 ? (b16 >> 8) : b16);
                }

                points.Add(new PointRecord
                {
                    X = x,
                    Y = y,
                    Z = z,
                    Intensity = intensity,
                    Classification = classification,
                    ReturnNumber = (byte)(flags & 0x07),
                    R = r,
                    G = g,
                    B = b
                });
            }

            return points;
        }

        public static readonly Dictionary<byte, (string Name, string ColorHex)> AsprsStandardClasses = new()
        {
            { 0, ("Created, Never Classified", "#94A3B8") },
            { 1, ("Unassigned", "#CBD5E1") },
            { 2, ("Ground", "#D4A373") },
            { 3, ("Low Vegetation", "#86EFAC") },
            { 4, ("Medium Vegetation", "#22C55E") },
            { 5, ("High Vegetation (Canopy)", "#15803D") },
            { 6, ("Building", "#EF4444") },
            { 7, ("Low Point / Noise", "#8B7464") },
            { 8, ("Model Key Point", "#F59E0B") },
            { 9, ("Water", "#0284C7") },
            { 10, ("Rail", "#A855F7") },
            { 11, ("Road Surface", "#475569") },
            { 12, ("Overlap / Reserved", "#EC4899") },
            { 13, ("Wire - Guard", "#EAB308") },
            { 14, ("Wire - Conductor", "#F97316") },
            { 15, ("Transmission Tower", "#84CC16") },
            { 17, ("Bridge Deck", "#78716C") },
            { 18, ("High Noise", "#06B6D4") }
        };

        public static (string Name, string ColorHex) GetClassMeta(byte classId)
        {
            if (AsprsStandardClasses.TryGetValue(classId, out var meta)) return meta;
            return ($"Class {classId}", "#64748B");
        }

        public static Dictionary<byte, long> ScanClassificationCounts(string filePath, byte[]? activeBatch = null)
        {
            var counts = new Dictionary<byte, long>();
            if (activeBatch != null && activeBatch.Length > 0)
            {
                for (int i = 0; i < activeBatch.Length; i++)
                {
                    byte c = activeBatch[i];
                    if (counts.TryGetValue(c, out long cnt)) counts[c] = cnt + 1;
                    else counts[c] = 1;
                }
                return counts;
            }

            if (!File.Exists(filePath)) return counts;
            string actualPath = EnsureUncompressedLas(filePath);
            var header = InspectLasHeader(actualPath);
            if (header.TotalPointCount == 0) return counts;

            using var fs = new FileStream(actualPath, FileMode.Open, FileAccess.Read, FileShare.Read, 4194304);
            int recLen = header.PointDataRecordLength;
            long startPos = (long)header.OffsetToPointData;
            ulong total = header.TotalPointCount;
            int fmt = header.PointDataRecordFormat;

            ulong step = Math.Max(1, total / 2_000_000UL);
            byte[] buf = new byte[recLen];

            for (ulong i = 0; i < total; i += step)
            {
                long pos = startPos + ((long)i * recLen);
                if (pos + recLen > fs.Length) break;
                fs.Seek(pos, SeekOrigin.Begin);
                if (fs.Read(buf, 0, recLen) < recLen) break;
                byte cls = fmt >= 6 ? buf[16] : (byte)(buf[15] & 0x1F);
                if (counts.TryGetValue(cls, out long cnt)) counts[cls] = cnt + (long)step;
                else counts[cls] = (long)step;
            }

            return counts;
        }
    }
}
