using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Raster;
using GeoStudio.UI.Services;
using OSGeo.GDAL;
using OSGeo.OSR;

namespace GeoStudio.UI.Dialogs.Layers.Tabs
{
    public partial class LayerSourceTab : UserControl
    {
        private LayerItem? _layer;

        public LayerSourceTab()
        {
            InitializeComponent();
        }

        public void BindLayer(LayerItem layer)
        {
            _layer = layer;
            TxtSourceLayerName.Text = layer.Name ?? "";
            TxtSourcePath.Text = layer.FilePath ?? "";

            DetectCrs(layer.FilePath);
        }

        public void ApplyChanges(LayerItem layer, MainWindow? main)
        {
            string newName = TxtSourceLayerName.Text.Trim();
            if (!string.IsNullOrWhiteSpace(newName) && newName != layer.Name)
            {
                layer.Name = newName;
                if (main?.TxtStatus != null)
                {
                    main.TxtStatus.Text = $"Renamed layer to: {layer.Name}";
                }
            }
        }

        private void DetectCrs(string? filePath)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath)) return;
            try
            {
                GdalCacheManager.Initialize();
                using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
                if (ds != null)
                {
                    string projWkt = ds.GetProjectionRef();
                    if (!string.IsNullOrWhiteSpace(projWkt))
                    {
                        using var srs = new SpatialReference(projWkt);
                        string authCode = srs.GetAuthorityCode(null) ?? srs.GetAuthorityCode("PROJCS") ?? srs.GetAuthorityCode("GEOGCS") ?? "";
                        string srsName = srs.GetName();
                        if (!string.IsNullOrEmpty(authCode))
                        {
                            SetDetectedCrs($"EPSG:{authCode} - {srsName}");
                        }
                    }
                }
            }
            catch { }
        }

        private void SetDetectedCrs(string crsDisplay)
        {
            foreach (ComboBoxItem item in ComboCrs.Items)
            {
                if (item.Content?.ToString()?.StartsWith(crsDisplay.Split('-')[0].Trim(), StringComparison.OrdinalIgnoreCase) == true)
                {
                    ComboCrs.SelectedItem = item;
                    return;
                }
            }
            var newItem = new ComboBoxItem { Content = crsDisplay, IsSelected = true };
            ComboCrs.Items.Insert(0, newItem);
            ComboCrs.SelectedIndex = 0;
        }

        private void BtnBrowseSource_Click(object sender, RoutedEventArgs e) =>
            FileDialogHelper.PromptOpenInto(TxtSourcePath, "All Supported Files|*.tif;*.tiff;*.geojson;*.shp;*.laz;*.las|GeoTIFF Rasters (*.tif)|*.tif;*.tiff|Vector Files (*.geojson;*.shp)|*.geojson;*.shp|All Files (*.*)|*.*", "Select Layer Data Source");
    }
}
