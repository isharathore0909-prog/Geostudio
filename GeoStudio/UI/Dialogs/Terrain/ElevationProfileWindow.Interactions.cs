using System;
using System.IO;
using System.Windows;
using System.Windows.Input;
using GeoStudio.UI.Services;

namespace GeoStudio.UI
{
    public partial class ElevationProfileWindow : Window
    {
        private void PlotContainer_MouseMove(object sender, MouseEventArgs e)
        {
            if (_distances.Length < 2 || _elevations.Length < 2) return;

            Point mousePos = e.GetPosition(PlotContainer);
            double w = PlotContainer.ActualWidth;
            double h = PlotContainer.ActualHeight;

            const double padLeft = 65;
            const double padRight = 30;
            const double padTop = 30;
            const double padBottom = 40;

            double plotW = w - padLeft - padRight;
            double plotH = h - padTop - padBottom;

            if (mousePos.X < padLeft || mousePos.X > padLeft + plotW ||
                mousePos.Y < padTop || mousePos.Y > padTop + plotH)
            {
                HoverCard.Visibility = Visibility.Collapsed;
                return;
            }

            double totalDist = _distances[_distances.Length - 1];
            double relX = (mousePos.X - padLeft) / plotW;
            double targetDist = relX * totalDist;

            int bestIdx = 0;
            double bestDiff = double.MaxValue;
            for (int i = 0; i < _distances.Length; i++)
            {
                double diff = Math.Abs(_distances[i] - targetDist);
                if (diff < bestDiff)
                {
                    bestDiff = diff;
                    bestIdx = i;
                }
            }

            double currDist = _distances[bestIdx];
            double currElev = _elevations[bestIdx];

            double slope = 0;
            if (bestIdx > 0)
            {
                double dx = _distances[bestIdx] - _distances[bestIdx - 1];
                double dz = _elevations[bestIdx] - _elevations[bestIdx - 1];
                if (dx > 0.01) slope = Math.Atan(dz / dx) * (180.0 / Math.PI);
            }

            TxtHover.Text = $"Station: {currDist:F1} m\nElev:    {currElev:F2} m\nSlope:   {slope:F1}°";
            HoverCard.Visibility = Visibility.Visible;

            double cardX = mousePos.X + 15;
            if (cardX + 140 > w) cardX = mousePos.X - 150;
            double cardY = mousePos.Y - 20;
            if (cardY < 10) cardY = 10;

            HoverCard.Margin = new Thickness(cardX, cardY, 0, 0);
        }

        private void PlotContainer_MouseLeave(object sender, MouseEventArgs e)
        {
            HoverCard.Visibility = Visibility.Collapsed;
        }

        private void BtnInvert_Click(object sender, RoutedEventArgs e)
        {
            _isInverted = !_isInverted;
            Array.Reverse(_elevations);
            ComputeStatistics();
            DrawProfile();
            TxtSubtitle.Text = _isInverted ? "Transect direction inverted (B ➔ A)" : "Transect direction (A ➔ B)";
        }

        private void BtnExportCsv_Click(object sender, RoutedEventArgs e)
        {
            if (FileDialogHelper.PromptSave("CSV Files (*.csv)|*.csv", $"{Path.GetFileNameWithoutExtension(_layerName)}_elevation_profile.csv", "Export Elevation Profile CSV") is not { } savePath)
                return;

            using var sw = new StreamWriter(savePath);
            sw.WriteLine("Station_Distance_m,Elevation_m");
            for (int i = 0; i < _distances.Length; i++)
            {
                sw.WriteLine($"{_distances[i]:F3},{_elevations[i]:F3}");
            }
            MessageBox.Show($"Elevation transect exported to CSV ({_distances.Length} points).", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
