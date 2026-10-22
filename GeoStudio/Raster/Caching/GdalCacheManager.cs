using System;
using System.IO;
using System.Threading.Tasks;
using MaxRev.Gdal.Core;
using OSGeo.GDAL;

namespace GeoStudio.Raster
{
    public static class GdalCacheManager
    {
        private static bool _isConfigured = false;
        private static readonly object _lock = new object();
        private static readonly object _dsLock = new object();
        private static Dataset? _cachedDs = null;
        private static string? _cachedDsPath = null;

        public static void Initialize()
        {
            if (_isConfigured) return;
            lock (_lock)
            {
                if (_isConfigured) return;
                try
                {
                    GdalBase.ConfigureAll();
                    Gdal.SetConfigOption("GDAL_CACHEMAX", "1024");
                    Gdal.SetConfigOption("GDAL_RASTERIO_RESAMPLING", "NEAREST");
                    Gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS");
                    Gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR");
                    Gdal.SetConfigOption("VSI_CACHE", "TRUE");
                    Gdal.SetConfigOption("VSI_CACHE_SIZE", "67108864");
                    _isConfigured = true;
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"GDAL Init Warning: {ex.Message}");
                }
            }
        }

        public static string GetCacheDirectory()
        {
            string appData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string cacheDir = Path.Combine(appData, "GeoStudio", "Cache");
            Directory.CreateDirectory(cacheDir);
            return cacheDir;
        }

        public static string GetOverviewCacheFileName(string filePath, bool isElevation = false, string shaderMode = "atlas", string palette = "GLOBAL_MAPPER_ATLAS")
        {
            string safeName = Path.GetFileNameWithoutExtension(filePath);
            long mtime = File.Exists(filePath) ? File.GetLastWriteTimeUtc(filePath).Ticks : 0;
            bool useShader = isElevation || (!string.IsNullOrEmpty(shaderMode) && shaderMode != "none");
            string key = $"{filePath}_{mtime}_{(useShader ? $"{shaderMode}_{palette}" : "rgb")}_3d".ToLowerInvariant();
            string hash = Convert.ToHexString(System.Security.Cryptography.MD5.HashData(System.Text.Encoding.UTF8.GetBytes(key)))[..8].ToLowerInvariant();
            return $"overview_{safeName}_{shaderMode}_{hash}.png";
        }

        public static void PruneCache()
        {
            Task.Run(() =>
            {
                try
                {
                    string cacheDir = GetCacheDirectory();
                    var di = new DirectoryInfo(cacheDir);

                    // 1. Prune temporary viewport windows: keep at most 4 latest
                    var winFiles = di.GetFiles("win_*.*");
                    if (winFiles.Length > 4)
                    {
                        Array.Sort(winFiles, (a, b) => b.CreationTimeUtc.CompareTo(a.CreationTimeUtc));
                        for (int i = 4; i < winFiles.Length; i++)
                        {
                            try { winFiles[i].Delete(); } catch { }
                        }
                    }

                    // 2. Prune overviews: keep at most 8 most recently used overviews
                    var ovrFiles = di.GetFiles("overview_*.*");
                    if (ovrFiles.Length > 8)
                    {
                        Array.Sort(ovrFiles, (a, b) => b.LastWriteTimeUtc.CompareTo(a.LastWriteTimeUtc));
                        for (int i = 8; i < ovrFiles.Length; i++)
                        {
                            try { ovrFiles[i].Delete(); } catch { }
                        }
                    }
                }
                catch { }
            });
        }

        public static void ClearCache()
        {
            lock (_dsLock)
            {
                _cachedDs?.Dispose();
                _cachedDs = null;
                _cachedDsPath = null;
            }

            try
            {
                string cacheDir = GetCacheDirectory();
                if (Directory.Exists(cacheDir))
                {
                    foreach (var file in Directory.GetFiles(cacheDir))
                    {
                        try { File.Delete(file); } catch { }
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"ClearCache warning: {ex.Message}");
            }
        }

        public static Dataset? GetOpenDataset(string filePath)
        {
            lock (_dsLock)
            {
                if (_cachedDs != null && _cachedDsPath == filePath)
                    return _cachedDs;

                try
                {
                    _cachedDs?.Dispose();
                    _cachedDs = Gdal.Open(filePath, Access.GA_ReadOnly);
                    _cachedDsPath = filePath;
                    return _cachedDs;
                }
                catch
                {
                    return null;
                }
            }
        }
    }
}
