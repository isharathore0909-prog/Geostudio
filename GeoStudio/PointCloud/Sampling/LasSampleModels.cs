using System;

namespace GeoStudio.PointCloud
{
    public readonly record struct LasCrsInfo(string? Wkt, int? Epsg, bool IsProjected);

    public sealed class LasSampleResult
    {
        public PointCloudBatch Batch { get; init; } = new();
        public long TotalPoints { get; init; }
        public double[] Bounds { get; init; } = new double[4];
        public double MinZ { get; init; }
        public double MaxZ { get; init; }
        public bool HasRgb { get; init; }
        public bool Reprojected { get; init; }
        public bool AssumedCrs { get; init; }
    }
}
