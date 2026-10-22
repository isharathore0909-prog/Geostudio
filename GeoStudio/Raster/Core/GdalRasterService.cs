using System;
using OSGeo.GDAL;

namespace GeoStudio.Raster
{
    public static class GdalRasterService
    {
        public static event Action<string, string>? OverviewReady
        {
            add => GdalOverviewGenerator.OverviewReady += value;
            remove => GdalOverviewGenerator.OverviewReady -= value;
        }

        public static void Initialize() => GdalCacheManager.Initialize();

        public static string GetCacheDirectory() => GdalCacheManager.GetCacheDirectory();

        public static void ClearCache() => GdalCacheManager.ClearCache();

        public static Dataset? GetOpenDataset(string filePath) => GdalCacheManager.GetOpenDataset(filePath);

        public static GdalRasterMetadata InspectMetadata(string filePath) =>
            GdalMetadataReader.InspectMetadata(filePath);

        public static void QueueOverviewGeneration(string filePath) =>
            GdalOverviewGenerator.QueueOverviewGeneration(filePath);

        public static GdalRasterMetadata InspectAndGeneratePreview(string filePath, int previewWidth = 2048) =>
            GdalOverviewGenerator.InspectAndGeneratePreview(filePath, previewWidth);

        public static GdalRasterMetadata ApplyTerrainShader(string filePath, string shaderMode = "atlas", string palette = "GLOBAL_MAPPER_ATLAS") =>
            GdalOverviewGenerator.InspectAndGeneratePreview(filePath, 2048, shaderMode, palette);

        public static (double[] distances, double[] elevations) SampleProfileLine(string filePath, double lon1, double lat1, double lon2, double lat2) =>
            ElevationShadedRelief.SampleProfileLine(filePath, lon1, lat1, lon2, lat2);

        public static void CheckAndBuildOverviewsInBackground(string filePath)
        {
            // Decimation in GDAL ReadRaster handles BigTIFFs in ~150ms without 100s .ovr file building
        }

        public static WindowRenderResult RenderWindow(
            string filePath,
            double reqMinLon, double reqMinLat, double reqMaxLon, double reqMaxLat,
            int screenW, int screenH,
            string? shaderMode = null,
            string? palette = null) =>
            GdalWindowRenderer.RenderWindow(filePath, reqMinLon, reqMinLat, reqMaxLon, reqMaxLat, screenW, screenH, shaderMode, palette);
    }
}
