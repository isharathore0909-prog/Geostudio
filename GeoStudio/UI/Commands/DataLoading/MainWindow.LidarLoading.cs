using System;
using System.Diagnostics;
using System.IO;
using System.Windows;
using Microsoft.Win32;
using GeoStudio.DuckDB;
using GeoStudio.Models;
using GeoStudio.PointCloud;

namespace GeoStudio
{
    public partial class MainWindow
    {
        internal async void BtnAddLidar_Click(object sender, RoutedEventArgs e)
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
                    _lidarClassifiedWithSmrf = sampleResult.Batch.c != null && System.Linq.Enumerable.Any(sampleResult.Batch.c, c => c >= 3 && c <= 5);
                    _activeLidarClassificationState = null;

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
                        ComboLidarColorBy.SelectedIndex = sampleResult.HasRgb ? 0 : 1;
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
    }
}
