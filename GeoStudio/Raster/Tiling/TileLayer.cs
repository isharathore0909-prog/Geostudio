using System.Collections.Concurrent;

namespace GeoStudio.Raster
{
    internal sealed class TileLayer
    {
        public string Id = "";
        public string SourcePath = "";
        public volatile string? CogPath;
        public int Version;
        public bool HasOverviews;
        public readonly ConcurrentBag<PooledDataset> Pool = new();
        public readonly object StretchLock = new();
        public (double lo, double hi)[]? Stretch;

        public void DrainPool()
        {
            while (Pool.TryTake(out var p)) p.Dispose();
        }
    }
}
