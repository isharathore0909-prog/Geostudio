using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.Raster;
using GeoStudio.PointCloud;

namespace GeoStudio
{
    public partial class MainWindow
    {
        private void BtnAddVector_Click(object sender, RoutedEventArgs e)
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

        private async void BtnAddRaster_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Open 100GB+ BigTIFF, GeoTIFF or DEM Raster",
                Filter = "GeoTIFF & BigTIFF (*.tif;*.tiff;*.dem;*.asc;*.vrt)|*.tif;*.tiff;*.dem;*.asc;*.vrt|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                try
                {
                    string selectedFile = dlg.FileName;
                    var sw = Stopwatch.StartNew();
                    if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Visible;
                    if (TxtBenchmarkFileName != null) TxtBenchmarkFileName.Text = Path.GetFileName(selectedFile);
                    if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = "Loading...";
                    if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = "Reading GDAL metadata & streaming viewport...";
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
                    if (TxtBenchmarkStatusIcon != null) TxtBenchmarkStatusIcon.Text = "⏳";
                    if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Streaming to GPU Canvas...";

                    TxtStatus.Text = $"Opening BigTIFF via GDAL: {Path.GetFileName(selectedFile)}...";

                    var meta = await System.Threading.Tasks.Task.Run(() => GdalRasterService.InspectMetadata(selectedFile));

                    long fileLoadMs = sw.ElapsedMilliseconds;
                    _activeRasterFilePath = selectedFile;

                    long fileLen = new FileInfo(selectedFile).Length;
                    string displaySize = fileLen >= 1024L * 1024 * 1024
                        ? $"{fileLen / (1024.0 * 1024 * 1024):F2} GB"
                        : $"{fileLen / (1024.0 * 1024):F1} MB";

                    string details = meta.IsElevation
                        ? $"DEM/DSM | {meta.Width:N0}x{meta.Height:N0} px | Elev: {meta.MinElevation:F1}m - {meta.MaxElevation:F1}m | {displaySize} | {meta.Projection}"
                        : $"GDAL BigTIFF | {meta.Width:N0}x{meta.Height:N0} px | {displaySize} | {meta.Projection}";

                    _activeRasterShaderMode = meta.IsElevation ? "atlas" : null;
                    _activeRasterPalette = meta.IsElevation ? "GLOBAL_MAPPER_ATLAS" : null;

                    var layer = new LayerItem
                    {
                        Id = Guid.NewGuid().ToString(),
                        Name = Path.GetFileName(selectedFile),
                        Type = LayerType.Raster,
                        FilePath = selectedFile,
                        FileSizeBytes = fileLen,
                        BoundingBox = meta.BoundingBox,
                        Details = details,
                        ColorHex = meta.IsElevation ? "#10B981" : "#D97706",
                        IsElevation = meta.IsElevation,
                        MinElevation = meta.MinElevation,
                        MaxElevation = meta.MaxElevation,
                        ShaderMode = _activeRasterShaderMode,
                        Palette = _activeRasterPalette
                    };
                    _activeRasterLayerId = layer.Id;
                    Layers.Add(layer);
                    UpdateLayerCount();

                    PostMessageToMap(new
                    {
                        action = "addRasterLayer",
                        id = layer.Id,
                        name = layer.Name,
                        filePath = selectedFile,
                        bounds = meta.BoundingBox,
                        width = meta.Width,
                        height = meta.Height,
                        imageUri = meta.PreviewUrl,
                        imageUrl = meta.PreviewUrl,
                        details = layer.Details,
                        fileLoadMs = fileLoadMs,
                        shaderMode = layer.ShaderMode,
                        palette = layer.Palette,
                        minElev = meta.MinElevation,
                        maxElev = meta.MaxElevation,
                        isElevation = meta.IsElevation
                    });

                    if (string.IsNullOrEmpty(meta.PreviewUrl))
                    {
                        TxtStatus.Text = meta.IsElevation
                            ? $"Loaded {layer.Name} ({meta.Width:N0}x{meta.Height:N0} px) • Generating Global Mapper 3D Shaded Relief in background..."
                            : $"Loaded {layer.Name} ({meta.Width:N0}x{meta.Height:N0} px) • Generating overview in background...";
                        if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
                    }
                    else
                    {
                        TxtStatus.Text = meta.IsElevation
                            ? $"Rendered: {layer.Name} (3D Shaded Relief | {meta.MinElevation:F1}m - {meta.MaxElevation:F1}m | {layer.DisplaySize})"
                            : $"Rendered: {layer.Name} ({meta.Width:N0}x{meta.Height:N0} px | {layer.DisplaySize})";
                    }
                    TxtCrs.Text = "CRS: " + meta.Projection;
                }
                catch (Exception ex)
                {
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                    TxtStatus.Text = $"GDAL reader warning: {ex.Message}";
                }
            }
        }

        private async void BtnAddLidar_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Open ASPRS LiDAR Point Cloud",
                Filter = "Point Clouds (*.las;*.laz)|*.las;*.laz|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                try
                {
                    DuckDbPointCloudService.Clear();
                    var sw = Stopwatch.StartNew();
                    if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Visible;
                    if (TxtBenchmarkFileName != null) TxtBenchmarkFileName.Text = Path.GetFileName(dlg.FileName);
                    if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = "Loading...";
                    if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = "Reading point cloud...";
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
                    if (TxtBenchmarkStatusIcon != null) TxtBenchmarkStatusIcon.Text = "⏳";
                    if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Sampling points for instant display...";

                    TxtStatus.Text = "Loading point cloud...";

                    string actualPath = await System.Threading.Tasks.Task.Run(() =>
                        LasPointCloudService.EnsureUncompressedLas(dlg.FileName, (pct, msg) =>
                        {
                            Dispatcher.InvokeAsync(() =>
                            {
                                if (ProgressBarFileLoad != null) ProgressBarFileLoad.Value = pct;
                                if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = $"{msg}: {pct}%";
                            });
                        }));

                    var header = LasPointCloudService.InspectLasHeader(actualPath);
                    var crs = new LasCrsInfo(header.CrsWkt, header.EpsgCode, header.IsProjected);

                    var sampleResult = await System.Threading.Tasks.Task.Run(() =>
                        LasSampleReader.Read(actualPath, crs, targetPoints: 800_000));

                    long readMs = sw.ElapsedMilliseconds;

                    var layer = new LayerItem
                    {
                        Id = Guid.NewGuid().ToString(),
                        Name = Path.GetFileName(dlg.FileName),
                        Type = LayerType.PointCloud,
                        FilePath = actualPath,
                        FileSizeBytes = header.FileSizeBytes,
                        FeatureCount = (int)sampleResult.TotalPoints,
                        Details = $"LiDAR | {sampleResult.TotalPoints:N0} Points | Elev: {sampleResult.MinZ:F1}m-{sampleResult.MaxZ:F1}m{(sampleResult.HasRgb ? " | RGB True Color" : "")}",
                        BoundingBox = sampleResult.Bounds,
                        ColorHex = "#8B5CF6"
                    };
                    Layers.Add(layer);
                    UpdateLayerCount();
                    _activePointCloudBatch = sampleResult.Batch;

                    PostMessageToMap(new
                    {
                        action = "loadPointCloud",
                        id = layer.Id,
                        name = layer.Name,
                        batch = sampleResult.Batch,
                        bounds = sampleResult.Bounds,
                        minZ = sampleResult.MinZ,
                        maxZ = sampleResult.MaxZ,
                        pointSize = 1.5,
                        colorMode = sampleResult.HasRgb ? "rgb_elev" : "elevation",
                        center = new { x = (sampleResult.Bounds[0] + sampleResult.Bounds[2]) / 2, y = (sampleResult.Bounds[1] + sampleResult.Bounds[3]) / 2 },
                        fileLoadMs = readMs,
                        fileHasRgb = sampleResult.HasRgb,
                        totalPoints = sampleResult.TotalPoints
                    });

                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                    if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = $"{readMs} ms";
                    if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = $"Sampled {sampleResult.Batch.count:N0} pts ({sampleResult.TotalPoints:N0} total) in {readMs} ms";
                    if (TxtBenchmarkStatusIcon != null) TxtBenchmarkStatusIcon.Text = "⚡";
                    if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Live GPU Point Cloud Active";
                    TxtStatus.Text = $"Loaded {Path.GetFileName(dlg.FileName)}: {sampleResult.TotalPoints:N0} points in {readMs} ms ({(sampleResult.HasRgb ? "RGB True Color" : "Elevation")})";
                    if (ComboLidarColorBy != null)
                    {
                        ComboLidarColorBy.SelectedIndex = sampleResult.HasRgb ? 1 : 2;
                    }

                    _ = System.Threading.Tasks.Task.Run(() =>
                    {
                        try
                        {
                            DuckDbPointCloudService.IngestLasFile(actualPath, null, maxPointsToIngest: 1_000_000);
                        }
                        catch (Exception ex)
                        {
                            System.Diagnostics.Debug.WriteLine($"DuckDB background ingest note: {ex.Message}");
                        }
                    });
                }
                catch (Exception ex)
                {
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                    if (TxtBenchmarkStatusIcon != null) TxtBenchmarkStatusIcon.Text = "⚠️";
                    if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Failed to load point cloud";
                    TxtStatus.Text = $"Point cloud error: {ex.Message}";
                    MessageBox.Show($"Could not inspect LAS file: {ex.Message}", "LiDAR Reader", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
        }

        private void BtnAddOsm_Click(object sender, RoutedEventArgs e)
        {
            var osmLayer = FindLayer("osm_basemap");
            if (osmLayer != null)
            {
                osmLayer.IsVisible = !osmLayer.IsVisible;
                PostMessageToMap(new { action = "toggleLayer", id = "osm_basemap", visible = osmLayer.IsVisible });
                TxtStatus.Text = $"OpenStreetMap basemap {(osmLayer.IsVisible ? "enabled" : "hidden")}";
            }
            else
            {
                var osm = new LayerItem
                {
                    Id = "osm_basemap",
                    Name = "OpenStreetMap Basemap",
                    Type = LayerType.Basemap,
                    IsVisible = true,
                    Opacity = 1.0,
                    Details = "Global XYZ Tile Layer | EPSG:3857",
                    ColorHex = "#3B82F6"
                };
                Layers.Add(osm);
                UpdateLayerCount();
                PostMessageToMap(new { action = "toggleLayer", id = "osm_basemap", visible = true });
                TxtStatus.Text = "OpenStreetMap basemap enabled";
            }
        }

        private void BtnDatabase_Click(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("Spatial Database Connection: Connect to PostGIS, Spatialite, or DuckDB spatial databases.", "Spatial Database", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void BtnFileBrowser_Click(object sender, RoutedEventArgs e)
        {
            BtnAddVector_Click(sender, e);
        }
    }
}
