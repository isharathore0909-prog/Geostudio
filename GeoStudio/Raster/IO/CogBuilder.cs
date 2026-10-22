using System;
using System.IO;
using OSGeo.GDAL;
using OSGeo.OSR;

namespace GeoStudio.Raster
{
    public static class CogBuilder
    {
        public static string GetCogPath(string sourcePath) =>
            Path.Combine(GdalRasterService.GetCacheDirectory(), "cog", CacheKeys.For(sourcePath) + ".tif");

        internal static bool IsWebMercator(string wkt)
        {
            using var a = new SpatialReference(wkt);
            using var b = new SpatialReference("");
            b.ImportFromEPSG(3857);
            return a.IsSame(b, null) == 1;
        }

        public static bool Enqueue(string layerId, string sourcePath)
        {
            GdalRasterService.Initialize();
            string finalPath = GetCogPath(sourcePath);

            if (!File.Exists(finalPath))
            {
                using var ds = Gdal.Open(sourcePath, Access.GA_ReadOnly);
                if (ds == null) return false;

                string wkt = ds.GetProjectionRef();
                if (string.IsNullOrWhiteSpace(wkt)) return false;

                bool isCog = string.Equals(ds.GetMetadataItem("LAYOUT", "IMAGE_STRUCTURE"), "COG", StringComparison.OrdinalIgnoreCase);
                if (isCog && IsWebMercator(wkt)) return false;

                Directory.CreateDirectory(Path.GetDirectoryName(finalPath)!);
                long free = new DriveInfo(Path.GetPathRoot(Path.GetFullPath(finalPath))!).AvailableFreeSpace;
                if (free < new FileInfo(sourcePath).Length)
                {
                    OptimizationQueue.ReportFailed(layerId, "Not enough free disk space to build the optimized copy.");
                    return false;
                }
            }

            OptimizationQueue.Enqueue(layerId, finalPath, (tmp, progress, ct) =>
            {
                using var src = Gdal.Open(sourcePath, Access.GA_ReadOnly);
                if (src == null) return false;

                var args = new[]
                {
                    "-of", "COG",
                    "-co", "TILING_SCHEME=GoogleMapsCompatible",
                    "-co", "COMPRESS=DEFLATE",
                    "-co", "PREDICTOR=YES",
                    "-co", "BIGTIFF=IF_SAFER",
                    "-co", "OVERVIEW_RESAMPLING=AVERAGE",
                    "-co", "NUM_THREADS=2"
                };

                Gdal.GDALProgressFuncDelegate cb = (double complete, IntPtr message, IntPtr data) =>
                {
                    progress((int)Math.Clamp(complete * 100.0, 0, 100));
                    return ct.IsCancellationRequested ? 0 : 1;
                };

                using var options = new GDALTranslateOptions(args);
                using var outDs = Gdal.wrapper_GDALTranslate(tmp, src, options, cb, null);
                GC.KeepAlive(cb);
                if (outDs == null) return false;
                outDs.FlushCache();
                return !ct.IsCancellationRequested;
            });
            return true;
        }
    }
}
