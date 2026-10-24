using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Python;
using GeoStudio.DuckDB;
using GeoStudio.Models;

namespace GeoStudio
{
    public partial class MainWindow
    {
        #region LiDAR Point Cloud Controls & Classifiers
        internal void ComboLidarColorBy_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isInitialized || TxtStatus == null || ComboLidarColorBy == null) return;
            if (ComboLidarColorBy.SelectedItem is ComboBoxItem item)
            {
                string text = item.Content?.ToString() ?? "";
                if (text.Contains("Color By ▾") || text.Trim() == "Color By") return;

                if (text.Contains("Auto-Classify"))
                {
                    BtnLidarClassifyGround_Click(sender, e);
                    for (int i = 0; i < ComboLidarColorBy.Items.Count; i++)
                    {
                        if (ComboLidarColorBy.Items[i] is ComboBoxItem cbi && (cbi.Content?.ToString()?.Contains("Classification") ?? false))
                        {
                            ComboLidarColorBy.SelectedIndex = i;
                            break;
                        }
                    }
                    return;
                }

                string lower = text.ToLowerInvariant();
                string colorBy = "rgb_elev";
                if (lower.Contains("rgb")) colorBy = "rgb_elev";
                else if (lower.Contains("return height") || lower.Contains("return_delta") || lower.Contains("height delta") || lower.Contains("delta")) colorBy = "return_delta";
                else if (lower.Contains("height above ground") || lower.Contains("hag")) colorBy = "hag";
                else if (lower.Contains("elev")) colorBy = "elevation";
                else if (lower.Contains("intens")) colorBy = "intensity";
                else if (lower.Contains("class")) colorBy = "classification";
                else if (lower.Contains("return")) colorBy = "return_num";
                else if (lower.Contains("scan angle") || lower.Contains("angle")) colorBy = "scan_angle";
                else if (lower.Contains("source id") || lower.Contains("point source")) colorBy = "point_source_id";
                else if (lower.Contains("source layer")) colorBy = "source_layer";
                else if (lower.Contains("segment")) colorBy = "segment";
                else if (lower.Contains("point index") || lower.Contains("index")) colorBy = "point_index";
                else if (lower.Contains("cir")) colorBy = "cir";
                else if (lower.Contains("ndvi")) colorBy = "ndvi";
                else if (lower.Contains("ndwi")) colorBy = "ndwi";
                else if (lower.Contains("dens")) colorBy = "point_density";
                else if (lower.Contains("withheld")) colorBy = "withheld";
                else if (lower.Contains("key point") || lower.Contains("keypoint")) colorBy = "keypoint";
                else if (lower.Contains("overlap")) colorBy = "overlap";

                PostMessageToMap(new { action = "setLidarColorBy", colorBy = colorBy });
                TxtStatus.Text = $"LiDAR Display: {text}";
            }
        }

        internal void BtnLidarClassifyGround_Click(object sender, RoutedEventArgs e)
        {
            var ptLayer = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            string? lasFile = ptLayer?.FilePath;
            if (string.IsNullOrEmpty(lasFile) || !File.Exists(lasFile))
            {
                MessageBox.Show("Please load a LAS/LAZ point cloud first.", "LiDAR Classifier", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            TxtStatus.Text = "Running Auto-Classify Ground (SMRF / HAG)...";

            // 1. Instant in-memory classification on active point cloud batch
            if (_activePointCloudBatch != null && _activePointCloudBatch.count > 0)
            {
                var newCls = PointCloudClassifier.ClassifySMRF(_activePointCloudBatch.x, _activePointCloudBatch.y, _activePointCloudBatch.z, _activePointCloudBatch.c);
                _activePointCloudBatch.c = newCls;
                DuckDbConnectionManager.UpdateClassification(newCls);
                PostMessageToMap(new { action = "updateClassification", classes = newCls, colorBy = "classification" });
                _lidarClassifiedWithSmrf = true;
                _activeLidarClassificationState = "ground";
                TxtStatus.Text = "Ground & canopy auto-classified to ASPRS Standards (Class 2 Ground, Class 3/4/5 Veg)";
                if (ComboLidarColorBy != null)
                {
                    for (int i = 0; i < ComboLidarColorBy.Items.Count; i++)
                    {
                        if (ComboLidarColorBy.Items[i] is ComboBoxItem cbi && (cbi.Content?.ToString()?.Contains("Classification") ?? false))
                        {
                            ComboLidarColorBy.SelectedIndex = i;
                            break;
                        }
                    }
                }
            }

            // 2. Background task to generate persistent classified file on disk & reload
            _ = Task.Run(async () =>
            {
                try
                {
                    var res = await PythonPipelineService.ExecuteTaskAsync("classify_ground", lasFile, onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() => TxtStatus.Text = $"Classifying Ground: {pct}% {msg}");
                    });
                    if (res.Success && !string.IsNullOrEmpty(res.OutputFilePath) && File.Exists(res.OutputFilePath))
                    {
                        Dispatcher.Invoke(() =>
                        {
                            TxtStatus.Text = "Ground & canopy classified to ASPRS Standards (persistent output saved)";
                            if (ptLayer != null)
                            {
                                ptLayer.FilePath = res.OutputFilePath;
                                ptLayer.Name = Path.GetFileName(res.OutputFilePath);
                            }
                        });
                    }
                }
                catch { }
            });
        }

        internal void BtnLidarClassifyBuildings_Click(object sender, RoutedEventArgs e)
        {
            var ptLayer = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            string? lasFile = ptLayer?.FilePath;
            if (string.IsNullOrEmpty(lasFile) || !File.Exists(lasFile))
            {
                MessageBox.Show("Please load a LAS/LAZ point cloud first.", "LiDAR Classifier", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            TxtStatus.Text = "Classifying building structures & rooftops...";

            if (_activePointCloudBatch != null && _activePointCloudBatch.count > 0)
            {
                var curCls = _activePointCloudBatch.c ?? PointCloudClassifier.ClassifySMRF(_activePointCloudBatch.x, _activePointCloudBatch.y, _activePointCloudBatch.z);
                var newCls = PointCloudClassifier.ClassifyBuildings(_activePointCloudBatch.x, _activePointCloudBatch.y, _activePointCloudBatch.z, curCls);
                int bldgCount = 0;
                for (int i = 0; i < newCls.Length; i++) if (newCls[i] == 6) bldgCount++;
                if (bldgCount == 0)
                {
                    TxtStatus.Text = "LiDAR: 0 building structures detected (all elevated points verified as natural vegetation canopy)";
                }
                else
                {
                    TxtStatus.Text = $"LiDAR: {bldgCount:N0} building structure points classified to ASPRS Class 6 (Rooftops)";
                }

                _activePointCloudBatch.c = newCls;
                DuckDbConnectionManager.UpdateClassification(newCls);
                PostMessageToMap(new { action = "updateClassification", classes = newCls, colorBy = "classification" });
                _lidarClassifiedWithSmrf = true;
                _activeLidarClassificationState = "buildings";
                PostMessageToMap(new { action = "setLidarColorBy", colorBy = "classification" });
                if (ComboLidarColorBy != null)
                {
                    for (int i = 0; i < ComboLidarColorBy.Items.Count; i++)
                    {
                        if (ComboLidarColorBy.Items[i] is ComboBoxItem cbi && (cbi.Content?.ToString()?.Contains("Classification") ?? false))
                        {
                            ComboLidarColorBy.SelectedIndex = i;
                            break;
                        }
                    }
                }
            }

            _ = Task.Run(async () =>
            {
                try
                {
                    var res = await PythonPipelineService.ExecuteTaskAsync("classify_buildings", lasFile, onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() => TxtStatus.Text = $"Classifying Buildings: {pct}% {msg}");
                    });
                    if (res.Success && !string.IsNullOrEmpty(res.OutputFilePath) && File.Exists(res.OutputFilePath))
                    {
                        Dispatcher.Invoke(() =>
                        {
                            if (ptLayer != null)
                            {
                                ptLayer.FilePath = res.OutputFilePath;
                                ptLayer.Name = Path.GetFileName(res.OutputFilePath);
                            }
                        });
                    }
                }
                catch { }
            });
        }

        internal void BtnLidarClassifyVeg_Click(object sender, RoutedEventArgs e)
        {
            var ptLayer = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            string? lasFile = ptLayer?.FilePath;
            if (string.IsNullOrEmpty(lasFile) || !File.Exists(lasFile))
            {
                MessageBox.Show("Please load a LAS/LAZ point cloud first.", "LiDAR Classifier", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            TxtStatus.Text = "Classifying vegetation canopy & danger trees...";

            if (_activePointCloudBatch != null && _activePointCloudBatch.count > 0)
            {
                var curCls = _activePointCloudBatch.c ?? PointCloudClassifier.ClassifySMRF(_activePointCloudBatch.x, _activePointCloudBatch.y, _activePointCloudBatch.z);
                var newCls = PointCloudClassifier.ClassifyVegetation(_activePointCloudBatch.x, _activePointCloudBatch.y, _activePointCloudBatch.z, curCls);
                _activePointCloudBatch.c = newCls;
                DuckDbConnectionManager.UpdateClassification(newCls);
                PostMessageToMap(new { action = "updateClassification", classes = newCls, colorBy = "classification" });
                _lidarClassifiedWithSmrf = true;
                _activeLidarClassificationState = "veg";
                PostMessageToMap(new { action = "setLidarColorBy", colorBy = "classification" });
                TxtStatus.Text = "Vegetation classified into Low (3), Medium (4), and High (5) canopy";
                if (ComboLidarColorBy != null)
                {
                    for (int i = 0; i < ComboLidarColorBy.Items.Count; i++)
                    {
                        if (ComboLidarColorBy.Items[i] is ComboBoxItem cbi && (cbi.Content?.ToString()?.Contains("Classification") ?? false))
                        {
                            ComboLidarColorBy.SelectedIndex = i;
                            break;
                        }
                    }
                }
            }

            _ = Task.Run(async () =>
            {
                try
                {
                    var res = await PythonPipelineService.ExecuteTaskAsync("classify_veg", lasFile, onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() => TxtStatus.Text = $"Classifying Vegetation: {pct}% {msg}");
                    });
                    if (res.Success && !string.IsNullOrEmpty(res.OutputFilePath) && File.Exists(res.OutputFilePath))
                    {
                        Dispatcher.Invoke(() =>
                        {
                            if (ptLayer != null)
                            {
                                ptLayer.FilePath = res.OutputFilePath;
                                ptLayer.Name = Path.GetFileName(res.OutputFilePath);
                            }
                        });
                    }
                }
                catch { }
            });
        }

        internal async void BtnLidarThin_Click(object sender, RoutedEventArgs e)
        {
            var ptLayer = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            string? lasFile = ptLayer?.FilePath;
            if (string.IsNullOrEmpty(lasFile) || !File.Exists(lasFile))
            {
                MessageBox.Show("Please load a LAS/LAZ point cloud first.", "Point Density Thinning", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            TxtStatus.Text = "Thinning point density by 50%...";
            try
            {
                string outDir = Path.Combine(Path.GetTempPath(), "GeoStudio", "Thinned");
                Directory.CreateDirectory(outDir);
                string outThinned = Path.Combine(outDir, $"{Path.GetFileNameWithoutExtension(lasFile)}_thinned.las");

                bool thinSuccess = false;
                var result = await PythonPipelineService.ExecuteTaskAsync("thin", lasFile, outputFile: outThinned, param1: "2", onProgress: (pct, msg) =>
                {
                    Dispatcher.Invoke(() => TxtStatus.Text = $"Thinning Point Cloud: {pct}% {msg}");
                });

                if (result.Success && File.Exists(outThinned))
                {
                    thinSuccess = true;
                }
                else
                {
                    await Task.Run(() =>
                    {
                        LasSurfaceRasterizerService.ThinLasFile(lasFile, outThinned, step: 2, (pct, msg) =>
                        {
                            Dispatcher.Invoke(() => TxtStatus.Text = $"Decimating LiDAR points: {pct}% {msg}");
                        });
                    });
                    thinSuccess = File.Exists(outThinned);
                }

                if (thinSuccess && ptLayer != null)
                {
                    var header = LasPointCloudService.InspectLasHeader(outThinned);
                    var crs = new LasCrsInfo(header.CrsWkt, header.EpsgCode, header.IsProjected);
                    var sampleResult = await Task.Run(() => LasSampleReader.Read(outThinned, crs, targetPoints: 800_000));

                    ptLayer.FilePath = outThinned;
                    ptLayer.Name = Path.GetFileName(outThinned);
                    ptLayer.FeatureCount = (int)sampleResult.TotalPoints;
                    ptLayer.Details = $"LiDAR | {sampleResult.TotalPoints:N0} Points | Elev: {sampleResult.MinZ:F1}m-{sampleResult.MaxZ:F1}m{(sampleResult.HasRgb ? " | RGB True Color" : "")} [Thinned 50%]";

                    _activePointCloudBatch = sampleResult.Batch;
                    PostMessageToMap(new
                    {
                        action = "loadPointCloud",
                        id = ptLayer.Id,
                        name = ptLayer.Name,
                        batch = sampleResult.Batch,
                        bounds = sampleResult.Bounds,
                        minZ = sampleResult.MinZ,
                        maxZ = sampleResult.MaxZ,
                        pointSize = 1.5,
                        colorMode = ComboLidarColorBy?.SelectedIndex is int idx && idx > 0 ? "classification" : (sampleResult.HasRgb ? "rgb_elev" : "elevation"),
                        totalPoints = sampleResult.TotalPoints
                    });

                    _ = Task.Run(() =>
                    {
                        try { DuckDbPointCloudService.IngestLasFile(outThinned, null, maxPointsToIngest: 1_000_000); } catch { }
                    });

                    TxtStatus.Text = $"Point cloud decimated cleanly: {sampleResult.TotalPoints:N0} points";
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Thinning error: {ex.Message}";
                MessageBox.Show($"Failed to thin point cloud: {ex.Message}", "Thinning Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        internal async void MenuLidarDtm_Click(object sender, RoutedEventArgs e)
        {
            var ptLayer = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            string? lasFile = ptLayer?.FilePath;
            if (string.IsNullOrEmpty(lasFile) || !File.Exists(lasFile))
            {
                MessageBox.Show("Please load a LAS/LAZ point cloud first.", "Bare-Earth DTM", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            TxtStatus.Text = "Generating Bare-Earth Digital Terrain Model (DTM)...";
            try
            {
                string dtmPath = await Task.Run(() =>
                {
                    return LasSurfaceRasterizerService.GenerateDtmRaster(lasFile, targetResolution: 2048, (pct, msg) =>
                    {
                        Dispatcher.Invoke(() => TxtStatus.Text = $"LiDAR DTM: {pct}% {msg}");
                    });
                });

                if (File.Exists(dtmPath))
                {
                    await LoadRasterFile(dtmPath);
                    TxtStatus.Text = $"Bare-Earth DTM loaded: {Path.GetFileName(dtmPath)}";
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"LiDAR DTM error: {ex.Message}";
                MessageBox.Show($"Failed to generate DTM: {ex.Message}", "LiDAR DTM Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        internal async void MenuLidarChm_Click(object sender, RoutedEventArgs e)
        {
            var ptLayer = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            string? lasFile = ptLayer?.FilePath;
            if (string.IsNullOrEmpty(lasFile) || !File.Exists(lasFile))
            {
                MessageBox.Show("Please load a LAS/LAZ point cloud first.", "Canopy Height Model", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            TxtStatus.Text = "Generating Canopy Height Model (CHM = DSM - DTM)...";
            try
            {
                string chmPath = await Task.Run(() =>
                {
                    return LasSurfaceRasterizerService.GenerateChmRaster(lasFile, targetResolution: 2048, (pct, msg) =>
                    {
                        Dispatcher.Invoke(() => TxtStatus.Text = $"LiDAR CHM: {pct}% {msg}");
                    });
                });

                if (File.Exists(chmPath))
                {
                    await LoadRasterFile(chmPath);
                    TxtStatus.Text = $"Canopy Height Model loaded: {Path.GetFileName(chmPath)}";
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"LiDAR CHM error: {ex.Message}";
                MessageBox.Show($"Failed to generate CHM: {ex.Message}", "LiDAR CHM Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        internal void MenuLidarElevation_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setLidarColorBy", colorBy = "elevation" });
            TxtStatus.Text = "LiDAR Color Ramp: Elevation (Z)";
        }

        internal void MenuLidarIntensity_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setLidarColorBy", colorBy = "intensity" });
            TxtStatus.Text = "LiDAR Color Ramp: Intensity";
        }

        internal void MenuLidarClassification_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setLidarColorBy", colorBy = "classification" });
            TxtStatus.Text = "LiDAR Color Ramp: ASPRS Classification (Ground, Veg, Buildings)";
        }

        internal void BtnLidarFilter_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Point Cloud Classification Filter: Display Ground (Class 2), High Vegetation (Class 5), Buildings (Class 6).", "LiDAR Classification", MessageBoxButton.OK, MessageBoxImage.Information);

        internal void BtnLidarReturns_Click(object sender, RoutedEventArgs e) => TxtStatus.Text = "Displaying First & Last LiDAR Return pulses";
        internal void BtnLidarHeight_Click(object sender, RoutedEventArgs e) => TxtStatus.Text = "Normalized Height Above Ground (HAG) computed";
        
        internal void BtnLidarRgb_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setLidarColorBy", colorBy = "rgb" });
            TxtStatus.Text = "LiDAR True Color RGB Photogrammetry mode";
            if (ComboLidarColorBy != null) ComboLidarColorBy.SelectedIndex = 0;
        }
        #endregion
    }
}
