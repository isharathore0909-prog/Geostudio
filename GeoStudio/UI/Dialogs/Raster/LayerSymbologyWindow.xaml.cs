using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Raster;
using GeoStudio.Raster.Services;
using OSGeo.GDAL;

namespace GeoStudio.UI.Dialogs.Raster
{
    public partial class LayerSymbologyWindow : Window
    {
        private readonly MainWindow _main;
        private readonly LayerItem _layer;
        private readonly ObservableCollection<RasterClassItem> _classes = new();
        private int _bandCount = 1;

        public LayerSymbologyWindow(MainWindow main, LayerItem layer)
        {
            InitializeComponent();
            _main = main;
            _layer = layer;
            Owner = main;

            Title = $"{layer.Name} — Symbology";
            GridClasses.ItemsSource = _classes;

            InspectBandsAndPopulate();
            LoadLayerInitialSymbology();
        }

        private void InspectBandsAndPopulate()
        {
            try
            {
                GdalCacheManager.Initialize();
                using var ds = Gdal.Open(_layer.FilePath, Access.GA_ReadOnly);
                if (ds != null)
                {
                    _bandCount = ds.RasterCount;
                    for (int b = 1; b <= _bandCount; b++)
                    {
                        string bandLabel = $"Band {b}" + (b == 1 ? " (Red)" : (b == 2 ? " (Green)" : (b == 3 ? " (Blue)" : "")));
                        ComboRedBand.Items.Add(bandLabel);
                        ComboGreenBand.Items.Add(bandLabel);
                        ComboBlueBand.Items.Add(bandLabel);
                    }

                    if (_bandCount >= 1) ComboRedBand.SelectedIndex = 0;
                    if (_bandCount >= 2) ComboGreenBand.SelectedIndex = 1;
                    if (_bandCount >= 3) ComboBlueBand.SelectedIndex = 2;
                }
            }
            catch { }
        }

        private void LoadLayerInitialSymbology()
        {
            bool isLulc = _layer.Name.Contains("LULC", StringComparison.OrdinalIgnoreCase) ||
                          _layer.Name.Contains("LandCover", StringComparison.OrdinalIgnoreCase) ||
                          _layer.Name.Contains("Refined", StringComparison.OrdinalIgnoreCase);

            var extracted = RasterSymbologyService.ExtractOrScanClasses(_layer.FilePath);
            if (extracted.Count > 0)
            {
                foreach (var c in extracted) _classes.Add(c);
            }
            else
            {
                foreach (var c in RasterSymbologyService.GetLulc22Preset()) _classes.Add(c);
            }

            if (_bandCount >= 3)
            {
                ComboRenderType.SelectedIndex = 0; // Multiband color
            }
            else if (isLulc || extracted.Count > 0 || (_layer.ShaderMode != null && _layer.ShaderMode.Contains("paletted")))
            {
                ComboRenderType.SelectedIndex = 1; // Paletted / Unique values
            }
            else if (_layer.IsElevation || (_layer.ShaderMode != null && _layer.ShaderMode.Contains("atlas")))
            {
                ComboRenderType.SelectedIndex = 2; // Singleband pseudocolor
            }
            else
            {
                ComboRenderType.SelectedIndex = 3; // Singleband gray
            }
        }

        private void ComboRenderType_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (PanelMultiband == null || PanelPaletted == null || PanelPseudocolor == null || PanelGray == null) return;
            string tag = (ComboRenderType.SelectedItem as ComboBoxItem)?.Tag as string ?? "paletted";

