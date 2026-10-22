using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;
using Microsoft.Win32;

namespace GeoStudio.UI
{
    public partial class ElevationProfileWindow : Window
    {
        private string _layerName;
        private double[] _distances;
        private double[] _elevations;
        private bool _isInverted = false;

        public ElevationProfileWindow(string layerName, double[] distances, double[] elevations)
        {
            InitializeComponent();
            _layerName = layerName;
            _distances = distances ?? Array.Empty<double>();
            _elevations = elevations ?? Array.Empty<double>();

            TxtTitle.Text = $"Elevation Profile: {_layerName}";
            TxtSubtitle.Text = $"Cross-section transect ({_elevations.Length} sampled elevation points)";

            ComputeStatistics();
            Loaded += (s, e) => DrawProfile();
        }

        public void UpdateData(string layerName, double[] distances, double[] elevations)
        {
            _layerName = layerName;
            _distances = distances ?? Array.Empty<double>();
            _elevations = elevations ?? Array.Empty<double>();
            _isInverted = false;

            TxtTitle.Text = $"Elevation Profile: {_layerName}";
            TxtSubtitle.Text = $"Cross-section transect ({_elevations.Length} sampled elevation points)";

            ComputeStatistics();
            DrawProfile();
        }

        private void ComputeStatistics()
        {
            if (_distances.Length == 0 || _elevations.Length == 0) return;

            double totalDist = _distances[_distances.Length - 1];
            double minElev = _elevations.Min();
            double maxElev = _elevations.Max();
            double relief = maxElev - minElev;

            double gain = 0;
            double loss = 0;
            double maxSlopeDeg = 0;
            double sumSlopeDeg = 0;
            int slopeCount = 0;

            for (int i = 1; i < _elevations.Length; i++)
            {
                double dz = _elevations[i] - _elevations[i - 1];
                double dx = _distances[i] - _distances[i - 1];

                if (dz > 0) gain += dz;
                else loss += Math.Abs(dz);

                if (dx > 0.001)
                {
                    double slopeDeg = Math.Atan(Math.Abs(dz) / dx) * (180.0 / Math.PI);
                    if (slopeDeg > maxSlopeDeg) maxSlopeDeg = slopeDeg;
                    sumSlopeDeg += slopeDeg;
                    slopeCount++;
                }
            }

            double avgSlopeDeg = slopeCount > 0 ? (sumSlopeDeg / slopeCount) : 0;

            TxtLength.Text = totalDist >= 1000 ? $"{totalDist / 1000.0:F2} km" : $"{totalDist:F1} m";
            TxtMinElev.Text = $"{minElev:F1} m";
            TxtMaxElev.Text = $"{maxElev:F1} m";
            TxtRelief.Text = $"{relief:F1} m";
            TxtGainLoss.Text = $"+{gain:F1}m / -{loss:F1}m";
            TxtSlope.Text = $"{avgSlopeDeg:F1}° / {maxSlopeDeg:F1}°";
        }

        private void PlotContainer_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            DrawProfile();
        }

