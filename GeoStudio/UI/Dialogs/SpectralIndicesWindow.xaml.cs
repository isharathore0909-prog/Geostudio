using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.Python;
using GeoStudio.Raster;

namespace GeoStudio.UI.Dialogs
{
    public partial class SpectralIndicesWindow : Window
    {
        private readonly MainWindow _main;
        private string? _customRasterPath;
        private string _activeMode = "NDVI";
        private bool _isUpdatingPreset = false;

        public SpectralIndicesWindow(MainWindow main, string defaultMode = "NDVI")
        {
            InitializeComponent();
            _main = main;
            Owner = main;
            _main.ActiveSpectralIndicesWindow = this;
            Closed += (s, e) =>
            {
                if (_main.ActiveSpectralIndicesWindow == this)
                    _main.ActiveSpectralIndicesWindow = null;
            };

            PopulateLayers();
            SetMode(defaultMode);
        }

        public void SetMode(string mode)
        {
            _activeMode = mode.ToUpperInvariant();
            if (ComboIndexMode == null) return;

            foreach (ComboBoxItem item in ComboIndexMode.Items)
            {
                if (item.Tag is string tag && tag.Equals(_activeMode, StringComparison.OrdinalIgnoreCase))
                {
                    ComboIndexMode.SelectedItem = item;
                    break;
                }
            }

            UpdateModeUI();
            UpdateDefaultOutputPath();
        }

        private void PopulateLayers()
        {
            if (ComboRasterLayer == null) return;
            ComboRasterLayer.Items.Clear();

            foreach (var l in _main.Layers.Where(x => x.Type == LayerType.Raster || x.Type == LayerType.Elevation))
            {
                ComboRasterLayer.Items.Add(new ComboBoxItem { Content = l.Name, Tag = l.FilePath });
            }

            if (ComboRasterLayer.Items.Count > 0)
                ComboRasterLayer.SelectedIndex = 0;

            InspectCurrentRaster();
            UpdateDefaultOutputPath();
        }

        private void InspectCurrentRaster()
        {
            string? rasterPath = GetSelectedRasterPath();
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                if (BadgeBands != null) BadgeBands.Visibility = Visibility.Collapsed;
                return;
            }

            try
            {
                var meta = GdalRasterService.InspectMetadata(rasterPath);
                if (meta.BandCount > 1)
                {
                    BadgeBands.Visibility = Visibility.Visible;
                    TxtBandsBadge.Text = $"✓ {meta.BandCount} Bands Detected (Multispectral)";
                    TxtBandsBadge.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
                    BadgeBands.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ECFDF5"));

                    // Auto-adjust preset if 4 bands
                    if (meta.BandCount == 4 && ComboSensorPreset != null)
                    {
                        foreach (ComboBoxItem item in ComboSensorPreset.Items)
                        {
                            if (item.Tag is string tag && tag == "planetscope")
                            {
                                ComboSensorPreset.SelectedItem = item;
                                break;
                            }
                        }
                    }
                }
                else
                {
                    BadgeBands.Visibility = Visibility.Visible;
                    TxtBandsBadge.Text = "Single Band Raster (Indices need multi-band imagery)";
                    TxtBandsBadge.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#D97706"));
                    BadgeBands.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FEF3C7"));
                }
            }
            catch
            {
                if (BadgeBands != null) BadgeBands.Visibility = Visibility.Collapsed;
            }
        }

        private string? GetSelectedRasterPath()
        {
            if (!string.IsNullOrEmpty(_customRasterPath)) return _customRasterPath;
            if (ComboRasterLayer?.SelectedItem is ComboBoxItem item && item.Tag is string path)
                return path;
            return null;
        }

        private void UpdateDefaultOutputPath()
        {
            if (TxtOutputPath == null) return;
            string? rasterPath = GetSelectedRasterPath();
            if (!string.IsNullOrEmpty(rasterPath))
            {
                string dir = Path.GetDirectoryName(rasterPath) ?? AppDomain.CurrentDomain.BaseDirectory;
                string baseName = Path.GetFileNameWithoutExtension(rasterPath);
                TxtOutputPath.Text = Path.Combine(dir, $"{baseName}_{_activeMode}.tif");
            }
        }

