using System.Windows;
using GeoStudio.Models;

namespace GeoStudio
{
    public partial class MainWindow
    {
        internal void BtnAddOsm_Click(object sender, RoutedEventArgs e)
        {
            var osmLayer = FindLayer("osm_basemap");
            if (osmLayer != null)
            {
                osmLayer.IsVisible = !osmLayer.IsVisible;
                PostMessageToMap(new { action = "toggleLayer", id = "osm_basemap", visible = osmLayer.IsVisible });
                TxtStatus.Text = $"OpenStreetMap basemap {(osmLayer.IsVisible ? "enabled" : "hidden")}";
            }
            else
            {
                var osm = new LayerItem
                {
                    Id = "osm_basemap",
                    Name = "OpenStreetMap Basemap",
                    Type = LayerType.Basemap,
                    IsVisible = true,
                    Opacity = 1.0,
                    Details = "Global XYZ Tile Layer | EPSG:3857",
                    ColorHex = "#3B82F6"
                };
                Layers.Add(osm);
                UpdateLayerCount();
                PostMessageToMap(new { action = "toggleLayer", id = "osm_basemap", visible = true });
                TxtStatus.Text = "OpenStreetMap basemap enabled";
            }
        }

        internal void BtnDatabase_Click(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("Spatial Database Connection: Connect to PostGIS, Spatialite, or DuckDB spatial databases.", "Spatial Database", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        internal void BtnFileBrowser_Click(object sender, RoutedEventArgs e)
        {
            BtnAddVector_Click(sender, e);
        }
    }
}
