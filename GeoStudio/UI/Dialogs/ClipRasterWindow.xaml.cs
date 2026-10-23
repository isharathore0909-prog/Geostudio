using System;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI.Dialogs
{
    public partial class ClipRasterWindow : Window
    {
        private readonly MainWindow _main;
        private string? _customRasterPath;
        private string? _customMaskPath;

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
            ComboRasterLayer.Items.Clear();
            ComboMaskLayer.Items.Clear();

            foreach (var l in _main.Layers.Where(x => x.Type == LayerType.Raster || x.Type == LayerType.Elevation))
            {
                ComboRasterLayer.Items.Add(new ComboBoxItem { Content = l.Name, Tag = l.FilePath });
            }

            foreach (var l in _main.Layers.Where(x => x.Type == LayerType.Vector))
            {
                ComboMaskLayer.Items.Add(new ComboBoxItem { Content = l.Name, Tag = l.FilePath });
            }

            if (ComboRasterLayer.Items.Count > 0)
                ComboRasterLayer.SelectedIndex = 0;
            if (ComboMaskLayer.Items.Count > 0)
                ComboMaskLayer.SelectedIndex = 0;

            UpdateDefaultOutputPath();
        }

        private void UpdateDefaultOutputPath()
        {
            string? rasterPath = GetSelectedRasterPath();
            if (!string.IsNullOrEmpty(rasterPath))
            {
                string dir = Path.GetDirectoryName(rasterPath) ?? AppDomain.CurrentDomain.BaseDirectory;
                string baseName = Path.GetFileNameWithoutExtension(rasterPath);
                TxtOutputPath.Text = Path.Combine(dir, $"{baseName}_clipped.tif");
            }
        }

        private string? GetSelectedRasterPath()
        {
            if (!string.IsNullOrEmpty(_customRasterPath)) return _customRasterPath;
            if (ComboRasterLayer.SelectedItem is ComboBoxItem item && item.Tag is string path)
                return path;
            return null;
        }

        private string? GetSelectedMaskPath()
        {
            if (!string.IsNullOrEmpty(_customMaskPath)) return _customMaskPath;
            if (ComboMaskLayer.SelectedItem is ComboBoxItem item && item.Tag is string path)
                return path;
            return null;
        }

        private void ComboRasterLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _customRasterPath = null;
            UpdateDefaultOutputPath();
        }

        private void ComboMaskLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _customMaskPath = null;
            if (BadgeMaskStatus != null)
                BadgeMaskStatus.Visibility = Visibility.Collapsed;
        }

        private void BtnBrowseRaster_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Select Input Raster Dataset",
                Filter = "GeoTIFF & BigTIFF (*.tif;*.tiff;*.dem;*.vrt)|*.tif;*.tiff;*.dem;*.vrt|All Files (*.*)|*.*"
            };
            if (dlg.ShowDialog() == true)
            {
                _customRasterPath = dlg.FileName;
                ComboRasterLayer.Items.Insert(0, new ComboBoxItem { Content = $"[File] {Path.GetFileName(dlg.FileName)}", Tag = dlg.FileName, IsSelected = true });
                UpdateDefaultOutputPath();
            }
        }

        private void BtnBrowseMask_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Select Clipping Mask Vector",
                Filter = "Vector Layers (*.geojson;*.json;*.shp;*.gpkg;*.kml)|*.geojson;*.json;*.shp;*.gpkg;*.kml|All Files (*.*)|*.*"
            };
            if (dlg.ShowDialog() == true)
            {
                _customMaskPath = dlg.FileName;
                ComboMaskLayer.Items.Insert(0, new ComboBoxItem { Content = $"[File] {Path.GetFileName(dlg.FileName)}", Tag = dlg.FileName, IsSelected = true });
            }
        }

        private void BtnDrawPolygon_Click(object sender, RoutedEventArgs e)
        {
            _main.PostMessageToMap(new { action = "setTool", tool = "draw_clip_polygon" });
            TxtStatus.Text = "✏️ Drawing mode: Click vertices on the map canvas; double-click to complete.";
            BtnDrawPolygon.Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(254, 226, 226));
        }

        public void SetDrawnMask(string filePath, string label)
        {
            _customMaskPath = filePath;
            var item = new ComboBoxItem { Content = $"[Canvas] {label}", Tag = filePath, IsSelected = true };
            ComboMaskLayer.Items.Insert(0, item);
            ComboMaskLayer.SelectedItem = item;

            if (BadgeMaskStatus != null)
            {
                BadgeMaskStatus.Visibility = Visibility.Visible;
                TxtMaskBadge.Text = $"✓ {label}";
            }

            BtnDrawPolygon.ClearValue(BackgroundProperty);
            TxtStatus.Text = $"✓ Captured manual boundary: {label}";
        }

        private void BtnBrowseOutput_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new SaveFileDialog
            {
                Title = "Save Clipped GeoTIFF",
                Filter = "GeoTIFF (*.tif)|*.tif|All Files (*.*)|*.*",
                FileName = Path.GetFileName(TxtOutputPath.Text.Trim())
            };
            if (dlg.ShowDialog() == true)
            {
                TxtOutputPath.Text = dlg.FileName;
            }
        }

        private async void BtnRunClip_Click(object sender, RoutedEventArgs e)
        {
            string? rasterPath = GetSelectedRasterPath();
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid input raster dataset.", "Clip Raster", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string? maskPath = GetSelectedMaskPath();
            if (string.IsNullOrEmpty(maskPath) || (!File.Exists(maskPath) && !maskPath.Contains(',')))
            {
                MessageBox.Show("Please select a clipping mask, draw one on the canvas, or use the current map extent.", "Clip Raster", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string outputPath = TxtOutputPath.Text.Trim();
            if (string.IsNullOrEmpty(outputPath))
            {
                MessageBox.Show("Please specify a valid output file path.", "Clip Raster", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            BtnRunClip.IsEnabled = false;
            ProgressClip.Visibility = Visibility.Visible;
            ProgressClip.Value = 10;
            TxtStatus.Text = "Running GDAL raster clip by mask...";

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
                            ProgressClip.Value = pct;
                            TxtStatus.Text = msg;
                        });
                    });

                if (result.Success && !string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                {
                    ProgressClip.Value = 100;
                    TxtStatus.Text = "Clip complete! Adding clipped raster to map...";
                    await _main.LoadRasterFile(result.OutputFilePath);
                    Close();
                }
                else
                {
                    ProgressClip.Visibility = Visibility.Collapsed;
                    TxtStatus.Text = $"Clip failed: {result.ErrorMessage}";
                    MessageBox.Show($"Raster clip failed:\n{result.ErrorMessage}", "Clip Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    BtnRunClip.IsEnabled = true;
                }
            }
            catch (Exception ex)
            {
                ProgressClip.Visibility = Visibility.Collapsed;
                TxtStatus.Text = $"Error: {ex.Message}";
                MessageBox.Show($"Unexpected error: {ex.Message}", "Clip Error", MessageBoxButton.OK, MessageBoxImage.Error);
                BtnRunClip.IsEnabled = true;
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
