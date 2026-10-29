using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI.Dialogs
{
    public partial class WatershedWindow : Window
    {
        private readonly MainWindow _main;

        public WatershedWindow(MainWindow main)
        {
            InitializeComponent();
            _main = main;
            Owner = main;

            PopulateLayers();
        }

        private void PopulateLayers()
        {
            PickerRaster.Populate(_main.Layers, l => (l.Type == LayerType.Raster || l.Type == LayerType.Elevation));

            // Default to active elevation raster if available
            if (!string.IsNullOrEmpty(_main.ActiveRasterFilePath))
            {
                PickerRaster.SelectedPath = _main.ActiveRasterFilePath;
            }

            UpdateDefaultOutputPath();
        }

        private void UpdateDefaultOutputPath()
        {
            string? inputPath = PickerRaster.SelectedPath;
            if (string.IsNullOrEmpty(inputPath)) return;

            string modeTag = (ComboMode.SelectedItem as ComboBoxItem)?.Tag as string ?? "watershed_both";
            string suffix = modeTag switch
            {
                "watershed_raster" => "_watershed.tif",
                "watershed_vector" => "_watershed.geojson",
                "watershed_both" => "_watershed.geojson",
                "stream_network" => "_streams.tif",
                "flowdir" => "_flowdir.tif",
                "flowaccum" => "_flowaccum.tif",
                "fillsinks" => "_dem_filled.tif",
                _ => "_watershed.geojson"
            };

            PickerOutput.SetAutoPath(inputPath, suffix);
        }

        private void PickerRaster_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateDefaultOutputPath();
        }

        private void ComboThresholdPreset_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TxtThreshold == null) return;

            if (ComboThresholdPreset.SelectedItem is ComboBoxItem item && item.Tag is string tag)
            {
                if (tag == "custom")
                {
                    TxtThreshold.IsEnabled = true;
                    TxtThreshold.Background = System.Windows.Media.Brushes.White;
                }
                else
                {
                    TxtThreshold.IsEnabled = false;
                    TxtThreshold.Background = (System.Windows.Media.Brush)new System.Windows.Media.BrushConverter().ConvertFromString("#F1F5F9")!;
                    TxtThreshold.Text = tag;
                }
            }
        }

        private void TxtThreshold_TextChanged(object sender, TextChangedEventArgs e)
        {
        }

        private void ComboMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateDefaultOutputPath();
        }

        private async void BtnRun_Click(object sender, RoutedEventArgs e)
        {
            string? rasterPath = PickerRaster.SelectedPath;
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid elevation DEM / DSM raster dataset.", "Watershed Delineation", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (!int.TryParse(TxtThreshold.Text.Trim(), out int threshold) || threshold <= 0)
            {
                MessageBox.Show("Please enter a valid positive stream accumulation threshold (e.g. 500, 2000, 10000).", "Watershed Delineation", MessageBoxButton.OK, MessageBoxImage.Warning);
                TxtThreshold.Focus();
                return;
            }

            string outputPath = PickerOutput.PathText;
            if (string.IsNullOrEmpty(outputPath))
            {
                MessageBox.Show("Please specify an output dataset destination path.", "Watershed Delineation", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string modeTag = (ComboMode.SelectedItem as ComboBoxItem)?.Tag as string ?? "watershed_both";
            string taskMode = modeTag switch
            {
                "stream_network" => "stream_network",
                "flowdir" => "flowdir",
                "flowaccum" => "flowaccum",
                "fillsinks" => "fillsinks",
                _ => "watershed"
            };

            string outputFormat = modeTag switch
            {
                "watershed_raster" => "raster",
                "watershed_vector" => "vector",
                _ => "both"
            };

            bool vectorize = modeTag != "watershed_raster" && modeTag != "flowdir" && modeTag != "flowaccum" && modeTag != "fillsinks";
            double minStreamLen = 30.0;
            if (double.TryParse(TxtMinStreamLength?.Text?.Trim(), out double parsedLen) && parsedLen >= 0)
            {
                minStreamLen = parsedLen;
            }

            var optionsObj = new
            {
                auto_fill = ChkAutoFill.IsChecked == true,
                smooth_surface = ChkSmoothDsm.IsChecked == true,
                format = outputFormat,
                vectorize = vectorize && (ChkCreateCatchments.IsChecked == true),
                generate_streams = ChkGenerateStreams.IsChecked == true,
                smooth_streams = ChkSmoothStreams.IsChecked == true,
                min_stream_len = minStreamLen
            };
            string optionsJson = JsonSerializer.Serialize(optionsObj);

            ActionBar.IsBusy = true;
            ActionBar.Progress = 5;
            ActionBar.StatusText = "Initializing hydrological modeling pipeline...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "watershed",
                    inputFile: rasterPath,
                    outputFile: outputPath,
                    mode: taskMode,
                    param1: threshold.ToString(),
                    param2: optionsJson,
                    onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() =>
                        {
                            ActionBar.Progress = pct;
                            ActionBar.StatusText = $"{msg} ({pct}%)";
                        });
                    }
                );

                if (result.Success)
                {
                    ActionBar.Progress = 100;
                    ActionBar.StatusText = "Hydrological delineation completed successfully!";

                    int numBasins = 0;
                    double totalAreaHa = 0.0;
                    string? vectorFile = null;
                    string? rasterFile = null;
                    string? streamsFile = null;

                    if (!string.IsNullOrEmpty(result.OutputData))
                    {
                        try
                        {
                            using var doc = JsonDocument.Parse(result.OutputData);
                            var root = doc.RootElement;
                            if (root.TryGetProperty("num_basins", out var nb)) numBasins = nb.GetInt32();
                            if (root.TryGetProperty("total_area_ha", out var ta)) totalAreaHa = ta.GetDouble();
                            if (root.TryGetProperty("vector_file", out var vf)) vectorFile = vf.GetString();
                            if (root.TryGetProperty("raster_file", out var rf)) rasterFile = rf.GetString();
                            if (root.TryGetProperty("streams_file", out var sf)) streamsFile = sf.GetString();
                        }
                        catch
                        {
                        }
                    }

                    if (numBasins > 0 || totalAreaHa > 0)
                    {
                        ActionBar.StatusText = $"Delineated {numBasins:N0} basins ({totalAreaHa:N1} ha).";
                    }

                    if (ChkLoadToMap.IsChecked == true)
                    {
                        bool zoom = ChkZoomTo.IsChecked == true;

                        // 1. Load vector catchment basins to map if available
                        if (!string.IsNullOrEmpty(vectorFile) && File.Exists(vectorFile) && (modeTag == "watershed_vector" || modeTag == "watershed_both"))
                        {
                            _main.LoadVectorFile(vectorFile, zoomTo: zoom);
                            _main.TxtStatus.Text = $"Delineated {numBasins} catchment basins on map canvas: {Path.GetFileName(vectorFile)}";
                        }
                        // Otherwise load raster GeoTIFF
                        else if (!string.IsNullOrEmpty(rasterFile) && File.Exists(rasterFile))
                        {
                            await _main.LoadRasterFile(rasterFile);
                            _main.TxtStatus.Text = $"Loaded hydrological raster layer: {Path.GetFileName(rasterFile)}";
                        }
                        else if (!string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                        {
                            if (result.OutputFilePath.EndsWith(".geojson", StringComparison.OrdinalIgnoreCase))
                                _main.LoadVectorFile(result.OutputFilePath, zoomTo: zoom);
                            else
                                await _main.LoadRasterFile(result.OutputFilePath);
                        }

                        // 2. Load Drainage Network stream channel lines directly on top of catchments
                        if (ChkGenerateStreams.IsChecked == true && !string.IsNullOrEmpty(streamsFile) && File.Exists(streamsFile))
                        {
                            await Task.Delay(200);
                            _main.LoadVectorFile(streamsFile, customColor: "#1D4ED8", zoomTo: false);
                        }
                    }

                    ActionBar.IsBusy = false;
                    ActionBar.ActionText = "⚡ Recalculate";
                    ActionBar.CancelText = "Close";
                    Activate();
                }
                else
                {
                    ActionBar.IsBusy = false;
                    ActionBar.StatusText = $"Hydrological delineation failed: {result.ErrorMessage}";
                    MessageBox.Show($"Watershed Analysis Failed:\n{result.ErrorMessage}", "Watershed Analysis Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                ActionBar.IsBusy = false;
                ActionBar.StatusText = $"Error: {ex.Message}";
                MessageBox.Show($"Calculation error:\n{ex.Message}", "Watershed Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
