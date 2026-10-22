using System;
using DuckDB.NET.Data;
using GeoStudio.PointCloud;

namespace GeoStudio.DuckDB
{
    internal static class DuckDbStatsReader
    {
        public static PointCloudStats ReadIngestedStats(DuckDBConnection conn, ulong total, LasHeaderInfo header)
        {
            var stats = new PointCloudStats
            {
                TotalPoints = (long)total,
                MinX = header.MinX,
                MaxX = header.MaxX,
                MinY = header.MinY,
                MaxY = header.MaxY,
                MinZ = header.MinZ,
                MaxZ = header.MaxZ
            };

            using (var boundCmd = conn.CreateCommand())
            {
                boundCmd.CommandText = "SELECT min(x), max(x), min(y), max(y), min(z), max(z), avg(z) FROM pointcloud;";
                using var bRdr = boundCmd.ExecuteReader();
                if (bRdr.Read() && !bRdr.IsDBNull(0))
                {
                    stats.MinX = Convert.ToDouble(bRdr.GetValue(0));
                    stats.MaxX = Convert.ToDouble(bRdr.GetValue(1));
                    stats.MinY = Convert.ToDouble(bRdr.GetValue(2));
                    stats.MaxY = Convert.ToDouble(bRdr.GetValue(3));
                    stats.MinZ = Convert.ToDouble(bRdr.GetValue(4));
                    stats.MaxZ = Convert.ToDouble(bRdr.GetValue(5));
                    stats.AvgZ = Convert.ToDouble(bRdr.GetValue(6));
                }
            }

            using (var statsCmd = conn.CreateCommand())
            {
                statsCmd.CommandText = "SELECT classification, count(*) FROM pointcloud GROUP BY classification;";
                using var rdr = statsCmd.ExecuteReader();
                while (rdr.Read())
                {
                    byte cls = Convert.ToByte(rdr.GetValue(0));
                    long count = Convert.ToInt64(rdr.GetValue(1));
                    stats.ClassificationBreakdown[cls] = count;
                }
            }

            return stats;
        }
    }
}
