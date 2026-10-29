using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using OSGeo.GDAL;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI.Dialogs.Terrain
{
    public partial class ViewshedWindow : Window
    {
        private readonly MainWindow _main;
        private readonly List<LayerItem> _rasterLayers;
        private double _demCenterX = 0;
        private double _demCenterY = 0;

        public ViewshedWindow(MainWindow main)
        {
            InitializeComponent();
            _main = main;
            Owner = main;

            _rasterLayers = main.Layers.Where(l => (l.Type == LayerType.Raster || l.Type == LayerType.Elevation) &&
                                                   !string.IsNullOrEmpty(l.FilePath) && File.Exists(l.FilePath)).ToList();

            foreach (var r in _rasterLayers)
            {
                ComboDemSurface.Items.Add(r.Name);
            }

            if (ComboDemSurface.Items.Count > 0)
            {
                ComboDemSurface.SelectedIndex = 0;
            }
            else
            {
                TxtStatus.Text = "No valid elevation DEM raster layers loaded.";
            }
        }

        private void ComboDemSurface_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboDemSurface.SelectedIndex < 0 || ComboDemSurface.SelectedIndex >= _rasterLayers.Count) return;
            var layer = _rasterLayers[ComboDemSurface.SelectedIndex];

            try
            {
                using var ds = Gdal.Open(layer.FilePath, Access.GA_ReadOnly);
                if (ds != null)
                {
                    double[] gt = new double[6];
                    ds.GetGeoTransform(gt);
                    _demCenterX = gt[0] + (ds.RasterXSize * gt[1]) / 2.0;
                    _demCenterY = gt[3] + (ds.RasterYSize * gt[5]) / 2.0;

                    bool isGeo = Math.Abs(_demCenterX) <= 180 && Math.Abs(_demCenterY) <= 90;
                    string fmt = isGeo ? "F6" : "F2";
                    TxtObserverX.Text = _demCenterX.ToString(fmt);
                    TxtObserverY.Text = _demCenterY.ToString(fmt);

                    string dir = Path.GetDirectoryName(layer.FilePath) ?? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
                    string defaultOut = Path.Combine(dir, $"{Path.GetFileNameWithoutExtension(layer.FilePath)}_Viewshed.tif");
                    PickerOutput.PathText = defaultOut;

                    TxtStatus.Text = $"Selected DEM: {layer.Name}. Observer centered.";
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Error inspecting DEM: {ex.Message}";
            }
        }

        private void BtnSetCenter_Click(object sender, RoutedEventArgs e)
        {
            if (_demCenterX != 0 || _demCenterY != 0)
            {
                bool isGeo = Math.Abs(_demCenterX) <= 180 && Math.Abs(_demCenterY) <= 90;
                string fmt = isGeo ? "F6" : "F2";
                TxtObserverX.Text = _demCenterX.ToString(fmt);
                TxtObserverY.Text = _demCenterY.ToString(fmt);
                TxtStatus.Text = "Observer coordinates reset to center of DEM extent.";
            }
        }

        private async void BtnCompute_Click(object sender, RoutedEventArgs e)
        {
            if (ComboDemSurface.SelectedIndex < 0 || ComboDemSurface.SelectedIndex >= _rasterLayers.Count)
            {
                MessageBox.Show("Please select an input DEM elevation raster surface.", "Viewshed Analysis", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var layer = _rasterLayers[ComboDemSurface.SelectedIndex];
            string demPath = layer.FilePath;

            if (!double.TryParse(TxtObserverX.Text, out double obsX) || !double.TryParse(TxtObserverY.Text, out double obsY))
            {
                MessageBox.Show("Please enter valid numeric coordinates for Observer X and Y.", "Coordinate Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            double.TryParse(TxtObserverHeight.Text, out double obsH);
            if (obsH <= 0) obsH = 2.0;

            double.TryParse(TxtTargetHeight.Text, out double tgtH);
            if (tgtH < 0) tgtH = 0.0;

            double.TryParse(TxtMaxDistance.Text, out double maxDist);
            if (maxDist <= 0) maxDist = 5000.0;

            double.TryParse(TxtCurvature.Text, out double curvCoeff);
            if (curvCoeff <= 0) curvCoeff = 0.85714;

            string outPath = PickerOutput.PathText;
            if (string.IsNullOrWhiteSpace(outPath))
            {
                outPath = Path.Combine(Path.GetDirectoryName(demPath) ?? "", $"{Path.GetFileNameWithoutExtension(demPath)}_Viewshed.tif");
                PickerOutput.PathText = outPath;
            }

            var vsParams = new
            {
                observer_x = obsX,
                observer_y = obsY,
                observer_h = obsH,
                target_h = tgtH,
                max_distance = maxDist,
                curvature_coeff = curvCoeff
            };

            string jsonParams = JsonSerializer.Serialize(vsParams);
            TxtStatus.Text = $"Computing line-of-sight viewshed from ({obsX:F1}, {obsY:F1}) radius {maxDist:N0}m...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "viewshed",
                    inputFile: demPath,
                    outputFile: outPath,
                    param1: jsonParams,
                    onProgress: (p, msg) => Dispatcher.Invoke(() => TxtStatus.Text = $"[{p}%] {msg}")
                );

                if (!result.Success)
                {
                    TxtStatus.Text = $"Viewshed failed: {result.ErrorMessage}";
                    MessageBox.Show($"Viewshed computation failed:\n{result.ErrorMessage}", "Viewshed Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // Parse returned results
                if (!string.IsNullOrEmpty(result.OutputData))
                {
                    using var doc = JsonDocument.Parse(result.OutputData);
                    var root = doc.RootElement;
                    double visKm2 = root.TryGetProperty("visible_km2", out var pVk) ? pVk.GetDouble() : 0.0;
                    double visHa = root.TryGetProperty("visible_ha", out var pVh) ? pVh.GetDouble() : 0.0;
                    double totalKm2 = root.TryGetProperty("total_radius_km2", out var pTk) ? pTk.GetDouble() : 0.0;
                    double covPct = root.TryGetProperty("coverage_percentage", out var pCp) ? pCp.GetDouble() : 0.0;
                    TxtStatus.Text = $"Viewshed computation complete! Visible: {visKm2:N2} km² ({covPct:F1}% coverage). Saved to: {Path.GetFileName(outPath)}";
                }
                else
                {
                    TxtStatus.Text = $"Viewshed computation complete! Output saved to: {Path.GetFileName(outPath)}";
                }

                // Add to Map Canvas if checked
                if (ChkAddToCanvas.IsChecked == true && File.Exists(outPath))
                {
                    await _main.LoadRasterFile(outPath);
                    TxtStatus.Text += " (Loaded onto Map Canvas)";
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Execution error: {ex.Message}";
                MessageBox.Show($"An unexpected error occurred: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