            PanelMultiband.Visibility = tag == "multiband" ? Visibility.Visible : Visibility.Collapsed;
            PanelPaletted.Visibility = tag == "paletted" ? Visibility.Visible : Visibility.Collapsed;
            PanelGray.Visibility = tag == "gray" ? Visibility.Visible : Visibility.Collapsed;
            PanelPseudocolor.Visibility = tag == "pseudocolor" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelSingleColor != null) PanelSingleColor.Visibility = tag == "singlecolor" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelHillshade != null) PanelHillshade.Visibility = tag == "hillshade" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelContours != null) PanelContours.Visibility = tag == "contours" ? Visibility.Visible : Visibility.Collapsed;
        }

        private void BtnScanClasses_Click(object sender, RoutedEventArgs e)
        {
            var scanned = RasterSymbologyService.ExtractOrScanClasses(_layer.FilePath);
            _classes.Clear();
            foreach (var c in scanned) _classes.Add(c);
        }

        private void ApplySymbology()
        {
            string mode = (ComboRenderType.SelectedItem as ComboBoxItem)?.Tag as string ?? "paletted";

            if (mode == "paletted")
            {
                _layer.ShaderMode = "paletted";
                _layer.Palette = "LULC";

                uint[] customLut = new uint[256];
                foreach (var item in _classes)
                {
                    if (item.Value >= 0 && item.Value < 256)
                    {
                        if (item.IsVisible && item.Value != 0)
                        {
                            customLut[item.Value] = (uint)(item.B | (item.G << 8) | (item.R << 16) | (item.A << 24));
                        }
                        else
                        {
                            customLut[item.Value] = 0;
                        }
                    }
                }
                RasterSymbologyService.LayerCustomLuts[_layer.FilePath] = customLut;
            }
            else if (mode == "pseudocolor")
            {
                string ramp = (ComboColorRamp.SelectedItem as ComboBoxItem)?.Tag as string ?? "GLOBAL_MAPPER_ATLAS";
                _layer.ShaderMode = "atlas";
                _layer.Palette = ramp;
                RasterSymbologyService.LayerCustomLuts.Remove(_layer.FilePath);
            }
            else if (mode == "multiband")
            {
                _layer.ShaderMode = "rgb";
                _layer.Palette = null;
                RasterSymbologyService.LayerCustomLuts.Remove(_layer.FilePath);
            }
            else if (mode == "hillshade")
            {
                _layer.ShaderMode = "hillshade";
                _layer.Palette = "GRAY";
                RasterSymbologyService.LayerCustomLuts.Remove(_layer.FilePath);
            }
            else if (mode == "contours")
            {
                _layer.ShaderMode = "contours";
                _layer.Palette = null;
                RasterSymbologyService.LayerCustomLuts.Remove(_layer.FilePath);
            }
            else if (mode == "singlecolor")
            {
                _layer.ShaderMode = "singlecolor";
                _layer.Palette = null;
                RasterSymbologyService.LayerCustomLuts.Remove(_layer.FilePath);
            }
            else
            {
                _layer.ShaderMode = "none";
                _layer.Palette = null;
                RasterSymbologyService.LayerCustomLuts.Remove(_layer.FilePath);
            }

            try
            {
                string cacheDir = GdalCacheManager.GetCacheDirectory();
                string safeName = Path.GetFileNameWithoutExtension(_layer.FilePath);
                foreach (var f in Directory.GetFiles(cacheDir, $"*{safeName}*"))
                {
                    try { File.Delete(f); } catch { }
                }
            }
            catch { }

            string blendMode = (ComboBlendMode.SelectedItem as ComboBoxItem)?.Content as string ?? "Normal";
            string cssFilter = BuildCssFilterString();

            _ = System.Threading.Tasks.Task.Run(() =>
            {
                var meta = GdalOverviewGenerator.InspectAndGeneratePreview(
                    _layer.FilePath,
                    2048,
                    _layer.ShaderMode ?? "paletted",
                    _layer.Palette ?? "LULC"
                );

                Dispatcher.Invoke(() =>
                {
                    _main.PostMessageToMap(new
                    {
                        action = "updateRasterLayerStyle",
                        id = _layer.Id,
                        layerId = _layer.Id,
                        imageUrl = meta.PreviewUrl,
                        imageUri = meta.PreviewUrl,
                        shaderMode = _layer.ShaderMode,
                        palette = _layer.Palette,
                        opacity = _layer.Opacity,
                        blendMode = blendMode,
                        filter = cssFilter
                    });
                });
            });
        }

        private void BtnApply_Click(object sender, RoutedEventArgs e) => ApplySymbology();

        private void BtnShuffle_Click(object sender, RoutedEventArgs e) => ShuffleRandomColors();

        private void BtnSingleColor_Click(object sender, RoutedEventArgs e) => PickSingleColor();

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            ApplySymbology();
            Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e) => Close();
    }
}
