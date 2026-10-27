using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.Python;
using GeoStudio.Raster;
using GeoStudio.Raster.Services;

namespace GeoStudio.UI.Dialogs
{
    public partial class SpectralIndicesWindow : Window
    {
        private readonly MainWindow _main;
        private string _activeMode = "NDVI";
        private bool _isUpdatingPreset = false;
        private bool _isLoaded = false;

        public SpectralIndicesWindow(MainWindow main, string defaultMode = "NDVI")
        {
            InitializeComponent();
            _main = main;
            Owner = main;
            ShowInTaskbar = false;
            _main.ActiveSpectralIndicesWindow = this;
            Closed += (s, e) =>
            {
                if (_main.ActiveSpectralIndicesWindow == this) _main.ActiveSpectralIndicesWindow = null;
                if (_main.WindowState == WindowState.Minimized) _main.WindowState = WindowState.Normal;
                _main.Activate();
            };

            _isLoaded = true;
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
            if (PickerRaster == null || _main == null) return;
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
                string sensorPreset = SpectralIndexDefinitions.DetectSensorPreset(rasterPath, meta.BandCount);
                SelectPresetTag(sensorPreset);

                if (meta.BandCount > 1)
                {
                    PickerRaster?.SetBadge($"✓ {meta.BandCount} Bands Detected (Multispectral)");
                }
                else
                {
                    int.TryParse(TxtBandNir?.Text.Trim() ?? "8", out int nir);
                    int.TryParse(TxtBandRed?.Text.Trim() ?? "4", out int red);
                    string? nirFile = SpectralIndexDefinitions.FindSiblingBandFile(rasterPath, $"B{nir}", $"B0{nir}", $"{nir}");
                    string? redFile = SpectralIndexDefinitions.FindSiblingBandFile(rasterPath, $"B{red}", $"B0{red}", $"{red}");

                    if (nirFile != null && redFile != null)
                    {
                        string sName = sensorPreset.Contains("landsat") ? "Landsat" : "Sentinel";
                        PickerRaster?.SetBadge($"✓ {sName} Scene (Bands B{red} & B{nir} Auto-Linked)");
                    }
                    else
                    {
                        PickerRaster?.SetBadge($"Single Band (B{red} / B{nir} sibling files required)");
                    }
                }
            }
            catch
            {
                PickerRaster?.ClearBadge();
            }
        }

        private void SelectPresetTag(string tag)
        {
            if (ComboSensorPreset == null) return;
            foreach (ComboBoxItem item in ComboSensorPreset.Items)
            {
                if (item.Tag is string itemTag && itemTag.Equals(tag, StringComparison.OrdinalIgnoreCase))
                {
                    ComboSensorPreset.SelectedItem = item;
                    break;
                }
            }
        }

        private void UpdateDefaultOutputPath()
        {
            if (PickerOutput == null) return;
            PickerOutput.SetAutoPath(PickerRaster?.SelectedPath, $"_{_activeMode}.tif");
        }

        private void UpdateModeUI()
        {
            if (!_isLoaded || TxtFormula == null || TxtModeDesc == null || TxtBandNir == null) return;

            if (!SpectralIndexDefinitions.Modes.TryGetValue(_activeMode, out var info))
                info = SpectralIndexDefinitions.Modes["NDVI"];

            var activeBorder = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
            var activeBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ECFDF5"));
            var normalBorder = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#CBD5E1"));
            var normalBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FFFFFF"));

            void StyleBox(TextBox? tb, bool needed)
            {
                if (tb == null) return;
                tb.BorderBrush = needed ? activeBorder : normalBorder;
                tb.Background = needed ? activeBg : normalBg;
                tb.Opacity = needed ? 1.0 : 0.45;
            }

            TxtFormula.Text = info.Formula;
            TxtFormula.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(info.ColorHex));
            TxtModeDesc.Text = info.Description;

            StyleBox(TxtBandNir, info.NeedsNir);
            StyleBox(TxtBandRed, info.NeedsRed);
            StyleBox(TxtBandGreen, info.NeedsGreen);
            StyleBox(TxtBandBlue, info.NeedsBlue);
            StyleBox(TxtBandSwir1, info.NeedsSwir1);
            StyleBox(TxtBandSwir2, info.NeedsSwir2);
        }

        private void PickerRaster_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isLoaded) return;
            InspectCurrentRaster();
            UpdateDefaultOutputPath();
        }

        private void ComboIndexMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isLoaded) return;
            if (ComboIndexMode.SelectedItem is ComboBoxItem item && item.Tag is string tag)
            {
                _activeMode = tag;
                UpdateModeUI();
                UpdateDefaultOutputPath();
            }
        }

        private void ComboSensorPreset_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isLoaded || TxtBandNir == null || ComboSensorPreset == null) return;
            if (ComboSensorPreset.SelectedItem is not ComboBoxItem item || item.Tag is not string preset)
                return;

            if (preset == "custom") return;

            _isUpdatingPreset = true;
            var bands = SpectralIndexDefinitions.GetPresetBands(preset);
            if (TxtBandNir != null) TxtBandNir.Text = bands.nir;
            if (TxtBandRed != null) TxtBandRed.Text = bands.red;
            if (TxtBandGreen != null) TxtBandGreen.Text = bands.green;
            if (TxtBandBlue != null) TxtBandBlue.Text = bands.blue;
            if (TxtBandSwir1 != null) TxtBandSwir1.Text = bands.swir1;
            if (TxtBandSwir2 != null) TxtBandSwir2.Text = bands.swir2;
            _isUpdatingPreset = false;
        }

        private void BandInput_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (!_isLoaded || _isUpdatingPreset || ComboSensorPreset == null) return;

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

            int.TryParse(TxtBandNir?.Text.Trim() ?? "8", out int nir);
            int.TryParse(TxtBandRed?.Text.Trim() ?? "4", out int red);
            int.TryParse(TxtBandGreen?.Text.Trim() ?? "3", out int green);
            int.TryParse(TxtBandBlue?.Text.Trim() ?? "2", out int blue);
            int.TryParse(TxtBandSwir1?.Text.Trim() ?? "11", out int swir1);
            int.TryParse(TxtBandSwir2?.Text.Trim() ?? "12", out int swir2);

            var bandMap = SpectralIndexDefinitions.BuildBandMap(nir, red, green, blue, swir1, swir2, rasterPath);
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
                    ActionBar.IsBusy = false;
                    ActionBar.StatusText = $"✓ {_activeMode} completed successfully! Added layer to map canvas.";
                    ActionBar.ActionText = "⚡ Recalculate";
                    ActionBar.CancelText = "Close";
                    await _main.LoadRasterFile(result.OutputFilePath);
                    Activate();
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

        private void BtnCancel_Click(object sender, RoutedEventArgs e) => Close();
    }
}
