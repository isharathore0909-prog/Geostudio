using System;
using System.Collections.ObjectModel;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.Raster.Services;

namespace GeoStudio.UI.Dialogs.Layers.Tabs
{
    public partial class LayerSymbologyTab : UserControl
    {
        private MainWindow? _main;
        private LayerItem? _layer;
        private readonly ObservableCollection<RasterClassItem> _classes = new();

        public LayerSymbologyTab()
        {
            InitializeComponent();
            GridClasses.ItemsSource = _classes;
        }

        public void BindLayer(MainWindow main, LayerItem layer)
        {
            _main = main;
            _layer = layer;

            if (_layer.Type == LayerType.Vector)
            {
                ExpanderRasterSymbology.Visibility = Visibility.Collapsed;
                ExpanderVectorSymbology.Visibility = Visibility.Visible;
                InitVectorControls();
            }
            else
            {
                ExpanderRasterSymbology.Visibility = Visibility.Visible;
                ExpanderVectorSymbology.Visibility = Visibility.Collapsed;
                LoadDefaultPreset();
            }
        }

        private string _tabFillHex = "#10B981";
        private string _tabStrokeHex = "#10B981";
        private bool _isTabInitializing = false;

        private void InitVectorControls()
        {
            if (_layer == null) return;
            _isTabInitializing = true;
            try
            {
                _tabStrokeHex = !string.IsNullOrEmpty(_layer.ColorHex) ? _layer.ColorHex : "#10B981";
                _tabFillHex = !string.IsNullOrEmpty(_layer.FillColorHex) && !_layer.FillColorHex.Equals("#FFFFFF", StringComparison.OrdinalIgnoreCase)
                    ? _layer.FillColorHex
                    : _tabStrokeHex;

                if (SliderTabStrokeWidth != null)
                    SliderTabStrokeWidth.Value = _layer.StrokeWidth > 0 ? _layer.StrokeWidth : 1.6;
                if (SliderTabFillOpacity != null)
                    SliderTabFillOpacity.Value = Math.Round((_layer.FillOpacity > 0 ? _layer.FillOpacity : 0.28) * 100);

                string dash = _layer.DashPattern ?? "solid";
                if (ComboTabDashStyle != null)
                {
                    foreach (ComboBoxItem item in ComboTabDashStyle.Items)
                    {
                        if (string.Equals(item.Tag?.ToString(), dash, StringComparison.OrdinalIgnoreCase))
                        {
                            ComboTabDashStyle.SelectedItem = item;
                            break;
                        }
                    }
                }

                string mode = !string.IsNullOrEmpty(_layer.VectorRenderType) ? _layer.VectorRenderType : "single";
                if (ComboTabVectorRenderType != null)
                {
                    foreach (ComboBoxItem item in ComboTabVectorRenderType.Items)
                    {
                        if (string.Equals(item.Tag?.ToString(), mode, StringComparison.OrdinalIgnoreCase))
                        {
                            ComboTabVectorRenderType.SelectedItem = item;
                            break;
                        }
                    }
                }
            }
            finally
            {
                _isTabInitializing = false;
            }
            UpdateColorBars();
        }

        private void UpdateColorBars()
        {
            try
            {
                var c = (Color)ColorConverter.ConvertFromString(_tabFillHex);
                if (SwatchTabFill != null) SwatchTabFill.Background = new SolidColorBrush(c);
                if (TxtTabFillHex != null) TxtTabFillHex.Text = _tabFillHex.ToUpperInvariant();
            }
            catch { }

            try
            {
                var c = (Color)ColorConverter.ConvertFromString(_tabStrokeHex);
                if (SwatchTabStroke != null) SwatchTabStroke.Background = new SolidColorBrush(c);
                if (TxtTabStrokeHex != null) TxtTabStrokeHex.Text = _tabStrokeHex.ToUpperInvariant();
            }
            catch { }
        }

