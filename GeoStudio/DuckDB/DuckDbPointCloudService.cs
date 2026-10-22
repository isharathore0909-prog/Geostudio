using System;
using System.Collections.Generic;
using GeoStudio.Models;

namespace GeoStudio.DuckDB
{
    public static class DuckDbPointCloudService
    {
        public static bool HasData => DuckDbConnectionManager.HasData;

        public static void Initialize() => DuckDbConnectionManager.Initialize();

        public static PointCloudStats IngestLasFile(string filePath, Action<int>? progressCallback = null, int maxPointsToIngest = 1000000) =>
            DuckDbLasIngestor.IngestLasFile(filePath, progressCallback, maxPointsToIngest);

        public static PointCloudBatch GetOverviewBatch(int maxPoints = 2000000) =>
            DuckDbQueryEngine.GetOverviewBatch(maxPoints);

        public static PointCloudBatch QueryViewportBatch(double minX, double maxX, double minY, double maxY, int maxPoints = 2000000, byte? classification = null) =>
            DuckDbQueryEngine.QueryViewportBatch(minX, maxX, minY, maxY, maxPoints, classification);

        public static void IngestPoints(List<PointRecord> points) =>
            DuckDbQueryEngine.IngestPoints(points);

        public static List<PointRecord> QueryViewportPoints(double minX, double maxX, double minY, double maxY, int maxPoints = 80000, byte? classification = null)
        {
            var batch = QueryViewportBatch(minX, maxX, minY, maxY, maxPoints, classification);
            var list = new List<PointRecord>(batch.count);
            for (int i = 0; i < batch.count; i++)
            {
                list.Add(new PointRecord
                {
                    X = batch.x[i],
                    Y = batch.y[i],
                    Z = batch.z[i],
                    Intensity = batch.i != null ? batch.i[i] : (ushort)128,
                    Classification = batch.c != null ? batch.c[i] : (byte)2,
                    R = batch.r != null ? batch.r[i] : (byte)180,
                    G = batch.g != null ? batch.g[i] : (byte)180,
                    B = batch.b != null ? batch.b[i] : (byte)180
                });
            }
            return list;
        }

        public static List<PointRecord> GetAllSampledPoints(int maxPoints = 120000, byte? classification = null)
        {
            var batch = GetOverviewBatch(maxPoints);
            var list = new List<PointRecord>(batch.count);
            for (int i = 0; i < batch.count; i++)
            {
                list.Add(new PointRecord
                {
                    X = batch.x[i],
                    Y = batch.y[i],
                    Z = batch.z[i],
                    Intensity = batch.i != null ? batch.i[i] : (ushort)128,
                    Classification = batch.c != null ? batch.c[i] : (byte)2,
                    R = batch.r != null ? batch.r[i] : (byte)180,
                    G = batch.g != null ? batch.g[i] : (byte)180,
                    B = batch.b != null ? batch.b[i] : (byte)180
                });
            }
            return list;
        }

        public static void Clear() => DuckDbConnectionManager.Clear();
    }
}
