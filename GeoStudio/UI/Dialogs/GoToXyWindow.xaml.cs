using System;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Dialogs
{
    public partial class GoToXyWindow : Window
    {
        private readonly Action<double, double, double, string>? _onNavigate;

        public GoToXyWindow(Action<double, double, double, string>? onNavigate)
        {
            InitializeComponent();
            _onNavigate = onNavigate;
        }

        private void SliderZoom_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (TxtZoomVal != null) TxtZoomVal.Text = $"{e.NewValue:F1}x";
        }

        private void TxtQuickPaste_TextChanged(object sender, TextChangedEventArgs e)
        {
            string text = TxtQuickPaste.Text.Trim();
            if (string.IsNullOrEmpty(text)) return;

            var parts = text.Split(new[] { ',', ' ', '\t', ';' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length >= 2)
            {
                if (double.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out double lat) &&
                    double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out double lon))
                {
                    // Detect if first is Lon or Lat
                    if (Math.Abs(lat) <= 90 && Math.Abs(lon) <= 180)
                    {
                        TxtLatitude.Text = lat.ToString(CultureInfo.InvariantCulture);
                        TxtLongitude.Text = lon.ToString(CultureInfo.InvariantCulture);
                    }
                    else if (Math.Abs(lat) <= 180 && Math.Abs(lon) <= 90)
                    {
                        TxtLatitude.Text = lon.ToString(CultureInfo.InvariantCulture);
                        TxtLongitude.Text = lat.ToString(CultureInfo.InvariantCulture);
                    }
                }
            }
        }

        private void BtnGo_Click(object sender, RoutedEventArgs e)
        {
            if (!double.TryParse(TxtLatitude.Text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out double lat) || lat < -90 || lat > 90)
            {
                MessageBox.Show("Please enter a valid Latitude between -90.0 and +90.0 degrees.", "Invalid Coordinate", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (!double.TryParse(TxtLongitude.Text.Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out double lon) || lon < -180 || lon > 180)
            {
                MessageBox.Show("Please enter a valid Longitude between -180.0 and +180.0 degrees.", "Invalid Coordinate", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            double zoom = SliderZoom.Value;
            string label = (ChkDropPin.IsChecked == true) ? $"Coordinate ({lat:F4}°, {lon:F4}°)" : "";

            _onNavigate?.Invoke(lon, lat, zoom, label);
            Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e) => Close();
    }
}
