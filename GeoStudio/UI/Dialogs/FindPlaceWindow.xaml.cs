using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace GeoStudio.UI.Dialogs
{
    public class PlaceItem
    {
        public string Name { get; set; } = "";
        public string Description { get; set; } = "";
        public string CategoryIcon { get; set; } = "📍";
        public double Lon { get; set; }
        public double Lat { get; set; }
        public double Zoom { get; set; } = 12.0;
        public string CoordinatesText => $"{Lat:F4}°, {Lon:F4}°";
    }

    public partial class FindPlaceWindow : Window
    {
        private readonly Action<double, double, double, string>? _onNavigate;
        private readonly List<PlaceItem> _allPlaces = new();
        public ObservableCollection<PlaceItem> FilteredPlaces { get; set; } = new();

        public FindPlaceWindow(Action<double, double, double, string>? onNavigate)
        {
            InitializeComponent();
            _onNavigate = onNavigate;
            LoadBuiltInGazetteer();
            FilterPlaces("");
        }

        private void LoadBuiltInGazetteer()
        {
            _allPlaces.AddRange(new[]
            {
                new PlaceItem { Name = "New Delhi", Description = "Capital City, India", CategoryIcon = "🏛️", Lon = 77.2090, Lat = 28.6139, Zoom = 12.0 },
                new PlaceItem { Name = "Mumbai", Description = "Maharashtra, India", CategoryIcon = "🏙️", Lon = 72.8777, Lat = 19.0760, Zoom = 12.0 },
                new PlaceItem { Name = "Bengaluru", Description = "Karnataka, India", CategoryIcon = "🏙️", Lon = 77.5946, Lat = 12.9716, Zoom = 12.0 },
                new PlaceItem { Name = "Mount Everest", Description = "Highest Peak, Himalayas, Nepal/Tibet", CategoryIcon = "🏔️", Lon = 86.9250, Lat = 27.9881, Zoom = 13.0 },
                new PlaceItem { Name = "Grand Canyon", Description = "National Park, Arizona, USA", CategoryIcon = "🏞️", Lon = -112.1129, Lat = 36.1069, Zoom = 12.0 },
                new PlaceItem { Name = "Tokyo", Description = "Capital City, Japan", CategoryIcon = "🏙️", Lon = 139.6917, Lat = 35.6895, Zoom = 12.0 },
                new PlaceItem { Name = "London", Description = "Capital City, United Kingdom", CategoryIcon = "🏛️", Lon = -0.1276, Lat = 51.5072, Zoom = 12.0 },
                new PlaceItem { Name = "Paris", Description = "Capital City, France", CategoryIcon = "🗼", Lon = 2.3522, Lat = 48.8566, Zoom = 12.0 },
                new PlaceItem { Name = "New York City", Description = "New York, USA", CategoryIcon = "🗽", Lon = -74.0060, Lat = 40.7128, Zoom = 12.0 },
                new PlaceItem { Name = "San Francisco", Description = "California, USA", CategoryIcon = "🌉", Lon = -122.4194, Lat = 37.7749, Zoom = 12.0 },
                new PlaceItem { Name = "Sydney", Description = "New South Wales, Australia", CategoryIcon = "⛵", Lon = 151.2093, Lat = -33.8688, Zoom = 12.0 },
                new PlaceItem { Name = "Dubai", Description = "United Arab Emirates", CategoryIcon = "🏙️", Lon = 55.2708, Lat = 25.2048, Zoom = 12.0 },
                new PlaceItem { Name = "Cairo", Description = "Capital City, Egypt", CategoryIcon = "🏛️", Lon = 31.2357, Lat = 30.0444, Zoom = 12.0 },
                new PlaceItem { Name = "Mount Fuji", Description = "Volcanic Peak, Honshu, Japan", CategoryIcon = "🌋", Lon = 138.7274, Lat = 35.3606, Zoom = 13.0 },
                new PlaceItem { Name = "Matterhorn", Description = "Alps Ridge, Switzerland/Italy", CategoryIcon = "🏔️", Lon = 7.7584, Lat = 45.9765, Zoom = 13.0 },
                new PlaceItem { Name = "Rio de Janeiro", Description = "State of Rio de Janeiro, Brazil", CategoryIcon = "🏖️", Lon = -43.1729, Lat = -22.9068, Zoom = 12.0 },
                new PlaceItem { Name = "Singapore", Description = "Republic of Singapore", CategoryIcon = "🦁", Lon = 103.8198, Lat = 1.3521, Zoom = 12.5 },
                new PlaceItem { Name = "Reykjavik", Description = "Capital City, Iceland", CategoryIcon = "🧊", Lon = -21.9426, Lat = 64.1466, Zoom = 12.0 },
                new PlaceItem { Name = "Victoria Falls", Description = "Zambia / Zimbabwe Border", CategoryIcon = "🌊", Lon = 25.8572, Lat = -17.9243, Zoom = 13.0 },
                new PlaceItem { Name = "Niagara Falls", Description = "New York USA / Ontario Canada", CategoryIcon = "🌊", Lon = -79.0377, Lat = 43.0896, Zoom = 13.0 }
            });
        }

        private void FilterPlaces(string query)
        {
            FilteredPlaces.Clear();
            var matches = string.IsNullOrWhiteSpace(query)
                ? _allPlaces
                : _allPlaces.Where(p => p.Name.Contains(query, StringComparison.OrdinalIgnoreCase) || p.Description.Contains(query, StringComparison.OrdinalIgnoreCase)).ToList();

            foreach (var m in matches) FilteredPlaces.Add(m);
            LstPlaces.ItemsSource = FilteredPlaces;
            if (FilteredPlaces.Count > 0) LstPlaces.SelectedIndex = 0;
            TxtMatchCount.Text = $"{FilteredPlaces.Count} locations available";
        }

        private void TxtSearch_TextChanged(object sender, TextChangedEventArgs e)
        {
            FilterPlaces(TxtSearch.Text.Trim());
        }

        private void TxtSearch_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                if (FilteredPlaces.Count > 0)
                {
                    BtnFlyTo_Click(sender, e);
                }
                else
                {
                    BtnOnlineSearch_Click(sender, e);
                }
            }
        }

        private async void BtnOnlineSearch_Click(object sender, RoutedEventArgs e)
        {
            string query = TxtSearch.Text.Trim();
            if (string.IsNullOrEmpty(query)) return;

            TxtMatchCount.Text = "Searching OpenStreetMap Nominatim geocoder...";
            try
            {
                using var client = new HttpClient();
                client.DefaultRequestHeaders.Add("User-Agent", "GeoStudio-GIS/2.0");
                string url = $"https://nominatim.openstreetmap.org/search?q={Uri.EscapeDataString(query)}&format=json&limit=8";
                string json = await client.GetStringAsync(url);

                using var doc = JsonDocument.Parse(json);
                var arr = doc.RootElement;
                if (arr.GetArrayLength() > 0)
                {
                    FilteredPlaces.Clear();
                    foreach (var elem in arr.EnumerateArray())
                    {
                        string displayName = elem.GetProperty("display_name").GetString() ?? query;
                        string latStr = elem.GetProperty("lat").GetString() ?? "0";
                        string lonStr = elem.GetProperty("lon").GetString() ?? "0";

                        double lat = double.Parse(latStr, CultureInfo.InvariantCulture);
                        double lon = double.Parse(lonStr, CultureInfo.InvariantCulture);

                        var firstComma = displayName.IndexOf(',');
                        string shortName = firstComma > 0 ? displayName.Substring(0, firstComma) : displayName;
                        string desc = firstComma > 0 ? displayName.Substring(firstComma + 1).Trim() : "Geocoded Location";

                        FilteredPlaces.Add(new PlaceItem
                        {
                            Name = shortName,
                            Description = desc,
                            CategoryIcon = "🌐",
                            Lon = lon,
                            Lat = lat,
                            Zoom = 13.0
                        });
                    }
                    if (FilteredPlaces.Count > 0) LstPlaces.SelectedIndex = 0;
                    TxtMatchCount.Text = $"{FilteredPlaces.Count} online results found";
                }
                else
                {
                    TxtMatchCount.Text = "No online matches found for query";
                }
            }
            catch (Exception)
            {
                TxtMatchCount.Text = "Online search unavailable (offline mode active)";
            }
        }

        private void BtnFlyTo_Click(object sender, RoutedEventArgs e)
        {
            if (LstPlaces.SelectedItem is PlaceItem p)
            {
                _onNavigate?.Invoke(p.Lon, p.Lat, p.Zoom, p.Name);
                Close();
            }
        }

        private void LstPlaces_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            BtnFlyTo_Click(sender, e);
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
