using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI.Dialogs
{
    public partial class ClipRasterWindow : Window
    {
        private readonly MainWindow _main;
        private string? _manualMaskPath;

        public ClipRasterWindow(MainWindow main)
        {
            InitializeComponent();
            _main = main;
            Owner = main;
            _main.ActiveClipRasterWindow = this;
            Closed += (s, e) =>
            {
                _main.ActiveClipRasterWindow = null;
                _main.PostMessageToMap(new { action = "clearClipMask" });
            };

            PopulateLayers();
        }

        private void PopulateLayers()
        {
            PickerRaster.Populate(_main.Layers, l => l.Type == LayerType.Raster || l.Type == LayerType.Elevation);
            PickerMask.Populate(_main.Layers, l => l.Type == LayerType.Vector);
            UpdateDefaultOutputPath();
        }

        private void UpdateDefaultOutputPath()
        {
            PickerOutput.SetAutoPath(PickerRaster.SelectedPath, "_clipped.tif");
        }

        private void PickerRaster_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateDefaultOutputPath();
        }

        private void PickerMask_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _manualMaskPath = null;
            PickerMask.ClearBadge();
        }

        private void BtnDrawPolygon_Click(object sender, RoutedEventArgs e)
        {
            _main.PostMessageToMap(new { action = "setTool", tool = "draw_clip_polygon" });
            ActionBar.StatusText = "✏️ Drawing mode: Click vertices on the map canvas; double-click to complete.";
            PickerMask.ExtraButtonControl.Background = new SolidColorBrush(Color.FromRgb(254, 226, 226));
        }

        public void SetDrawnMask(string filePath, string label)
        {
            _manualMaskPath = filePath;
            PickerMask.AddCustomItem($"[Canvas] {label}", filePath, select: true);
            PickerMask.SetBadge($"✓ {label}");
            PickerMask.ExtraButtonControl.ClearValue(BackgroundProperty);
            ActionBar.StatusText = $"✓ Captured manual boundary: {label}";
        }

        private async void BtnRunClip_Click(object sender, RoutedEventArgs e)
        {
            string? rasterPath = PickerRaster.SelectedPath;
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid input raster dataset.", "Clip Raster", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string? maskPath = !string.IsNullOrEmpty(_manualMaskPath) ? _manualMaskPath : PickerMask.SelectedPath;
            if (string.IsNullOrEmpty(maskPath) || (!File.Exists(maskPath) && !maskPath.Contains(',')))
            {
                MessageBox.Show("Please select a clipping mask, draw one on the canvas, or use the current map extent.", "Clip Raster", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string outputPath = PickerOutput.PathText;
            if (string.IsNullOrEmpty(outputPath))
            {
                MessageBox.Show("Please specify a valid output file path.", "Clip Raster", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            ActionBar.IsBusy = true;
            ActionBar.Progress = 10;
            ActionBar.StatusText = "Running GDAL raster clip by mask...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "clip_raster",
                    inputFile: rasterPath,
                    outputFile: outputPath,
                    param1: maskPath,
                    onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() =>
                        {
                            ActionBar.Progress = pct;
                            ActionBar.StatusText = msg;
                        });
                    });

                if (result.Success && !string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                {
                    ActionBar.Progress = 100;
                    ActionBar.StatusText = "Clip complete! Adding clipped raster to map...";
                    await _main.LoadRasterFile(result.OutputFilePath);
                    Close();
                }
                else
                {
                    ActionBar.IsBusy = false;
                    ActionBar.StatusText = $"Clip failed: {result.ErrorMessage}";
                    MessageBox.Show($"Raster clip failed:\n{result.ErrorMessage}", "Clip Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                ActionBar.IsBusy = false;
                ActionBar.StatusText = $"Error: {ex.Message}";
                MessageBox.Show($"Unexpected error: {ex.Message}", "Clip Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