        private void BtnTabPickFill_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string? chosen = GeoStudio.UI.Services.ColorDialogHelper.PromptColorHex(_tabFillHex, Window.GetWindow(this));
                if (!string.IsNullOrEmpty(chosen))
                {
                    _tabFillHex = chosen;
                    UpdateColorBars();
                    ApplyLiveVectorStyle();
                }
            }
            catch { }
        }

        private void BtnTabPickStroke_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string? chosen = GeoStudio.UI.Services.ColorDialogHelper.PromptColorHex(_tabStrokeHex, Window.GetWindow(this));
                if (!string.IsNullOrEmpty(chosen))
                {
                    _tabStrokeHex = chosen;
                    UpdateColorBars();
                    ApplyLiveVectorStyle();
                }
            }
            catch { }
        }

        private void SliderTab_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_isTabInitializing) return;
            ApplyLiveVectorStyle();
        }

        private void ComboTabDashStyle_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isTabInitializing) return;
            ApplyLiveVectorStyle();
        }

        private void ComboTabVectorRenderType_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isTabInitializing || _layer == null) return;
            string mode = (ComboTabVectorRenderType?.SelectedItem as ComboBoxItem)?.Tag as string ?? "single";
            _layer.VectorRenderType = mode;
            ApplyLiveVectorStyle();
        }

        private void ApplyLiveVectorStyle()
        {
            if (_layer == null || _layer.Type != LayerType.Vector || _main == null) return;
            double strokeWidth = SliderTabStrokeWidth != null ? SliderTabStrokeWidth.Value : 1.6;
            double fillOpacity = SliderTabFillOpacity != null ? SliderTabFillOpacity.Value / 100.0 : 0.28;
            string dashTag = (ComboTabDashStyle?.SelectedItem as ComboBoxItem)?.Tag as string ?? "solid";
            string mode = (ComboTabVectorRenderType?.SelectedItem as ComboBoxItem)?.Tag as string ?? (_layer.VectorRenderType ?? "single");

            _layer.ColorHex = _tabStrokeHex;
            _layer.FillColorHex = _tabFillHex;
            _layer.StrokeWidth = strokeWidth;
            _layer.FillOpacity = fillOpacity;
            _layer.DashPattern = dashTag;
            _layer.VectorRenderType = mode;

            _main.PostMessageToMap(new
            {
                action = "updateVectorLayerStyle",
                id = _layer.Id,
                mode = mode,
                color = _tabStrokeHex,
                strokeColor = _tabStrokeHex,
                fillColor = _tabFillHex,
                strokeWidth = strokeWidth,
                fillOpacity = fillOpacity,
                dashPattern = dashTag,
                pointRadius = _layer.PointRadius,
                opacity = _layer.Opacity
            });
        }

        public void ApplyChanges(LayerItem layer, MainWindow? main)
        {
            if (layer.Type == LayerType.Vector)
            {
                ApplyLiveVectorStyle();
            }
        }

        public void LoadDefaultPreset()
        {
            _classes.Clear();
            var preset = RasterSymbologyService.GetLulc22Preset();
            if (preset != null)
            {
                foreach (var item in preset) _classes.Add(item);
            }
        }

        private void ComboColorRamp_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboColorRamp?.SelectedItem is ComboBoxItem item)
            {
                string tag = item.Tag?.ToString() ?? "Viridis";
                _classes.Clear();
                var classes = tag == "dw9" ? RasterSymbologyService.GetDynamicWorldPreset() : RasterSymbologyService.GetLulc22Preset();
                if (classes != null)
                {
                    foreach (var c in classes) _classes.Add(c);
                }
            }
        }

        private void BtnClassify_Click(object sender, RoutedEventArgs e)
        {
            LoadDefaultPreset();
            MessageBox.Show("Classified values successfully updated.", "Symbology", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void BtnOpenFullSymbology_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                if (_main != null && _layer != null)
                {
                    var dlg = new Raster.LayerSymbologyWindow(_main, _layer);
                    dlg.Owner = Window.GetWindow(this) ?? _main;
                    dlg.ShowDialog();
                    if (_layer.Type == LayerType.Vector)
                    {
                        InitVectorControls();
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[OpenFullSymbology Error]: {ex}");
                MessageBox.Show($"Could not open Symbology Studio: {ex.Message}", "Symbology", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }
    }
}

