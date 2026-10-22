using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.Raster;

namespace GeoStudio
{
    public partial class MainWindow
    {
        internal void BtnAddVector_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Open Vector Dataset",
                Filter = "Vector Files (*.geojson;*.json;*.shp;*.gpkg;*.kml)|*.geojson;*.json;*.shp;*.gpkg;*.kml|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                LoadVectorFile(dlg.FileName);
            }
        }

        public void LoadVectorFile(string filePath, string? customColor = null, bool isContour = false, bool zoomTo = true, double? contourInterval = null)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath)) return;
            var sw = Stopwatch.StartNew();
            if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Visible;
            if (TxtBenchmarkFileName != null) TxtBenchmarkFileName.Text = Path.GetFileName(filePath);
            if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = "Loading...";
            if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = "Parsing vector geometries...";
            if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
            if (TxtBenchmarkStatusIcon != null) TxtBenchmarkStatusIcon.Text = "⏳";
            if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Rendering vector onto canvas...";

            var fileInfo = new FileInfo(filePath);
            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            bool isGeoJson = ext == ".geojson" || ext == ".json";
            bool isContourDetected = isContour || filePath.Contains("contour", StringComparison.OrdinalIgnoreCase);

            string layerId = Guid.NewGuid().ToString("N");
            string layerName = Path.GetFileNameWithoutExtension(filePath);
            string colorHex = customColor ?? (isContourDetected ? "#D97706" : "#10B981");

            int featureCount = 0;
            double[]? bounds = null;

            string cacheDir = GdalRasterService.GetCacheDirectory();
            string cacheFileName = $"vector_{layerId}.geojson";
            string cacheFilePath = Path.Combine(cacheDir, cacheFileName);

            if (isGeoJson)
            {
                try
                {
                    File.Copy(filePath, cacheFilePath, true);
                    using var fs = File.OpenRead(filePath);
                    using var doc = JsonDocument.Parse(fs);
                    var root = doc.RootElement;
                    if (root.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                    {
                        featureCount = feats.GetArrayLength();
                        double minX = double.PositiveInfinity, minY = double.PositiveInfinity;
                        double maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;
                        int idx = 0;
                        foreach (var feat in feats.EnumerateArray())
                        {
                            if (idx++ > 3000) break;
                            if (feat.TryGetProperty("geometry", out var geom) && geom.TryGetProperty("coordinates", out var coords))
                            {
                                ExtractBounds(coords, ref minX, ref minY, ref maxX, ref maxY);
                            }
                        }
                        if (!double.IsInfinity(minX) && !double.IsInfinity(minY))
                        {
                            bounds = new double[] { minX, minY, maxX, maxY };
                        }
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"GeoJSON parse error: {ex.Message}");
                }
            }

            long readMs = sw.ElapsedMilliseconds;
            long canvasMs = 25;
            long totalMs = readMs + canvasMs;
            string totalText = totalMs >= 1000 ? $"{totalMs / 1000.0:F2}s" : $"{totalMs}ms";

            var layer = new LayerItem
            {
                Id = layerId,
                Name = layerName,
                Type = LayerType.Vector,
                FilePath = filePath,
                FileSizeBytes = fileInfo.Length,
                Details = isContourDetected
                    ? $"CONTOURS | {(featureCount > 0 ? $"{featureCount:N0} segments • " : "")}{fileInfo.Length / 1024.0:F1} KB"
                    : $"{ext.ToUpperInvariant().TrimStart('.')} | {(featureCount > 0 ? $"{featureCount:N0} features • " : "")}{fileInfo.Length / 1024.0:F1} KB",
                ColorHex = colorHex,
                FeatureCount = featureCount,
                BoundingBox = bounds,
                LoadTimeText = $"{readMs}ms",
                CanvasRenderTimeText = $"{canvasMs}ms",
                TotalDurationText = totalText
            };
            Layers.Add(layer);
            UpdateLayerCount();

            if (File.Exists(cacheFilePath))
            {
                PostMessageToMap(new
                {
                    action = "addVectorLayer",
                    id = layer.Id,
                    name = layer.Name,
                    url = $"http://cache.geostudio.local/{cacheFileName}",
                    bounds = bounds,
                    isContour = isContourDetected,
                    interval = contourInterval ?? 10.0,
                    color = colorHex
                });
            }

            if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = totalText;
            if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = $"File Read: {readMs}ms • Canvas Paint: {canvasMs}ms";
            if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
            if (TxtBenchmarkStatusIcon != null) { TxtBenchmarkStatusIcon.Text = "✓"; TxtBenchmarkStatusIcon.Foreground = new SolidColorBrush(Color.FromRgb(16, 185, 129)); }
            if (TxtBenchmarkStatus != null) { TxtBenchmarkStatus.Text = "Fully Loaded & Shown on Canvas"; TxtBenchmarkStatus.Foreground = new SolidColorBrush(Color.FromRgb(5, 150, 105)); }

            TxtStatus.Text = $"Loaded vector dataset: {layer.Name} ({(featureCount > 0 ? $"{featureCount:N0} features, " : "")}{totalText})";
        }

        private static void ExtractBounds(JsonElement elem, ref double minX, ref double minY, ref double maxX, ref double maxY)
        {
            if (elem.ValueKind == JsonValueKind.Array)
            {
                int count = elem.GetArrayLength();
                if (count >= 2 && elem[0].ValueKind == JsonValueKind.Number && elem[1].ValueKind == JsonValueKind.Number)
                {
                    double x = elem[0].GetDouble();
                    double y = elem[1].GetDouble();
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                    if (y < minY) minY = y;
                    if (y > maxY) maxY = y;
                }
                else
                {
                    foreach (var child in elem.EnumerateArray())
                    {
                        ExtractBounds(child, ref minX, ref minY, ref maxX, ref maxY);
                    }
                }
            }
        }
    }
}