        private void UpdateModeUI()
        {
            if (TxtFormula == null || TxtModeDesc == null) return;

            // Highlight color
            var activeBorder = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
            var activeBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ECFDF5"));
            var normalBorder = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#CBD5E1"));
            var normalBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FFFFFF"));

            void StyleBox(TextBox tb, bool needed)
            {
                tb.BorderBrush = needed ? activeBorder : normalBorder;
                tb.Background = needed ? activeBg : normalBg;
                tb.Opacity = needed ? 1.0 : 0.45;
            }

            switch (_activeMode)
            {
                case "NDVI":
                    TxtFormula.Text = "(NIR - Red) / (NIR + Red)";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
                    TxtModeDesc.Text = "Normalized Difference Vegetation Index: Evaluates photosynthetic canopy density, vegetation greenness, and crop vigor (-1.0 to +1.0).";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, true);
                    StyleBox(TxtBandGreen, false);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, false);
                    break;

                case "NDWI":
                    TxtFormula.Text = "(Green - NIR) / (Green + NIR)";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
                    TxtModeDesc.Text = "Normalized Difference Water Index (McFeeters): Delineates open water bodies, rivers, reservoirs, and surface moisture levels (-1.0 to +1.0).";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, false);
                    StyleBox(TxtBandGreen, true);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, false);
                    break;

                case "EVI":
                    TxtFormula.Text = "2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#16A34A"));
                    TxtModeDesc.Text = "Enhanced Vegetation Index: Atmospheric- and soil-corrected vegetation index ideal for high-biomass regions and dense forest canopies.";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, true);
                    StyleBox(TxtBandGreen, false);
                    StyleBox(TxtBandBlue, true);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, false);
                    break;

                case "NDBI":
                    TxtFormula.Text = "(SWIR1 - NIR) / (SWIR1 + NIR)";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#E11D48"));
                    TxtModeDesc.Text = "Normalized Difference Built-up Index: Identifies urban structures, residential areas, asphalt highways, and impervious surfaces (-1.0 to +1.0).";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, false);
                    StyleBox(TxtBandGreen, false);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, true);
                    StyleBox(TxtBandSwir2, false);
                    break;

                case "NBR":
                    TxtFormula.Text = "(NIR - SWIR2) / (NIR + SWIR2)";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EA580C"));
                    TxtModeDesc.Text = "Normalized Burn Ratio: Measures wildfire burn severity, fire scar perimeters, and post-fire ecological vegetation regeneration (-1.0 to +1.0).";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, false);
                    StyleBox(TxtBandGreen, false);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, true);
                    break;

                case "FALSE_COLOR":
                    TxtFormula.Text = "Composite: Channel R = NIR, Channel G = Red, Channel B = Green";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#7C3AED"));
                    TxtModeDesc.Text = "Standard Color Infrared (CIR) False-Color Composite: Displays healthy vegetation in vibrant shades of red/pink, with dynamic percentile stretch.";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, true);
                    StyleBox(TxtBandGreen, true);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, false);
                    break;
            }
        }

        private void ComboIndexMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboIndexMode?.SelectedItem is ComboBoxItem item && item.Tag is string tag)
            {
                _activeMode = tag;
                UpdateModeUI();
                UpdateDefaultOutputPath();
            }
        }

        private void ComboSensorPreset_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isUpdatingPreset || ComboSensorPreset?.SelectedItem is not ComboBoxItem item || item.Tag is not string preset)
                return;

            _isUpdatingPreset = true;
            try
            {
                switch (preset)
                {
                    case "sentinel2":
                        TxtBandNir.Text = "8";
                        TxtBandRed.Text = "4";
                        TxtBandGreen.Text = "3";
                        TxtBandBlue.Text = "2";
                        TxtBandSwir1.Text = "11";
                        TxtBandSwir2.Text = "12";
                        break;
                    case "landsat8":
                        TxtBandNir.Text = "5";
                        TxtBandRed.Text = "4";
                        TxtBandGreen.Text = "3";
                        TxtBandBlue.Text = "2";
                        TxtBandSwir1.Text = "6";
                        TxtBandSwir2.Text = "7";
                        break;
                    case "landsat7":
                        TxtBandNir.Text = "4";
                        TxtBandRed.Text = "3";
                        TxtBandGreen.Text = "2";
                        TxtBandBlue.Text = "1";
                        TxtBandSwir1.Text = "5";
                        TxtBandSwir2.Text = "7";
                        break;
                    case "planetscope":
                        TxtBandNir.Text = "4";
                        TxtBandRed.Text = "1";
                        TxtBandGreen.Text = "2";
                        TxtBandBlue.Text = "3";
                        TxtBandSwir1.Text = "4";
                        TxtBandSwir2.Text = "4";
                        break;
                }
            }
            finally
            {
                _isUpdatingPreset = false;
            }
        }

        private void BandInput_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (_isUpdatingPreset || ComboSensorPreset == null) return;
            // Switch preset to custom if user manually edits numbers
            foreach (ComboBoxItem item in ComboSensorPreset.Items)
            {
                if (item.Tag is string tag && tag == "custom")
                {
                    _isUpdatingPreset = true;
                    ComboSensorPreset.SelectedItem = item;
                    _isUpdatingPreset = false;
                    break;
                }
            }
        }

        private void ComboRasterLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _customRasterPath = null;
            InspectCurrentRaster();
            UpdateDefaultOutputPath();
        }

        private void BtnBrowseRaster_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Select Multispectral Raster Dataset",
                Filter = "GeoTIFF & BigTIFF (*.tif;*.tiff)|*.tif;*.tiff|All Raster Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                _customRasterPath = dlg.FileName;
                ComboRasterLayer.Items.Insert(0, new ComboBoxItem
                {
                    Content = $"📁 {Path.GetFileName(_customRasterPath)}",
                    Tag = _customRasterPath,
                    IsSelected = true
                });
                InspectCurrentRaster();
                UpdateDefaultOutputPath();
            }
        }

        private void BtnBrowseOutput_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new SaveFileDialog
            {
                Title = "Save Spectral Index GeoTIFF",
                Filter = "GeoTIFF (*.tif)|*.tif|All Files (*.*)|*.*",
                FileName = Path.GetFileName(TxtOutputPath.Text.Trim())
            };

            if (dlg.ShowDialog() == true)
            {
                TxtOutputPath.Text = dlg.FileName;
            }
        }

        private async void BtnRunIndex_Click(object sender, RoutedEventArgs e)
        {
            string? rasterPath = GetSelectedRasterPath();
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid multispectral raster dataset.", "Spectral Indices", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string outputPath = TxtOutputPath.Text.Trim();
            if (string.IsNullOrEmpty(outputPath))
            {
                MessageBox.Show("Please specify a valid output GeoTIFF destination.", "Spectral Indices", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            int.TryParse(TxtBandNir.Text.Trim(), out int nir);
            int.TryParse(TxtBandRed.Text.Trim(), out int red);
            int.TryParse(TxtBandGreen.Text.Trim(), out int green);
            int.TryParse(TxtBandBlue.Text.Trim(), out int blue);
            int.TryParse(TxtBandSwir1.Text.Trim(), out int swir1);
            int.TryParse(TxtBandSwir2.Text.Trim(), out int swir2);

            var bandMap = new
            {
                nir = Math.Max(1, nir),
                red = Math.Max(1, red),
                green = Math.Max(1, green),
                blue = Math.Max(1, blue),
                swir1 = Math.Max(1, swir1),
                swir2 = Math.Max(1, swir2),
                r_composite = Math.Max(1, nir),
                g_composite = Math.Max(1, red),
                b_composite = Math.Max(1, green)
            };
            string bandJson = JsonSerializer.Serialize(bandMap);

            BtnRunIndex.IsEnabled = false;
            ProgressCalculation.Visibility = Visibility.Visible;
            ProgressCalculation.Value = 10;
            TxtStatus.Text = $"Initializing {_activeMode} spectral calculation via Python GDAL...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "satellite",
                    inputFile: rasterPath,
                    outputFile: outputPath,
                    mode: _activeMode,
                    param1: _activeMode,
                    param2: bandJson,
                    onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() =>
                        {
                            ProgressCalculation.Value = pct;
                            TxtStatus.Text = msg;
                        });
                    });

                if (result.Success && !string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                {
                    ProgressCalculation.Value = 100;
                    TxtStatus.Text = $"{_activeMode} completed! Adding dataset to map canvas...";
                    await _main.LoadRasterFile(result.OutputFilePath);
                    Close();
                }
                else
                {
                    ProgressCalculation.Visibility = Visibility.Collapsed;
                    TxtStatus.Text = $"Calculation failed: {result.ErrorMessage}";
                    MessageBox.Show($"Spectral index processing failed:\n{result.ErrorMessage}", "Spectral Index Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    BtnRunIndex.IsEnabled = true;
                }
            }
            catch (Exception ex)
            {
                ProgressCalculation.Visibility = Visibility.Collapsed;
                TxtStatus.Text = $"Error: {ex.Message}";
                MessageBox.Show($"Unexpected error: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                BtnRunIndex.IsEnabled = true;
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
