using System;
using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Input;

namespace GeoStudio.UI.Dialogs
{
    public class BookmarkItem
    {
        public string Name { get; set; } = "";
        public double Lon { get; set; }
        public double Lat { get; set; }
        public double Zoom { get; set; }
        public string Details => $"Lon: {Lon:F4}°, Lat: {Lat:F4}°";
        public string ZoomText => $"Zoom {Zoom:F1}x";
    }

    public partial class BookmarksWindow : Window
    {
        public ObservableCollection<BookmarkItem> Bookmarks { get; set; } = new();
        private readonly Action<double, double, double>? _onNavigate;
        private readonly (double lon, double lat, double zoom)? _currentExtent;

        private static readonly ObservableCollection<BookmarkItem> SharedBookmarks = new()
        {
            new BookmarkItem { Name = "Global Overview", Lon = 76.515, Lat = 24.762, Zoom = 4.5 },
            new BookmarkItem { Name = "Himalayan Ridge & Mt. Everest", Lon = 86.9250, Lat = 27.9881, Zoom = 12.0 },
            new BookmarkItem { Name = "Grand Canyon National Park", Lon = -112.1129, Lat = 36.1069, Zoom = 11.0 },
            new BookmarkItem { Name = "Swiss Alps (Matterhorn Peak)", Lon = 7.7584, Lat = 45.9765, Zoom = 12.0 },
            new BookmarkItem { Name = "Tokyo Bay & Coastal Plain", Lon = 139.7671, Lat = 35.6812, Zoom = 11.5 }
        };

        public BookmarksWindow((double lon, double lat, double zoom)? currentExtent, Action<double, double, double>? onNavigate)
        {
            InitializeComponent();
            _currentExtent = currentExtent;
            _onNavigate = onNavigate;
            Bookmarks = SharedBookmarks;
            LstBookmarks.ItemsSource = Bookmarks;
            if (Bookmarks.Count > 0) LstBookmarks.SelectedIndex = 0;
        }

        private void BtnFlyTo_Click(object sender, RoutedEventArgs e)
        {
            if (LstBookmarks.SelectedItem is BookmarkItem b)
            {
                _onNavigate?.Invoke(b.Lon, b.Lat, b.Zoom);
                Close();
            }
        }

        private void LstBookmarks_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            BtnFlyTo_Click(sender, e);
        }

        private void BtnSaveCurrent_Click(object sender, RoutedEventArgs e)
        {
            if (!_currentExtent.HasValue)
            {
                MessageBox.Show("Current map extent is not available yet.", "Bookmark", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            string name = TxtNewBookmarkName.Text.Trim();
            if (string.IsNullOrEmpty(name)) name = $"Bookmark {Bookmarks.Count + 1}";

            var item = new BookmarkItem
            {
                Name = name,
                Lon = _currentExtent.Value.lon,
                Lat = _currentExtent.Value.lat,
                Zoom = _currentExtent.Value.zoom
            };

            Bookmarks.Add(item);
            LstBookmarks.SelectedItem = item;
            TxtNewBookmarkName.Text = "New View Bookmark";
        }

        private void BtnDelete_Click(object sender, RoutedEventArgs e)
        {
            if (LstBookmarks.SelectedItem is BookmarkItem b)
            {
                Bookmarks.Remove(b);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
