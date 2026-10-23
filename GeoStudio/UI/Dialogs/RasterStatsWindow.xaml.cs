using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using GeoStudio.Models;
using GeoStudio.Python;

namespace GeoStudio.UI.Dialogs
{
    public partial class RasterStatsWindow : Window
    {
        private readonly MainWindow _main;
        private List<double>? _currentHistogram;

        public RasterStatsWindow(MainWindow main)
        {
            InitializeComponent();
            _main = main;
            Owner = main;
            PopulateLayers();
        }

        private void PopulateLayers()
        {
            ComboRaster.Items.Clear();
            foreach (var l in _main.Layers.Where(x => x.Type == LayerType.Raster || x.Type == LayerType.Elevation))
            {
                ComboRaster.Items.Add(new ComboBoxItem { Content = l.Name, Tag = l.FilePath });
            }

            if (ComboRaster.Items.Count > 0)
            {
                ComboRaster.SelectedIndex = 0;
                BtnCalculate_Click(this, new RoutedEventArgs());
            }
            else
            {
                TxtStatus.Text = "No raster layer loaded.";
            }
        }

        private async void BtnCalculate_Click(object sender, RoutedEventArgs e)
        {
            if (ComboRaster.SelectedItem is not ComboBoxItem item || item.Tag is not string rasterPath || !File.Exists(rasterPath))
            {
                MessageBox.Show("Please select a valid loaded raster layer.", "Raster Statistics", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            int band = 1;
            if (ComboBand.SelectedItem is ComboBoxItem bandItem && bandItem.Content is string content)
            {
                var match = System.Text.RegularExpressions.Regex.Match(content, @"\d+");
                if (match.Success) band = int.Parse(match.Value);
            }

            BtnCalculate.IsEnabled = false;
            ProgressStats.Visibility = Visibility.Visible;
            TxtStatus.Text = $"Calculating statistics for Band {band}...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "raster_stats",
                    inputFile: rasterPath,
                    param1: band.ToString());

                if (result.Success && !string.IsNullOrEmpty(result.OutputData))
                {
                    using var doc = JsonDocument.Parse(result.OutputData);
                    var root = doc.RootElement;

                    double min = root.GetProperty("min").GetDouble();
                    double max = root.GetProperty("max").GetDouble();
                    double mean = root.GetProperty("mean").GetDouble();
                    double stddev = root.GetProperty("stddev").GetDouble();
                    int w = root.GetProperty("width").GetInt32();
                    int h = root.GetProperty("height").GetInt32();
                    string dtype = root.GetProperty("data_type").GetString() ?? "Unknown";
                    double px = root.GetProperty("pixel_size_x").GetDouble();
                    double py = root.GetProperty("pixel_size_y").GetDouble();

                    TxtMin.Text = min.ToString("F3");
                    TxtMax.Text = max.ToString("F3");
                    TxtMean.Text = mean.ToString("F3");
                    TxtStdDev.Text = stddev.ToString("F3");
                    TxtDetails.Text = $"Dimensions: {w:N0} x {h:N0} px | Pixel Size: {px:F4} x {py:F4} | Data Type: {dtype}";

                    if (root.TryGetProperty("histogram", out var histElem) && histElem.ValueKind == JsonValueKind.Array)
                    {
                        _currentHistogram = histElem.EnumerateArray().Select(x => x.GetDouble()).ToList();
                        RenderHistogram();
                    }

                    TxtStatus.Text = "Statistics computed successfully.";
                }
                else
                {
                    TxtStatus.Text = $"Failed: {result.ErrorMessage}";
                    MessageBox.Show($"Failed to compute raster statistics:\n{result.ErrorMessage}", "Raster Statistics Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Error: {ex.Message}";
                MessageBox.Show($"Error: {ex.Message}", "Raster Statistics Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                BtnCalculate.IsEnabled = true;
                ProgressStats.Visibility = Visibility.Collapsed;
            }
        }

        private void CanvasHistogram_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            RenderHistogram();
        }

        private void RenderHistogram()
        {
            CanvasHistogram.Children.Clear();
            if (_currentHistogram == null || _currentHistogram.Count == 0) return;

            double width = CanvasHistogram.ActualWidth;
            double height = CanvasHistogram.ActualHeight;
            if (width <= 10 || height <= 10) return;

            double maxVal = _currentHistogram.Max();
            if (maxVal <= 0) maxVal = 1;

            int binCount = _currentHistogram.Count;
            double binWidth = width / binCount;

            var polygon = new Polygon
            {
                Fill = new LinearGradientBrush(
                    Color.FromArgb(180, 2, 132, 199),
                    Color.FromArgb(40, 2, 132, 199),
                    new Point(0, 0),
                    new Point(0, 1)),
                Stroke = new SolidColorBrush(Color.FromRgb(56, 189, 248)),
                StrokeThickness = 1.5
            };

            polygon.Points.Add(new Point(0, height));

            for (int i = 0; i < binCount; i++)
            {
                double x = i * binWidth;
                double norm = _currentHistogram[i] / maxVal;
                double y = height - (norm * (height - 10));
                polygon.Points.Add(new Point(x, y));
            }

            polygon.Points.Add(new Point(width, height));
            CanvasHistogram.Children.Add(polygon);
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