        private void DrawProfile()
        {
            PlotCanvas.Children.Clear();
            if (_distances.Length < 2 || _elevations.Length < 2) return;

            double w = PlotContainer.ActualWidth;
            double h = PlotContainer.ActualHeight;
            if (w < 100 || h < 100) return;

            const double padLeft = 65;
            const double padRight = 30;
            const double padTop = 30;
            const double padBottom = 40;

            double plotW = Math.Max(10, w - padLeft - padRight);
            double plotH = Math.Max(10, h - padTop - padBottom);

            double totalDist = _distances[_distances.Length - 1];
            if (totalDist <= 0.001) totalDist = 1.0;

            double minElev = _elevations.Min();
            double maxElev = _elevations.Max();
            double elevRange = maxElev - minElev;
            if (elevRange <= 0.001) elevRange = 10.0;

            // Add 10% breathing room to elevation range
            double elevMinPlot = minElev - elevRange * 0.08;
            double elevMaxPlot = maxElev + elevRange * 0.08;
            double plotElevRange = elevMaxPlot - elevMinPlot;

            // 1. Grid Lines & Axis Labels (Elevations)
            int yTicks = 5;
            for (int i = 0; i <= yTicks; i++)
            {
                double frac = (double)i / yTicks;
                double y = padTop + plotH * (1.0 - frac);
                double elevVal = elevMinPlot + frac * plotElevRange;

                var gridLine = new Line
                {
                    X1 = padLeft,
                    Y1 = y,
                    X2 = padLeft + plotW,
                    Y2 = y,
                    Stroke = new SolidColorBrush(Color.FromArgb(40, 148, 163, 184)),
                    StrokeThickness = 1,
                    StrokeDashArray = new DoubleCollection { 3, 3 }
                };
                PlotCanvas.Children.Add(gridLine);

                var txt = new TextBlock
                {
                    Text = $"{elevVal:F0} m",
                    FontSize = 10,
                    Foreground = new SolidColorBrush(Color.FromRgb(148, 163, 184)),
                    FontFamily = new FontFamily("Consolas")
                };
                Canvas.SetLeft(txt, 10);
                Canvas.SetTop(txt, y - 8);
                PlotCanvas.Children.Add(txt);
            }

            // 2. Grid Lines & Axis Labels (Distances)
            int xTicks = 6;
            for (int i = 0; i <= xTicks; i++)
            {
                double frac = (double)i / xTicks;
                double x = padLeft + plotW * frac;
                double distVal = frac * totalDist;

                var gridLine = new Line
                {
                    X1 = x,
                    Y1 = padTop,
                    X2 = x,
                    Y2 = padTop + plotH,
                    Stroke = new SolidColorBrush(Color.FromArgb(40, 148, 163, 184)),
                    StrokeThickness = 1,
                    StrokeDashArray = new DoubleCollection { 3, 3 }
                };
                PlotCanvas.Children.Add(gridLine);

                string dStr = distVal >= 1000 ? $"{distVal / 1000.0:F1}k" : $"{distVal:F0}m";
                var txt = new TextBlock
                {
                    Text = dStr,
                    FontSize = 10,
                    Foreground = new SolidColorBrush(Color.FromRgb(148, 163, 184)),
                    FontFamily = new FontFamily("Consolas")
                };
                Canvas.SetLeft(txt, x - 12);
                Canvas.SetTop(txt, padTop + plotH + 8);
                PlotCanvas.Children.Add(txt);
            }

            // 3. Build Polyline and Polygon Area Fill
            var points = new PointCollection(_distances.Length);
            for (int i = 0; i < _distances.Length; i++)
            {
                double d = _distances[i];
                double e = _elevations[i];
                double px = padLeft + (d / totalDist) * plotW;
                double py = padTop + plotH * (1.0 - (e - elevMinPlot) / plotElevRange);
                points.Add(new Point(px, py));
            }

            // Fill area under profile
            var fillPoints = new PointCollection(points)
            {
                new Point(padLeft + plotW, padTop + plotH),
                new Point(padLeft, padTop + plotH)
            };

            var polyFill = new Polygon
            {
                Points = fillPoints,
                Fill = new LinearGradientBrush
                {
                    StartPoint = new Point(0, 0),
                    EndPoint = new Point(0, 1),
                    GradientStops = new GradientStopCollection
                    {
                        new GradientStop(Color.FromArgb(160, 2, 132, 199), 0.0),
                        new GradientStop(Color.FromArgb(20, 16, 185, 129), 1.0)
                    }
                }
            };
            PlotCanvas.Children.Add(polyFill);

            // Profile Line
            var polyLine = new System.Windows.Shapes.Polyline
            {
                Points = points,
                Stroke = new SolidColorBrush(Color.FromRgb(56, 189, 248)),
                StrokeThickness = 2.5,
                StrokeLineJoin = PenLineJoin.Round
            };
            PlotCanvas.Children.Add(polyLine);

            // Bounding Box Axes
            var box = new Rectangle
            {
                Width = plotW,
                Height = plotH,
                Stroke = new SolidColorBrush(Color.FromArgb(100, 71, 85, 105)),
                StrokeThickness = 1
            };
            Canvas.SetLeft(box, padLeft);
            Canvas.SetTop(box, padTop);
            PlotCanvas.Children.Add(box);
        }

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

            // Find closest sampled point
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
            var dlg = new SaveFileDialog
            {
                Title = "Export Elevation Profile CSV",
                Filter = "CSV Files (*.csv)|*.csv",
                FileName = $"{System.IO.Path.GetFileNameWithoutExtension(_layerName)}_elevation_profile.csv"
            };

            if (dlg.ShowDialog() == true)
            {
                using var sw = new StreamWriter(dlg.FileName);
                sw.WriteLine("Station_Distance_m,Elevation_m");
                for (int i = 0; i < _distances.Length; i++)
                {
                    sw.WriteLine($"{_distances[i]:F3},{_elevations[i]:F3}");
                }
                MessageBox.Show($"Elevation transect exported to CSV ({_distances.Length} points).", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
