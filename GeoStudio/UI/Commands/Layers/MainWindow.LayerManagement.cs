using System;
using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Raster;
using GeoStudio.PointCloud;

namespace GeoStudio
{
    public partial class MainWindow
    {
        private void UpdateLayerCount()
        {
            if (!_isInitialized || TxtLayerCount == null || TxtActiveLayer == null) return;
            TxtLayerCount.Text = Layers.Count.ToString();
            TxtActiveLayer.Text = Layers.Count > 0 ? $"Layer: {Layers[Layers.Count - 1].Name}" : "Layer: None";
        }

        private LayerItem? FindLayer(string id)
        {
            foreach (var item in Layers)
            {
                if (item.Id == id) return item;
            }
            return null;
        }

        internal void LayerCheckBox_Checked(object sender, RoutedEventArgs e)
        {
            if (sender is CheckBox cb && cb.Tag is string layerId)
            {
                var layer = FindLayer(layerId);
                PostMessageToMap(new { action = "toggleLayer", id = layerId, visible = true, type = layer?.Type.ToString() });
            }
        }

        internal void LayerCheckBox_Unchecked(object sender, RoutedEventArgs e)
        {
            if (sender is CheckBox cb && cb.Tag is string layerId)
            {
                var layer = FindLayer(layerId);
                PostMessageToMap(new { action = "toggleLayer", id = layerId, visible = false, type = layer?.Type.ToString() });
            }
        }

        internal void LayerOpacity_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (sender is FrameworkElement fe)
            {
                var layer = fe.DataContext as LayerItem ?? (fe.Tag is string id ? FindLayer(id) : null);
                if (layer != null)
                {
                    layer.Opacity = e.NewValue;
                    PostMessageToMap(new { action = "setLayerOpacity", id = layer.Id, opacity = e.NewValue, type = layer.Type.ToString() });
                }
            }
        }

        internal void BtnRemoveLayer_Click(object sender, RoutedEventArgs e)
        {
            string? layerId = (sender as FrameworkElement)?.Tag as string;
            if (string.IsNullOrEmpty(layerId)) return;

            var layer = FindLayer(layerId);
            if (layer != null)
            {
                Layers.Remove(layer);

                if (LayersListControl.ItemsSource is ObservableCollection<LayerItem> currentSource && currentSource != Layers)
                {
                    currentSource.Remove(layer);
                }

                if (_activeRasterLayerId == layerId)
                {
                    _activeRasterLayerId = null;
                    _activeRasterFilePath = null;
                    _activeRasterShaderMode = null;
                    _activeRasterPalette = null;
                    _rasterCts?.Cancel();
                }

                UpdateLayerCount();
                if (Layers.Count <= 1)
                {
                    if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Collapsed;
                    GdalRasterService.ClearCache();
                    DuckDbPointCloudService.Clear();
                }
                PostMessageToMap(new { action = "removeLayer", id = layerId, type = layer.Type.ToString() });
                TxtStatus.Text = $"Removed layer: {layer.Name}";
            }
        }

        internal void TxtSearchLayers_TextChanged(object sender, TextChangedEventArgs e)
        {
            string query = TxtSearchLayers.Text.Trim().ToLowerInvariant();
            if (string.IsNullOrEmpty(query))
            {
                LayersListControl.ItemsSource = Layers;
                return;
            }

            var filtered = new ObservableCollection<LayerItem>();
            foreach (var item in Layers)
            {
                if (item.Name.ToLowerInvariant().Contains(query) || item.Details.ToLowerInvariant().Contains(query))
                {
                    filtered.Add(item);
                }
            }
            LayersListControl.ItemsSource = filtered;
        }

        internal void BtnZoomToLayer_Click(object sender, RoutedEventArgs e)
        {
            string? layerId = (sender as FrameworkElement)?.Tag as string;
            if (!string.IsNullOrEmpty(layerId))
            {
                var layer = FindLayer(layerId);
                if (layer != null && layer.BoundingBox != null)
                {
                    PostMessageToMap(new { action = "zoomToExtent", bounds = layer.BoundingBox });
                    TxtStatus.Text = $"Zoomed to layer: {layer.Name}";
                }
                else
                {
                    PostMessageToMap(new { action = "zoomFull" });
                }
            }
        }

        internal void MenuToggleGpu_Click(object sender, RoutedEventArgs e)
        {
            string? layerId = (sender as FrameworkElement)?.Tag as string;
            if (string.IsNullOrEmpty(layerId)) return;
            var layer = FindLayer(layerId);
            if (layer != null)
            {
                layer.UseGpuAcceleration = !layer.UseGpuAcceleration;
                PostMessageToMap(new
                {
                    action = "toggleLayerGpu",
                    id = layer.Id,
                    useGpu = layer.UseGpuAcceleration
                });
                TxtStatus.Text = $"Layer '{layer.Name}' GPU Acceleration: {(layer.UseGpuAcceleration ? "Enabled" : "Disabled")}";
            }
        }
    }
}
