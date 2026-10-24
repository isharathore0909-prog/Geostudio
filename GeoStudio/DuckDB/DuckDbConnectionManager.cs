using System;
using DuckDB.NET.Data;

namespace GeoStudio.DuckDB
{
    internal static class DuckDbConnectionManager
    {
        private static DuckDBConnection? _connection = null;
        private static readonly object _dbLock = new object();
        private static bool _hasData = false;

        public static object DbLock => _dbLock;
        public static DuckDBConnection? Connection => _connection;
        public static bool HasData
        {
            get => _hasData;
            set => _hasData = value;
        }

        public static void Initialize()
        {
            if (_connection != null) return;
            lock (_dbLock)
            {
                if (_connection != null) return;
                try
                {
                    _connection = new DuckDBConnection("DataSource=:memory:");
                    _connection.Open();
                    using var cmd = _connection.CreateCommand();
                    cmd.CommandText = "CREATE TABLE IF NOT EXISTS pointcloud (x DOUBLE, y DOUBLE, z FLOAT, intensity USMALLINT, classification UTINYINT, r UTINYINT, g UTINYINT, b UTINYINT);";
                    cmd.ExecuteNonQuery();
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"DuckDB init error: {ex.Message}");
                }
            }
        }

        public static void RecreateTable()
        {
            if (_connection == null) return;
            using var clearCmd = _connection.CreateCommand();
            clearCmd.CommandText = "DROP TABLE IF EXISTS pointcloud; CREATE TABLE pointcloud (x DOUBLE, y DOUBLE, z FLOAT, intensity USMALLINT, classification UTINYINT, r UTINYINT, g UTINYINT, b UTINYINT, rn UTINYINT, nr UTINYINT, sa UTINYINT, ps USMALLINT, fl UTINYINT, nir UTINYINT, t UTINYINT);";
            clearCmd.ExecuteNonQuery();
        }

        public static void UpdateClassification(byte[] newCls)
        {
            if (_connection == null || newCls == null || newCls.Length == 0) return;
            lock (_dbLock)
            {
                try
                {
                    // Update in-memory DuckDB classification if rowid matches
                    using var cmd = _connection.CreateCommand();
                    cmd.CommandText = "SELECT count(*) FROM pointcloud;";
                    long count = Convert.ToInt64(cmd.ExecuteScalar());
                    if (count == newCls.Length)
                    {
                        using var trans = _connection.BeginTransaction();
                        using var updateCmd = _connection.CreateCommand();
                        updateCmd.CommandText = "UPDATE pointcloud SET classification = $1 WHERE rowid = $2;";
                        var pCls = updateCmd.CreateParameter();
                        var pRow = updateCmd.CreateParameter();
                        updateCmd.Parameters.Add(pCls);
                        updateCmd.Parameters.Add(pRow);
                        for (int i = 0; i < newCls.Length; i++)
                        {
                            pCls.Value = newCls[i];
                            pRow.Value = i;
                            updateCmd.ExecuteNonQuery();
                        }
                        trans.Commit();
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"DuckDB classification update note: {ex.Message}");
                }
            }
        }

        public static void BuildSpatialIndex()
        {
            if (_connection == null) return;
            try
            {
                using var idxCmd = _connection.CreateCommand();
                idxCmd.CommandText = "CREATE INDEX IF NOT EXISTS idx_pc_xy ON pointcloud (x, y);";
                idxCmd.ExecuteNonQuery();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"DuckDB index creation note: {ex.Message}");
            }
        }

        public static void Clear()
        {
            lock (_dbLock)
            {
                if (_connection == null) return;
                try
                {
                    using var clearCmd = _connection.CreateCommand();
                    clearCmd.CommandText = "DROP TABLE IF EXISTS pointcloud; DROP TABLE IF EXISTS pointcloud_opt;";
                    clearCmd.ExecuteNonQuery();
                    _hasData = false;
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"DuckDB Clear warning: {ex.Message}");
                }
            }
        }
    }
}
