using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI.Dialogs.Raster
{
    public partial class LulcIntelligenceWindow : Window
    {
        private readonly MainWindow? _main;

        public LulcIntelligenceWindow() : this(Application.Current.MainWindow as MainWindow) { }

        public LulcIntelligenceWindow(MainWindow? main)
        {
            InitializeComponent();
            _main = main;
            if (main != null)
            {
                Owner = main;
            }

            PopulateLayers();
        }

        private void PopulateLayers()
        {
            if (_main != null)
            {
                PickerRaster.Populate(_main.Layers, l => l.Type == LayerType.Raster);
                PickerDem.Populate(_main.Layers, l => l.Type == LayerType.Elevation || l.Type == LayerType.Raster);
                PickerDw.Populate(_main.Layers, l => l.Type == LayerType.Raster);

                if (!string.IsNullOrEmpty(_main.ActiveRasterFilePath))
                {
                    PickerRaster.SelectedPath = _main.ActiveRasterFilePath;
                }
            }

            UpdateDefaultOutputPath();
        }

        private void UpdateDefaultOutputPath()
        {
            string? inputPath = PickerRaster.SelectedPath;
            if (!string.IsNullOrEmpty(inputPath))
            {
                PickerOutput.SetAutoPath(inputPath, "_LULC_Refined.tif");
            }
        }

        private void PickerRaster_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateDefaultOutputPath();
        }

        private async void BtnRun_Click(object sender, RoutedEventArgs e)
        {
            string? rasterPath = PickerRaster.SelectedPath;
            if (string.IsNullOrEmpty(rasterPath) || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid multispectral satellite raster dataset (e.g. Sentinel-2).", 
                                "LULC Intelligence", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string outputPath = PickerOutput.PathText;
            if (string.IsNullOrEmpty(outputPath))
            {
                MessageBox.Show("Please specify an output dataset destination path.", 
                                "LULC Intelligence", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var optionsObj = new
            {
                dem_path = PickerDem.SelectedPath,
                dw_path = PickerDw.SelectedPath,
                apply_majority_filter = ChkMajorityFilter.IsChecked == true,
                export_visual_rgb = ChkExportVisual.IsChecked == true
            };
            string optionsJson = JsonSerializer.Serialize(optionsObj);

            ActionBar.IsBusy = true;
            ActionBar.Progress = 5;
            ActionBar.StatusText = "Initializing LULC classification engine...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "lulc",
                    inputFile: rasterPath,
                    outputFile: outputPath,
                    mode: "intelligence",
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

                ActionBar.IsBusy = false;

                if (result.Success)
                {
                    ActionBar.Progress = 100;
                    ActionBar.StatusText = "LULC Intelligence classification completed successfully!";
                    ActionBar.ActionText = "⚡ Reclassify";
                    ActionBar.CancelText = "Close";

                    if (!string.IsNullOrEmpty(result.OutputData))
                    {
                        try
                        {
                            using var doc = JsonDocument.Parse(result.OutputData);
                            var root = doc.RootElement;
                            if (root.TryGetProperty("total_area_ha", out var totElem))
                                ActionBar.StatusText = $"LULC complete! Total extent: {totElem.GetDouble():N0} ha.";
                        }
                        catch
                        {
                        }
                    }

                    if (ChkLoadToMap.IsChecked == true && _main != null && File.Exists(outputPath))
                    {
                        await _main.LoadRasterFile(outputPath);
                        Activate();
                    }
                }
                else
                {
                    ActionBar.StatusText = $"Classification failed: {result.ErrorMessage}";
                    MessageBox.Show($"LULC Classification failed:\n{result.ErrorMessage}", 
                                    "LULC Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                ActionBar.IsBusy = false;
                ActionBar.StatusText = $"Execution error: {ex.Message}";
                MessageBox.Show($"Classification error:\n{ex.Message}", "LULC Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
