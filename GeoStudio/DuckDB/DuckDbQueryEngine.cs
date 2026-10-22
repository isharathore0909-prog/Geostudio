using System;
using System.Collections.Generic;
using DuckDB.NET.Data;
using GeoStudio.Models;

namespace GeoStudio.DuckDB
{
    internal static class DuckDbQueryEngine
    {
        public static PointCloudBatch GetOverviewBatch(int maxPoints = 2000000)
        {
            DuckDbConnectionManager.Initialize();
            if (!DuckDbConnectionManager.HasData || DuckDbConnectionManager.Connection == null)
                return new PointCloudBatch();

            lock (DuckDbConnectionManager.DbLock)
            {
                try
                {
                    using var cmd = DuckDbConnectionManager.Connection.CreateCommand();
                    cmd.CommandText = "SELECT count(*) FROM pointcloud;";
                    long total = Convert.ToInt64(cmd.ExecuteScalar());

                    if (total <= maxPoints)
                    {
                        cmd.CommandText = "SELECT x, y, z, intensity, classification, r, g, b FROM pointcloud;";
                    }
                    else
                    {
                        cmd.CommandText = $@"
                            SELECT x, y, z, intensity, classification, r, g, b 
                            FROM pointcloud 
                            USING SAMPLE reservoir({maxPoints} ROWS);";
                    }

                    return ReadBatchFromCommand(cmd, (int)Math.Min((long)maxPoints, total));
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"DuckDB overview batch error: {ex.Message}");
                    return new PointCloudBatch();
                }
            }
        }

        public static PointCloudBatch QueryViewportBatch(double minX, double maxX, double minY, double maxY, int maxPoints = 2000000, byte? classification = null)
        {
            DuckDbConnectionManager.Initialize();
            if (!DuckDbConnectionManager.HasData || DuckDbConnectionManager.Connection == null)
                return new PointCloudBatch();

            double realMinX = Math.Min(minX, maxX);
            double realMaxX = Math.Max(minX, maxX);
            double realMinY = Math.Min(minY, maxY);
            double realMaxY = Math.Max(minY, maxY);

            lock (DuckDbConnectionManager.DbLock)
            {
                try
                {
                    using var cmd = DuckDbConnectionManager.Connection.CreateCommand();
                    string filterCls = classification.HasValue ? $"AND classification = {classification.Value}" : "";

                    cmd.CommandText = $@"
                        SELECT count(*) 
                        FROM pointcloud 
                        WHERE x BETWEEN {realMinX} AND {realMaxX} 
                          AND y BETWEEN {realMinY} AND {realMaxY}
                          {filterCls};";
                    long vpCount = Convert.ToInt64(cmd.ExecuteScalar());

                    if (vpCount == 0) return new PointCloudBatch();

                    if (vpCount <= maxPoints)
                    {
                        cmd.CommandText = $@"
                            SELECT x, y, z, intensity, classification, r, g, b 
                            FROM pointcloud 
                            WHERE x BETWEEN {realMinX} AND {realMaxX} 
                              AND y BETWEEN {realMinY} AND {realMaxY}
                              {filterCls};";
                    }
                    else
                    {
                        cmd.CommandText = $@"
                            SELECT x, y, z, intensity, classification, r, g, b 
                            FROM pointcloud 
                            WHERE x BETWEEN {realMinX} AND {realMaxX} 
                              AND y BETWEEN {realMinY} AND {realMaxY}
                              {filterCls}
                            USING SAMPLE reservoir({maxPoints} ROWS);";
                    }

                    return ReadBatchFromCommand(cmd, (int)Math.Min((long)maxPoints, vpCount));
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"DuckDB viewport batch error: {ex.Message}");
                    return new PointCloudBatch();
                }
            }
        }

        private static PointCloudBatch ReadBatchFromCommand(DuckDBCommand cmd, int estimatedCapacity)
        {
            var xList = new List<double>(estimatedCapacity);
            var yList = new List<double>(estimatedCapacity);
            var zList = new List<float>(estimatedCapacity);
            var iList = new List<byte>(estimatedCapacity);
            var cList = new List<byte>(estimatedCapacity);
            var rList = new List<byte>(estimatedCapacity);
            var gList = new List<byte>(estimatedCapacity);
            var bList = new List<byte>(estimatedCapacity);

            using var rdr = cmd.ExecuteReader();
            while (rdr.Read())
            {
                xList.Add(rdr.GetDouble(0));
                yList.Add(rdr.GetDouble(1));
                zList.Add(rdr.GetFloat(2));
                int rawI = Convert.ToInt32(rdr.GetValue(3));
                iList.Add((byte)(rawI > 255 ? (rawI >> 8) : rawI));
                cList.Add(rdr.GetByte(4));
                rList.Add(rdr.GetByte(5));
                gList.Add(rdr.GetByte(6));
                bList.Add(rdr.GetByte(7));
            }

            return new PointCloudBatch
            {
                count = xList.Count,
                x = xList.ToArray(),
                y = yList.ToArray(),
                z = zList.ToArray(),
                i = iList.ToArray(),
                c = cList.ToArray(),
                r = rList.ToArray(),
                g = gList.ToArray(),
                b = bList.ToArray()
            };
        }

        public static void IngestPoints(List<PointRecord> points)
        {
            if (points == null || points.Count == 0) return;
            DuckDbConnectionManager.Initialize();

            lock (DuckDbConnectionManager.DbLock)
            {
                var conn = DuckDbConnectionManager.Connection;
                if (conn == null) return;
                DuckDbConnectionManager.RecreateTable();

                using (var appender = conn.CreateAppender("pointcloud"))
                {
                    foreach (var pt in points)
                    {
                        var row = appender.CreateRow();
                        row.AppendValue(pt.X);
                        row.AppendValue(pt.Y);
                        row.AppendValue((float)pt.Z);
                        row.AppendValue(pt.Intensity);
                        row.AppendValue(pt.Classification);
                        row.AppendValue(pt.R);
                        row.AppendValue(pt.G);
                        row.AppendValue(pt.B);
                        row.EndRow();
                    }
                }

                DuckDbConnectionManager.HasData = true;
            }
        }
    }
}
