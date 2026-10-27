using System;
using System.IO;
using System.Windows;
using Microsoft.Win32;
using GeoStudio.Routing.Models;
using GeoStudio.Routing.Services;

namespace GeoStudio.UI.Dialogs.Routing
{
    public partial class RoutingWindow : Window
    {
        private RouteGeometryResponse? _lastRoute;

        public RoutingWindow()
        {
            InitializeComponent();
        }

        private void BtnPickOrigin_Click(object sender, RoutedEventArgs e)
        {
            TxtStatusMsg.Text = "Origin picker active. Current coordinates retained.";
        }

        private void BtnPickDest_Click(object sender, RoutedEventArgs e)
        {
            TxtStatusMsg.Text = "Destination picker active. Current coordinates retained.";
        }

        private void BtnComputeRoute_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                if (!TryParseCoords(TxtStartCoords.Text, out double sLng, out double sLat) ||
                    !TryParseCoords(TxtEndCoords.Text, out double eLng, out double eLat))
                {
                    MessageBox.Show("Please enter valid Longitude, Latitude coordinates (e.g. 75.78, 26.91).", "Invalid Coordinates", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                var opt = RadioFastest.IsChecked == true ? RoutingOptimization.FastestTime : RoutingOptimization.ShortestDistance;
                _lastRoute = RoadRoutingService.Instance.Route(sLng, sLat, eLng, eLat, opt);

                if (_lastRoute.Success)
                {
                    TxtResultDistance.Text = $"Total Distance: {_lastRoute.DistanceKm:F2} km ({_lastRoute.DistanceKm * 0.621371:F2} miles)";
                    TxtResultDuration.Text = $"Estimated Duration: {_lastRoute.DurationMin:F1} minutes";
                    TxtResultTime.Text = $"Calculation Time: {_lastRoute.SearchTimeMs:F1} ms";
                    TxtStatusMsg.Text = $"Route computed successfully ({_lastRoute.Coordinates.Count} path vertices).";
                }
                else
                {
                    TxtStatusMsg.Text = $"Routing error: {_lastRoute.ErrorMessage}";
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Route calculation failed: {ex.Message}", "Routing Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnDrawOnMap_Click(object sender, RoutedEventArgs e)
        {
            if (_lastRoute == null || !_lastRoute.Success || string.IsNullOrEmpty(_lastRoute.GeoJson))
            {
                MessageBox.Show("Please compute a route first before adding to the map.", "No Route", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var main = Application.Current.MainWindow as MainWindow;
            if (main != null)
            {
                // Send GeoJSON to map
                string tempPath = Path.Combine(Path.GetTempPath(), $"route_{Guid.NewGuid():N}.geojson");
                File.WriteAllText(tempPath, _lastRoute.GeoJson);
                main.LoadVectorFile(tempPath, customColor: "#4F46E5");
                TxtStatusMsg.Text = "Route layer added to map canvas.";
            }
        }

        private void BtnExportGeoJson_Click(object sender, RoutedEventArgs e)
        {
            if (_lastRoute == null || string.IsNullOrEmpty(_lastRoute.GeoJson))
            {
                MessageBox.Show("Please calculate a route before exporting.", "No Data", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var sfd = new SaveFileDialog
            {
                Filter = "GeoJSON File (*.geojson)|*.geojson",
                FileName = "optimized_route.geojson"
            };

            if (sfd.ShowDialog() == true)
            {
                File.WriteAllText(sfd.FileName, _lastRoute.GeoJson);
                MessageBox.Show($"Route GeoJSON exported to:\n{sfd.FileName}", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private static bool TryParseCoords(string input, out double lng, out double lat)
        {
            lng = 0; lat = 0;
            if (string.IsNullOrWhiteSpace(input)) return false;
            string[] parts = input.Split(new[] { ',', ' ' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length >= 2 && double.TryParse(parts[0], out lng) && double.TryParse(parts[1], out lat))
            {
                return true;
            }
            return false;
        }
    }
}
