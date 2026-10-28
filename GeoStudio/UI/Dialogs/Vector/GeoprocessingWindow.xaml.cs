using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Python;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Dialogs
{
    public partial class GeoprocessingWindow : Window
    {
        private readonly MainWindow _main;
        private string _activeMode = "buffer";
        private string? _customMaskPath = null;

        public GeoprocessingWindow(MainWindow main, string defaultMode = "buffer")
        {
            _main = main;
            _main.ActiveClipVectorWindow = this;
            InitializeComponent();
            Closed += (s, e) =>
            {
                if (_main.ActiveClipVectorWindow == this)
                    _main.ActiveClipVectorWindow = null;
            };
            Owner = main;
            _activeMode = defaultMode.ToLowerInvariant();
            PopulateLayers();
            SetMode(_activeMode);
        }

        public void SetMode(string mode)
        {
            _activeMode = mode.ToLowerInvariant();
            if (ComboOperation != null)
            {
                foreach (ComboBoxItem item in ComboOperation.Items)
                {
                    if (item.Tag is string tag && tag.Equals(_activeMode, StringComparison.OrdinalIgnoreCase))
                    {
                        ComboOperation.SelectedItem = item;
                        break;
                    }
                }
            }
            UpdateModeUI();
            UpdateDefaultOutputPath();
        }

        private void PopulateLayers()
        {
            if (ComboInputLayer == null || ComboClipMaskLayer == null) return;

            ComboInputLayer.Items.Clear();
            ComboClipMaskLayer.Items.Clear();

            foreach (var l in _main.Layers.Where(x => x.Type == LayerType.Vector))
            {
                ComboInputLayer.Items.Add(new ComboBoxItem { Content = l.Name, Tag = l });
                ComboClipMaskLayer.Items.Add(new ComboBoxItem { Content = l.Name, Tag = l });
            }

            if (ComboInputLayer.Items.Count > 0)
                ComboInputLayer.SelectedIndex = 0;
            if (ComboClipMaskLayer.Items.Count > 1)
                ComboClipMaskLayer.SelectedIndex = 1;
            else if (ComboClipMaskLayer.Items.Count > 0)
                ComboClipMaskLayer.SelectedIndex = 0;

            PopulateFields();
            UpdateDefaultOutputPath();
        }

        private void PopulateFields()
        {
            if (ComboDissolveField == null) return;

            ComboDissolveField.Items.Clear();
            ComboDissolveField.Items.Add(new ComboBoxItem { Content = "-- Dissolve All Features (Single Geometry) --", Tag = "" });

            if (ComboInputLayer != null && ComboInputLayer.SelectedItem is ComboBoxItem item && item.Tag is LayerItem layer && layer.AttributeFields != null)
            {
                foreach (var field in layer.AttributeFields)
                {
                    ComboDissolveField.Items.Add(new ComboBoxItem { Content = field, Tag = field });
                }
            }
            ComboDissolveField.SelectedIndex = 0;
        }

        private void UpdateModeUI()
        {
            if (PanelBufferParams == null || PanelConvexHullParams == null || 
                PanelDissolveParams == null || PanelClipParams == null || Header == null)
                return;

            PanelBufferParams.Visibility = Visibility.Collapsed;
            PanelConvexHullParams.Visibility = Visibility.Collapsed;
            PanelDissolveParams.Visibility = Visibility.Collapsed;
            PanelClipParams.Visibility = Visibility.Collapsed;

            switch (_activeMode)
            {
                case "buffer":
                    PanelBufferParams.Visibility = Visibility.Visible;
                    Header.Icon = "🌐";
                    Header.Title = "Geodesic Buffer Tool";
                    Header.Description = "Creates surrounding buffer polygon zones at specified distance using Shapely.";
                    break;

                case "convex_hull":
                    PanelConvexHullParams.Visibility = Visibility.Visible;
                    Header.Icon = "⌂";
                    Header.Title = "Minimum Convex Hull";
                    Header.Description = "Computes the smallest convex enclosing polygon for features.";
                    break;

                case "centroids":
                    Header.Icon = "•";
                    Header.Title = "Calculate Vector Centroids";
                    Header.Description = "Extracts geometric center points for all polygon or line features.";
                    break;

                case "dissolve":
                    PanelDissolveParams.Visibility = Visibility.Visible;
                    Header.Icon = "◉";
                    Header.Title = "Dissolve Vector Geometries";
                    Header.Description = "Merges contiguous/matching geometries sharing identical attribute values.";
                    break;

                case "voronoi":
                    Header.Icon = "🔲";
                    Header.Title = "Voronoi (Thiessen) Polygons";
                    Header.Description = "Constructs Delaunay dual Voronoi polygons partitioning space around points.";
                    break;

                case "clip":
                    PanelClipParams.Visibility = Visibility.Visible;
                    Header.Icon = "✂";
                    Header.Title = "Clip Vector by Mask Polygon";
                    Header.Description = "Cuts features using overlay boundary polygon or canvas drawn geometry.";
                    break;
            }
        }

        private void UpdateDefaultOutputPath()
        {
            if (PickerOutput == null) return;
            string? inPath = GetSelectedInputLayer()?.FilePath;
            if (!string.IsNullOrEmpty(inPath))
            {
                string dir = Path.GetDirectoryName(inPath) ?? AppDomain.CurrentDomain.BaseDirectory;
                string baseName = Path.GetFileNameWithoutExtension(inPath);
                PickerOutput.PathText = Path.Combine(dir, $"{baseName}_{_activeMode}.geojson");
            }
        }

        private LayerItem? GetSelectedInputLayer()
        {
            if (ComboInputLayer?.SelectedItem is ComboBoxItem item && item.Tag is LayerItem l)
                return l;
            return null;
        }

        private string? GetSelectedClipMaskPath()
        {
            if (!string.IsNullOrEmpty(_customMaskPath)) return _customMaskPath;
            if (ComboClipMaskLayer?.SelectedItem is ComboBoxItem item && item.Tag is LayerItem l)
                return l.FilePath;
            return null;
        }

        private void ComboOperation_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboOperation.SelectedItem is ComboBoxItem item && item.Tag is string mode)
            {
                _activeMode = mode;
                UpdateModeUI();
                UpdateDefaultOutputPath();
            }
        }

        private void ComboInputLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            PopulateFields();
            UpdateDefaultOutputPath();
        }

        private void ComboClipMaskLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _customMaskPath = null;
            if (BadgeClipMaskStatus != null)
                BadgeClipMaskStatus.Visibility = Visibility.Collapsed;
        }

        private void BtnBrowseClipMask_Click(object sender, RoutedEventArgs e)
        {
            if (FileDialogHelper.PromptOpen("Vector Files (*.geojson;*.json;*.shp;*.gpkg;*.kml)|*.geojson;*.json;*.shp;*.gpkg;*.kml|All Files (*.*)|*.*", "Select Clip Mask Vector File") is { } file)
            {
                _customMaskPath = file;
                var newItem = new ComboBoxItem { Content = $"[File] {Path.GetFileName(file)}", Tag = file };
                ComboClipMaskLayer.Items.Insert(0, newItem);
                ComboClipMaskLayer.SelectedItem = newItem;
            }
        }

        private void BtnDrawClipPolygon_Click(object sender, RoutedEventArgs e)
        {
            _main.PostMessageToMap(new { action = "setTool", tool = "draw_clip_polygon" });
            ActionBar.StatusText = "✏️ Canvas Drawing: Click vertices on the map; double-click to complete.";
            BtnDrawClipPolygon.Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(254, 226, 226));
        }

        public void SetDrawnMask(string filePath, string label)
        {
            _customMaskPath = filePath;
            var item = new ComboBoxItem { Content = $"[Canvas] {label}", Tag = filePath, IsSelected = true };
            ComboClipMaskLayer.Items.Insert(0, item);
            ComboClipMaskLayer.SelectedItem = item;

            if (BadgeClipMaskStatus != null)
            {
                BadgeClipMaskStatus.Visibility = Visibility.Visible;
                TxtClipMaskBadge.Text = $"✓ {label}";
            }

            BtnDrawClipPolygon.ClearValue(BackgroundProperty);
            ActionBar.StatusText = $"✓ Captured manual boundary: {label}";
        }

        private async void BtnRun_Click(object sender, RoutedEventArgs e)
        {
            var layer = GetSelectedInputLayer();
            if (layer == null || string.IsNullOrEmpty(layer.FilePath) || !File.Exists(layer.FilePath))
            {
                MessageBox.Show("Please select a valid vector input layer.", "Input Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string outPath = PickerOutput.PathText;
            if (string.IsNullOrEmpty(outPath))
            {
                MessageBox.Show("Please provide a valid output file path.", "Output Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string? param1 = null;
            string? param2 = null;

            if (_activeMode == "buffer")
            {
                if (!double.TryParse(TxtBufferDistance.Text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out double dist) || dist <= 0)
                {
                    MessageBox.Show("Please enter a valid positive buffer distance.", "Buffer Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
                param1 = dist.ToString(CultureInfo.InvariantCulture);

                int segments = 16;
                if (ComboSegments.SelectedItem is ComboBoxItem segItem && int.TryParse(segItem.Content?.ToString(), out int s))
                    segments = s;

                bool dissolve = ChkBufferDissolve.IsChecked == true;
                param2 = JsonSerializer.Serialize(new { segments = segments, dissolve = dissolve });
            }
            else if (_activeMode == "convex_hull")
            {
                param1 = (ComboHullScope.SelectedItem is ComboBoxItem hs && hs.Tag is string t) ? t : "all";
            }
            else if (_activeMode == "dissolve")
            {
                param1 = (ComboDissolveField.SelectedItem is ComboBoxItem df && df.Tag is string f) ? f : "";
            }
            else if (_activeMode == "clip")
            {
                string? maskPath = GetSelectedClipMaskPath();
                if (string.IsNullOrEmpty(maskPath) || !File.Exists(maskPath))
                {
                    MessageBox.Show("Please select a layer, browse a file, or draw a polygon on the map canvas to use as the clipping mask.", "Clip Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }
                param1 = maskPath;
            }

            ActionBar.IsBusy = true;
            ActionBar.Progress = 15;
            ActionBar.StatusText = $"Executing {_activeMode} algorithm via Python Shapely backend...";

            try
            {
                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "vector_geoprocessing",
                    inputFile: layer.FilePath,
                    outputFile: outPath,
                    mode: _activeMode,
                    param1: param1,
                    param2: param2,
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
                    ActionBar.StatusText = "Processing complete! Loading result onto map...";

                    string color = _activeMode switch
                    {
                        "buffer" => "#2563EB",
                        "convex_hull" => "#9333EA",
                        "centroids" => "#EF4444",
                        "dissolve" => "#059669",
                        "voronoi" => "#D97706",
                        "clip" => "#E11D48",
                        _ => "#3B82F6"
                    };

                    _main.LoadVectorFile(result.OutputFilePath, customColor: color);
                    Close();
                }
                else
                {
                    ActionBar.IsBusy = false;
                    ActionBar.StatusText = $"Failed: {result.ErrorMessage}";
                    MessageBox.Show($"Geoprocessing failed:\n{result.ErrorMessage}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
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
