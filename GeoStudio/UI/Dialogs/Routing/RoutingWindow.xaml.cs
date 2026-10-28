using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using GeoStudio.Routing.Models;
using GeoStudio.Routing.Services;
using GeoStudio.UI.Services;
using Microsoft.Win32;

namespace GeoStudio.UI.Dialogs.Routing
{
    public partial class RoutingWindow : Window
    {
        private readonly MainWindow? _main;
        private RouteGeometryResponse? _lastRoute;
        private readonly List<(double Lng, double Lat, string Name)> _destCentroids = new();

        public RoutingWindow() : this(Application.Current.MainWindow as MainWindow) { }

        public RoutingWindow(MainWindow? main)
        {
            InitializeComponent();
            _main = main;
            AutoDetectCentroidsLayer();
        }

        private void AutoDetectCentroidsLayer()
        {
            if (_main?.Layers != null)
            {
                foreach (var l in _main.Layers)
                {
                    if (l.Type == Models.LayerType.Vector && !string.IsNullOrEmpty(l.FilePath) && File.Exists(l.FilePath))
                    {
                        if (l.Name.Contains("centroid", StringComparison.OrdinalIgnoreCase) ||
                            l.FilePath.Contains("centroid", StringComparison.OrdinalIgnoreCase))
                        {
                            TxtDestGeoJson.Text = l.FilePath;
                            return;
                        }
                    }
                }
            }

            string downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads", "Bhairwanda_centroids.geojson");
            if (File.Exists(downloads))
            {
                TxtDestGeoJson.Text = downloads;
            }
        }

        private void CalculateOption_Changed(object sender, RoutedEventArgs e)
        {
            if (GridRoadMetric != null && ChkRoad != null)
            {
                GridRoadMetric.Visibility = ChkRoad.IsChecked == true ? Visibility.Visible : Visibility.Collapsed;
            }
        }

        private void BtnPickOrigin_Click(object sender, RoutedEventArgs e)
        {
            _main?.StartOriginPicker(this);
            TxtStatusMsg.Text = "📍 Click anywhere on the map canvas to set Origin.";
        }

        public void SetOriginCoordinate(double lon, double lat)
        {
            Dispatcher.Invoke(() =>
            {
                TxtStartCoords.Text = $"{lon:F5}, {lat:F5}";
                TxtStatusMsg.Text = $"✓ Origin set: {lat:F5}°, {lon:F5}°";
                WindowState = WindowState.Normal;
                Activate();
            });
        }

        private void BtnBrowseDest_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog { Title = "Select Centroids GeoJSON", Filter = "GeoJSON (*.geojson;*.json)|*.geojson;*.json" };
            if (dlg.ShowDialog() == true) TxtDestGeoJson.Text = dlg.FileName;
        }

