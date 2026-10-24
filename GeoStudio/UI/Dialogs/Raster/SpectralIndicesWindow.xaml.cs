using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.Python;
using GeoStudio.Raster;

namespace GeoStudio.UI.Dialogs
{
    public partial class SpectralIndicesWindow : Window
    {
        private readonly MainWindow _main;
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
            if (PickerRaster == null) return;
            PickerRaster.Populate(_main.Layers, l => l.Type == LayerType.Raster || l.Type == LayerType.Elevation);

            InspectCurrentRaster();
            UpdateDefaultOutputPath();
        }

        private void InspectCurrentRaster()
        {
            string? rasterPath = PickerRaster?.SelectedPath;
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                PickerRaster?.ClearBadge();
                return;
            }

            try
            {
                var meta = GdalRasterService.InspectMetadata(rasterPath);
                if (meta.BandCount > 1)
                {
                    PickerRaster?.SetBadge($"✓ {meta.BandCount} Bands Detected (Multispectral)");

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
                    PickerRaster?.SetBadge("Single Band (Needs multi-band)");
                }
            }
            catch
            {
                PickerRaster?.ClearBadge();
            }
        }

        private void UpdateDefaultOutputPath()
        {
            if (PickerOutput == null) return;
            PickerOutput.SetAutoPath(PickerRaster?.SelectedPath, $"_{_activeMode}.tif");
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
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#D97706"));
                    TxtModeDesc.Text = "Normalized Burn Ratio: Highlights burned fire scars and estimates burn severity across forest and shrub ecosystems (-1.0 to +1.0).";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, false);
                    StyleBox(TxtBandGreen, false);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, true);
                    break;

                case "FALSE_COLOR":
                    TxtFormula.Text = "R = NIR, G = Red, B = Green (Standard Color Infrared)";
                    TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#9333EA"));
                    TxtModeDesc.Text = "Infrared Color Composite: Maps NIR to Red channel so dense chlorophyll vegetation appears vivid crimson red, water deep dark, and urban gray-cyan.";
                    StyleBox(TxtBandNir, true);
                    StyleBox(TxtBandRed, true);
                    StyleBox(TxtBandGreen, true);
                    StyleBox(TxtBandBlue, false);
                    StyleBox(TxtBandSwir1, false);
                    StyleBox(TxtBandSwir2, false);
                    break;
            }
        }

        private void PickerRaster_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            InspectCurrentRaster();
            UpdateDefaultOutputPath();
        }

        private void ComboIndexMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboIndexMode.SelectedItem is ComboBoxItem item && item.Tag is string tag)
            {
                _activeMode = tag;
                UpdateModeUI();
                UpdateDefaultOutputPath();
            }
        }

        private void ComboSensorPreset_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboSensorPreset.SelectedItem is not ComboBoxItem item || item.Tag is not string preset)
                return;

            _isUpdatingPreset = true;

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

                case "custom":
                    break;
            }

            _isUpdatingPreset = false;
        }

        private void BandInput_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (_isUpdatingPreset || ComboSensorPreset == null) return;

            foreach (ComboBoxItem item in ComboSensorPreset.Items)
            {
                if (item.Tag is string tag && tag == "custom")
                {
                    ComboSensorPreset.SelectedItem = item;
                    break;
                }
            }
        }

        private async void BtnRunIndex_Click(object sender, RoutedEventArgs e)
        {
            string? rasterPath = PickerRaster.SelectedPath;
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid multispectral raster dataset.", "Spectral Indices", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string outputPath = PickerOutput.PathText;
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

            ActionBar.IsBusy = true;
            ActionBar.Progress = 10;
            ActionBar.StatusText = $"Initializing {_activeMode} spectral calculation via Python GDAL...";

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
                            ActionBar.Progress = pct;
                            ActionBar.StatusText = msg;
                        });
                    });

                if (result.Success && !string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                {
                    ActionBar.Progress = 100;
                    ActionBar.StatusText = $"{_activeMode} completed! Adding dataset to map canvas...";
                    await _main.LoadRasterFile(result.OutputFilePath);
                    Close();
                }
                else
                {
                    ActionBar.IsBusy = false;
                    ActionBar.StatusText = $"Calculation failed: {result.ErrorMessage}";
                    MessageBox.Show($"Spectral index processing failed:\n{result.ErrorMessage}", "Spectral Index Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                ActionBar.IsBusy = false;
                ActionBar.StatusText = $"Error: {ex.Message}";
                MessageBox.Show($"Unexpected error: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
