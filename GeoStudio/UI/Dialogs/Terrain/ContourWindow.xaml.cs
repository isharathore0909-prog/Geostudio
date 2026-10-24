using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI
{
    public partial class ContourWindow : Window
    {
        private readonly List<LayerItem> _rasterLayers;
        private readonly Action<string, string, bool, double>? _onContourReady;

        public ContourWindow(List<LayerItem> rasterLayers, LayerItem? selectedRaster = null, Action<string, string, bool, double>? onContourReady = null)
        {
            InitializeComponent();
            _rasterLayers = rasterLayers ?? new List<LayerItem>();
            _onContourReady = onContourReady;

            ComboSourceRaster.ItemsSource = _rasterLayers;
            ComboSourceRaster.DisplayMemberPath = "Name";

            if (selectedRaster != null && _rasterLayers.Contains(selectedRaster))
            {
                ComboSourceRaster.SelectedItem = selectedRaster;
            }
            else if (_rasterLayers.Count > 0)
            {
                ComboSourceRaster.SelectedIndex = 0;
            }
        }

        private async void BtnGenerate_Click(object sender, RoutedEventArgs e)
        {
            var selectedRaster = ComboSourceRaster.SelectedItem as LayerItem;
            if (selectedRaster == null || string.IsNullOrEmpty(selectedRaster.FilePath) || !File.Exists(selectedRaster.FilePath))
            {
                MessageBox.Show("Please select a valid elevation raster layer.", "Contour Generator", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (!double.TryParse(TxtInterval.Text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out double interval) || interval <= 0)
            {
                MessageBox.Show("Please enter a valid positive contour interval (e.g. 5, 10, 20).", "Contour Generator", MessageBoxButton.OK, MessageBoxImage.Warning);
                TxtInterval.Focus();
                return;
            }

            double.TryParse(TxtBaseElev.Text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out double baseElev);

            string colorHex = "#D97706";
            if (ComboContourColor.SelectedItem is ComboBoxItem cbi && cbi.Tag is string hex)
            {
                colorHex = hex;
            }

            bool zoomTo = ChkZoomToContour.IsChecked == true;

            ActionBar.IsBusy = true;
            ActionBar.Progress = 10;
            ActionBar.StatusText = $"Extracting {interval}m contour lines from {selectedRaster.Name}...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "terrain",
                    inputFile: selectedRaster.FilePath,
                    mode: "contours",
                    param1: interval.ToString(CultureInfo.InvariantCulture),
                    param2: baseElev.ToString(CultureInfo.InvariantCulture),
                    onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() =>
                        {
                            ActionBar.Progress = pct;
                            ActionBar.StatusText = $"Contour extraction: {pct}% {msg}";
                        });
                    });

                if (result.Success && !string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                {
                    ActionBar.Progress = 100;
                    ActionBar.StatusText = $"Contour generation successful: {Path.GetFileName(result.OutputFilePath)}";

                    _onContourReady?.Invoke(result.OutputFilePath, colorHex, zoomTo, interval);

                    await Task.Delay(300);
                    Close();
                }
                else
                {
                    ActionBar.IsBusy = false;
                    ActionBar.StatusText = $"Extraction failed: {result.ErrorMessage}";
                    MessageBox.Show($"Contour generation failed:\n{result.ErrorMessage}", "Contour Generator Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                ActionBar.IsBusy = false;
                ActionBar.StatusText = $"Error: {ex.Message}";
                MessageBox.Show($"Exception during contour extraction:\n{ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