        private void TxtDestGeoJson_TextChanged(object sender, System.Windows.Controls.TextChangedEventArgs e)
        {
            _destCentroids.Clear();
            string path = TxtDestGeoJson.Text.Trim();
            if (!File.Exists(path)) return;

            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                if (doc.RootElement.TryGetProperty("features", out var feats))
                {
                    int idx = 1;
                    foreach (var f in feats.EnumerateArray())
                    {
                        if (f.TryGetProperty("geometry", out var g) && g.TryGetProperty("coordinates", out var c) && c.GetArrayLength() >= 2)
                        {
                            string name = $"Centroid #{idx++}";
                            if (f.TryGetProperty("properties", out var p) && p.TryGetProperty("name", out var np))
                                name = np.GetString() ?? name;
                            _destCentroids.Add((c[0].GetDouble(), c[1].GetDouble(), name));
                        }
                    }
                }
            }
            catch { }
        }

        private async void BtnComputeRoute_Click(object sender, RoutedEventArgs e)
        {
            if (!TryParseCoords(TxtStartCoords.Text, out double sLng, out double sLat))
            {
                MessageBox.Show("Specify valid Origin coordinates or click '📍 Map Click'.", "Origin Missing", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (_destCentroids.Count == 0)
            {
                MessageBox.Show("Browse or select a valid Centroids GeoJSON file first.", "Centroids Missing", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            bool doRoad = ChkRoad.IsChecked == true;
            bool doAerial = ChkAerial.IsChecked == true;

            if (!doRoad && !doAerial)
            {
                MessageBox.Show("Please check at least one calculation option (Road Distance or Aerial Distance).", "Select Calculation", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            BtnComputeRoute.IsEnabled = false;
            TxtStatusMsg.Text = $"Calculating distances for {_destCentroids.Count} centroids...";

            var opt = RadioFastest.IsChecked == true ? RoutingOptimization.FastestTime : RoutingOptimization.ShortestDistance;
            var sw = Stopwatch.StartNew();

            try
            {
                var (routes, roadTotal, aerialTotal, totalDur, solvedCount) = await System.Threading.Tasks.Task.Run(() =>
                {
                    double rSum = 0, aSum = 0, dSum = 0;
                    var routeList = new List<object>();

                    foreach (var d in _destCentroids)
                    {
                        RouteGeometryResponse? roadResp = null;
                        RouteGeometryResponse? aerialResp = null;

                        if (doRoad)
                        {
                            roadResp = RoadRoutingService.Instance.Route(sLng, sLat, d.Lng, d.Lat, opt);
                            if (roadResp.Success)
                            {
                                rSum += roadResp.DistanceKm;
                                dSum += roadResp.DurationMin;
                                routeList.Add(new
                                {
                                    type = "Feature",
                                    geometry = new { type = "LineString", coordinates = roadResp.Coordinates },
                                    properties = new
                                    {
                                        target = d.Name,
                                        type = "Road Route",
                                        distance_km = Math.Round(roadResp.DistanceKm, 2),
                                        duration_min = Math.Round(roadResp.DurationMin, 1)
                                    }
                                });
                            }
                        }

                        if (doAerial)
                        {
                            aerialResp = RoadRoutingService.Instance.RouteAerial(sLng, sLat, d.Lng, d.Lat);
                            if (aerialResp.Success)
                            {
                                aSum += aerialResp.DistanceKm;
                                if (!doRoad) dSum += aerialResp.DurationMin;

                                routeList.Add(new
                                {
                                    type = "Feature",
                                    geometry = new { type = "LineString", coordinates = aerialResp.Coordinates },
                                    properties = new
                                    {
                                        target = d.Name,
                                        type = "Aerial Air Line",
                                        distance_km = Math.Round(aerialResp.DistanceKm, 2),
                                        duration_min = Math.Round(aerialResp.DurationMin, 1)
                                    }
                                });
                            }
                        }
                    }

                    return (routeList, rSum, aSum, dSum, _destCentroids.Count);
                });

                sw.Stop();
                if (routes.Count == 0)
                {
                    TxtStatusMsg.Text = "Could not compute paths to centroids.";
                    return;
                }

                _lastRoute = new RouteGeometryResponse
                {
                    Success = true,
                    DistanceKm = doRoad ? roadTotal : aerialTotal,
                    DurationMin = totalDur,
                    SearchTimeMs = sw.Elapsed.TotalMilliseconds,
                    GeoJson = JsonSerializer.Serialize(new { type = "FeatureCollection", features = routes })
                };

                // Display Road Distance
                if (doRoad)
                    TxtResultRoad.Text = $"🚗 Road Distance: {roadTotal:F2} km (Avg: {roadTotal / solvedCount:F2} km / centroid)";
                else
                    TxtResultRoad.Text = "🚗 Road Distance: (Not selected)";

                // Display Aerial Distance
                if (doAerial)
                    TxtResultAerial.Text = $"✈️ Aerial Distance: {aerialTotal:F2} km (Avg: {aerialTotal / solvedCount:F2} km / centroid)";
                else
                    TxtResultAerial.Text = "✈️ Aerial Distance: (Not selected)";

                // Duration & Circuity Factor
                if (doRoad && doAerial && aerialTotal > 0)
                    TxtResultDuration.Text = $"Road/Aerial Factor: {roadTotal / aerialTotal:F2}x • Est. Drive Duration: {totalDur:F1} min";
                else if (doRoad)
                    TxtResultDuration.Text = $"Estimated Drive Duration: {totalDur:F1} min";
                else
                    TxtResultDuration.Text = $"Direct Flight Duration: {totalDur:F1} min";

                TxtResultTime.Text = $"Solved {routes.Count} lines across {solvedCount} centroids in {sw.Elapsed.TotalMilliseconds:F0} ms";
                TxtStatusMsg.Text = $"✓ Calculated distances for all {solvedCount} centroids. Click 'Draw on Map' to display.";
            }
            finally
            {
                BtnComputeRoute.IsEnabled = true;
            }
        }

        private void BtnDrawOnMap_Click(object sender, RoutedEventArgs e)
        {
            if (_lastRoute?.GeoJson == null) { MessageBox.Show("Compute routes first.", "No Route", MessageBoxButton.OK, MessageBoxImage.Information); return; }
            string tmp = Path.Combine(Path.GetTempPath(), $"routes_{DateTime.Now:yyyyMMdd_HHmmss}.geojson");
            File.WriteAllText(tmp, _lastRoute.GeoJson);
            string routeColor = (ChkRoad.IsChecked == true) ? "#4F46E5" : "#0284C7";
            _main?.LoadVectorFile(tmp, customColor: routeColor);
            TxtStatusMsg.Text = "✓ Route layer added to map canvas.";
        }

        private void BtnExportGeoJson_Click(object sender, RoutedEventArgs e)
        {
            if (_lastRoute?.GeoJson == null) { MessageBox.Show("Compute routes first.", "No Route", MessageBoxButton.OK, MessageBoxImage.Warning); return; }
            if (FileDialogHelper.PromptSave("GeoJSON File (*.geojson)|*.geojson", "centroid_routes.geojson") is { } savePath)
            {
                File.WriteAllText(savePath, _lastRoute.GeoJson);
                MessageBox.Show($"Exported to:\n{savePath}", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();

        private static bool TryParseCoords(string input, out double lng, out double lat)
        {
            lng = 0; lat = 0;
            if (string.IsNullOrWhiteSpace(input)) return false;
            string[] p = input.Split(new[] { ',', ' ' }, StringSplitOptions.RemoveEmptyEntries);
            return p.Length >= 2 &&
                   double.TryParse(p[0], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out lng) &&
                   double.TryParse(p[1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out lat);
        }
    }
}
