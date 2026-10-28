using System;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;

namespace GeoStudio.UI.Dialogs.Layers.Tabs
{
    public partial class LayerTransparencyTab : UserControl
    {
        private MainWindow? _main;
        private LayerItem? _layer;
        private bool _isInitializing = true;

        public LayerTransparencyTab()
        {
            InitializeComponent();
        }

        public void BindLayer(MainWindow main, LayerItem layer)
        {
            _main = main;
            _layer = layer;
            _isInitializing = true;

            SliderGlobalOpacity.Value = layer.Opacity;
            TxtGlobalOpacityPercent.Text = $"{(int)Math.Round(layer.Opacity * 100)}%";
            ChkTransparencyVisible.IsChecked = layer.IsVisible;

            _isInitializing = false;
        }

        public void ApplyChanges(LayerItem layer, MainWindow? main)
        {
            layer.Opacity = SliderGlobalOpacity.Value;
            layer.IsVisible = ChkTransparencyVisible.IsChecked == true;

            main?.PostMessageToMap(new
            {
                action = "setLayerOpacity",
                id = layer.Id,
                opacity = layer.Opacity,
                type = layer.Type.ToString()
            });

            main?.PostMessageToMap(new
            {
                action = "toggleLayer",
                id = layer.Id,
                visible = layer.IsVisible,
                type = layer.Type.ToString()
            });
        }

        private void SliderGlobalOpacity_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_isInitializing || _layer == null) return;
            _layer.Opacity = SliderGlobalOpacity.Value;
            if (TxtGlobalOpacityPercent != null)
            {
                TxtGlobalOpacityPercent.Text = $"{(int)Math.Round(_layer.Opacity * 100)}%";
            }

            _main?.PostMessageToMap(new
            {
                action = "setLayerOpacity",
                id = _layer.Id,
                opacity = _layer.Opacity,
                type = _layer.Type.ToString()
            });
        }

        private void ChkTransparencyVisible_Checked(object sender, RoutedEventArgs e)
        {
            if (_isInitializing || _layer == null) return;
            _layer.IsVisible = true;
            _main?.PostMessageToMap(new { action = "toggleLayer", id = _layer.Id, visible = true, type = _layer.Type.ToString() });
        }

        private void ChkTransparencyVisible_Unchecked(object sender, RoutedEventArgs e)
        {
            if (_isInitializing || _layer == null) return;
            _layer.IsVisible = false;
            _main?.PostMessageToMap(new { action = "toggleLayer", id = _layer.Id, visible = false, type = _layer.Type.ToString() });
        }
    }
}
