using System;
using System.IO;
using System.Threading.Tasks;
using System.Collections.Concurrent;

namespace GeoStudio.Raster
{
    public static partial class GdalOverviewGenerator
    {
        public static event Action<string, string>? OverviewReady;
        private static readonly ConcurrentDictionary<string, bool> _overviewGeneratingPaths = new();

        public static void QueueOverviewGeneration(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath)) return;
            string normPath = Path.GetFullPath(filePath);
            if (!_overviewGeneratingPaths.TryAdd(normPath, true)) return;

            Task.Run(() =>
            {
                try
                {
                    var meta = InspectAndGeneratePreview(normPath, previewWidth: 2048);
                    if (!string.IsNullOrEmpty(meta.PreviewUrl))
                    {
                        OverviewReady?.Invoke(normPath, meta.PreviewUrl);
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Background overview generation error: {ex.Message}");
                }
                finally
                {
                    _overviewGeneratingPaths.TryRemove(normPath, out _);
                }
            });
        }
    }
}
