using System.Windows;
using GeoStudio.Models;

namespace GeoStudio
{
    public partial class MainWindow
    {
        internal void BtnAddOsm_Click(object sender, RoutedEventArgs e)
        {
            // Basemap removed
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
