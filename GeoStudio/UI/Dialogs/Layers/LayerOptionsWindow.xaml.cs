using System;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.UI.Dialogs.Layers.Tabs;

namespace GeoStudio.UI.Dialogs.Layers
{
    public partial class LayerOptionsWindow : Window
    {
        private readonly MainWindow? _main;
        private readonly LayerItem? _layer;
        private readonly double _originalOpacity;
        private readonly bool _originalVisibility;
        private readonly bool _originalGpu;

        // Modular Child Tab UserControls
        private readonly LayerInfoTab _infoTab;
        private readonly LayerSourceTab _sourceTab;
        private readonly LayerSymbologyTab _symbologyTab;
        private readonly LayerTransparencyTab _transparencyTab;
        private readonly LayerHistogramTab _histogramTab;
        private readonly LayerRenderingTab _renderingTab;

        private bool _isInitializing = true;

        public LayerOptionsWindow(MainWindow main, LayerItem layer)
        {
            _main = main;
            _layer = layer;
            _originalOpacity = layer?.Opacity ?? 1.0;
            _originalVisibility = layer?.IsVisible ?? true;
            _originalGpu = layer?.UseGpuAcceleration ?? true;

            InitializeComponent();
            Owner = main;

            // Instantiate tabs
            _infoTab = new LayerInfoTab();
            _sourceTab = new LayerSourceTab();
            _symbologyTab = new LayerSymbologyTab();
            _transparencyTab = new LayerTransparencyTab();
            _histogramTab = new LayerHistogramTab();
            _renderingTab = new LayerRenderingTab();

            // Bind data
            if (_layer != null)
            {
                _infoTab.BindLayer(_layer);
                _sourceTab.BindLayer(_layer);
                _symbologyTab.BindLayer(main, _layer);
                _transparencyTab.BindLayer(main, _layer);
                _histogramTab.BindLayer(_layer);
                _renderingTab.BindLayer(main, _layer, () => Close());
            }

            _isInitializing = false;

            if (LstTabs != null)
            {
                LstTabs.SelectedIndex = 0;
            }
        }

        private void LstTabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isInitializing || _layer == null || LstTabs == null) return;
            if (LstTabs.SelectedItem is not ListBoxItem item) return;
            string tag = item.Tag?.ToString() ?? "Information";

            Title = $"Layer Properties - {_layer.Name} — {tag}";

            TabContentPresenter.Content = tag switch
            {
                "Information" => _infoTab,
                "Source" => _sourceTab,
                "Symbology" => _symbologyTab,
                "Transparency" => _transparencyTab,
                "Histogram" => _histogramTab,
                "Rendering" => _renderingTab,
                _ => _infoTab
            };
        }

        private void TxtSearchTabs_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (LstTabs == null || TxtSearchTabs == null) return;
            string query = TxtSearchTabs.Text.Trim().ToLowerInvariant();
            foreach (var item in LstTabs.Items)
            {
                if (item is ListBoxItem lbi)
                {
                    string tag = lbi.Tag?.ToString()?.ToLowerInvariant() ?? "";
                    lbi.Visibility = (string.IsNullOrEmpty(query) || tag.Contains(query)) ? Visibility.Visible : Visibility.Collapsed;
                }
            }
        }

        private void BtnStyle_Click(object sender, RoutedEventArgs e)
        {
            var cm = new ContextMenu();
            var miLoad = new MenuItem { Header = "Load Style..." };
            var miSave = new MenuItem { Header = "Save Style..." };
            var miDefault = new MenuItem { Header = "Restore Default Style" };
            miDefault.Click += (s, args) => _symbologyTab.LoadDefaultPreset();
            cm.Items.Add(miLoad);
            cm.Items.Add(miSave);
            cm.Items.Add(miDefault);
            cm.IsOpen = true;
        }

        private void BtnApply_Click(object sender, RoutedEventArgs e)
        {
            if (_layer == null) return;
            _sourceTab.ApplyChanges(_layer, _main);
            _transparencyTab.ApplyChanges(_layer, _main);
            _renderingTab.ApplyChanges(_layer, _main);
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            BtnApply_Click(sender, e);
            Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            if (_layer != null)
            {
                _layer.Opacity = _originalOpacity;
                _layer.IsVisible = _originalVisibility;
                _layer.UseGpuAcceleration = _originalGpu;

                _main?.PostMessageToMap(new
                {
                    action = "setLayerOpacity",
                    id = _layer.Id,
                    opacity = _originalOpacity,
                    type = _layer.Type.ToString()
                });
            }
            Close();
        }

        private void BtnHelp_Click(object sender, RoutedEventArgs e)
        {
            string layerName = _layer?.Name ?? "Layer";
            MessageBox.Show($"Layer Properties for '{layerName}'.\nUse this dialog to inspect provider information, modify coordinate reference systems, and configure transparency, symbology, and GPU acceleration.",
                            "Layer Properties Help", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }
}
