using System;
using System.Collections.Generic;

namespace GeoStudio.PointCloud
{
    public class LasHeaderInfo
    {
        public string FileSignature { get; set; } = "LASF";
        public byte VersionMajor { get; set; } = 1;
        public byte VersionMinor { get; set; } = 2;
        public uint HeaderSize { get; set; }
        public uint OffsetToPointData { get; set; }
        public byte PointDataRecordFormat { get; set; }
        public ushort PointDataRecordLength { get; set; }
        public ulong LegacyPointCount { get; set; }
        public ulong TotalPointCount { get; set; }
        public double ScaleX { get; set; } = 0.01;
        public double ScaleY { get; set; } = 0.01;
        public double ScaleZ { get; set; } = 0.01;
        public double OffsetX { get; set; }
        public double OffsetY { get; set; }
        public double OffsetZ { get; set; }
        public double MinX { get; set; }
        public double MaxX { get; set; }
        public double MinY { get; set; }
        public double MaxY { get; set; }
        public double MinZ { get; set; }
        public double MaxZ { get; set; }
        public long FileSizeBytes { get; set; }
        public string? CrsWkt { get; set; }
        public int? EpsgCode { get; set; }
        public bool IsProjected => Math.Abs(MinX) > 180 || Math.Abs(MaxX) > 180 || Math.Abs(MinY) > 90 || Math.Abs(MaxY) > 90;
    }

    public class PointRecord
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public ushort Intensity { get; set; }
        public byte Classification { get; set; }
        public byte ReturnNumber { get; set; }
        public byte R { get; set; }
        public byte G { get; set; }
        public byte B { get; set; }
    }

    public class PointCloudStats
    {
        public long TotalPoints { get; set; }
        public double MinX { get; set; }
        public double MaxX { get; set; }
        public double MinY { get; set; }
        public double MaxY { get; set; }
        public double MinZ { get; set; }
        public double MaxZ { get; set; }
        public double AvgZ { get; set; }
        public Dictionary<byte, long> ClassificationBreakdown { get; set; } = new();
    }

    public class PointCloudBatch
    {
        public int count { get; set; }
        public double[] x { get; set; } = Array.Empty<double>();
        public double[] y { get; set; } = Array.Empty<double>();
        public float[] z { get; set; } = Array.Empty<float>();
        public byte[]? r { get; set; }
        public byte[]? g { get; set; }
        public byte[]? b { get; set; }
        public byte[]? c { get; set; }
        public byte[]? i { get; set; }
        public byte[]? rn { get; set; }
        public byte[]? nr { get; set; }
        public byte[]? sa { get; set; }
        public byte[]? ps { get; set; }
        public byte[]? fl { get; set; }
        public byte[]? nir { get; set; }
        public byte[]? t { get; set; }
        public bool hasRgb { get; set; }
    }
}
