using System;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;

namespace GeoStudio.UI.Dialogs.Layers.Tabs
{
    public partial class LayerRenderingTab : UserControl
    {
        private MainWindow? _main;
        private LayerItem? _layer;
        private Action? _onClose;
        private bool _isInitializing = true;

        public LayerRenderingTab()
        {
            InitializeComponent();
        }

        public void BindLayer(MainWindow main, LayerItem layer, Action onClose)
        {
            _main = main;
            _layer = layer;
            _onClose = onClose;
            _isInitializing = true;

            ChkGpuRendering.IsChecked = layer.UseGpuAcceleration;

            _isInitializing = false;
        }

        public void ApplyChanges(LayerItem layer, MainWindow? main)
        {
            layer.UseGpuAcceleration = ChkGpuRendering.IsChecked == true;
            main?.PostMessageToMap(new
            {
                action = "toggleLayerGpu",
                id = layer.Id,
                useGpu = layer.UseGpuAcceleration
            });
        }

        private void ChkGpuRendering_Checked(object sender, RoutedEventArgs e)
        {
            if (_isInitializing || _layer == null) return;
            _layer.UseGpuAcceleration = true;
            _main?.PostMessageToMap(new { action = "toggleLayerGpu", id = _layer.Id, useGpu = true });
        }

        private void ChkGpuRendering_Unchecked(object sender, RoutedEventArgs e)
        {
            if (_isInitializing || _layer == null) return;
            _layer.UseGpuAcceleration = false;
            _main?.PostMessageToMap(new { action = "toggleLayerGpu", id = _layer.Id, useGpu = false });
        }

        private void BtnZoomToLayer_Click(object sender, RoutedEventArgs e)
        {
            if (_layer != null) _main?.ZoomToLayer(_layer);
        }

        private void BtnRemoveLayer_Click(object sender, RoutedEventArgs e)
        {
            if (_layer == null) return;
            var res = MessageBox.Show($"Are you sure you want to remove layer '{_layer.Name}' from the canvas?",
                                      "Remove Layer", MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (res == MessageBoxResult.Yes)
            {
                _main?.RemoveLayer(_layer);
                _onClose?.Invoke();
            }
        }
    }
}
