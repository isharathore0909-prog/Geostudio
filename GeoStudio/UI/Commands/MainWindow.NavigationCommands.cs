using System.Windows;

namespace GeoStudio
{
    public partial class MainWindow
    {
        #region Map Navigation Commands
        private void BtnPan_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "pan" });
            TxtStatus.Text = "Pan tool active (Drag map to navigate)";
        }

        private void BtnZoomIn_Click(object sender, RoutedEventArgs e) => PostMessageToMap(new { action = "zoomIn" });
        
        private void BtnZoomOut_Click(object sender, RoutedEventArgs e) => PostMessageToMap(new { action = "zoomOut" });
        
        private void BtnZoomFull_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "zoomFull" });
            TxtStatus.Text = "Zoomed to full layer extent";
        }

        private void BtnRefresh_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "refresh" });
            TxtStatus.Text = "Map display refreshed";
        }

        private void BtnSplit_Click(object sender, RoutedEventArgs e)
        {
            var rasterLayers = System.Linq.Enumerable.ToList(System.Linq.Enumerable.Where(Layers, l => l.Type == Models.LayerType.Raster));
            if (rasterLayers.Count < 2)
            {
                TxtStatus.Text = "Swipe & Compare requires at least 2 raster layers loaded (e.g. DTM and DSM).";
                MessageBox.Show("Please load at least two raster layers (such as a DTM and DSM surface) to use the interactive Swipe & Compare tool.", "Swipe & Compare", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            PostMessageToMap(new { action = "toggleSwipe" });
            TxtStatus.Text = "Interactive Swipe & Compare View toggled. Drag vertical curtain divider to compare surfaces.";
        }

        private void BtnOverview_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Overview inset map toggled";
        #endregion

        #region Feature Selection Tools
        private void BtnIdentify_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select" });
            TxtStatus.Text = "Identify Tool: Click on any feature to view attributes";
        }

        private void BtnSelectPointer_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select" });
            TxtStatus.Text = "Single feature selection mode";
        }

        private void BtnSelectBox_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select" });
            TxtStatus.Text = "Rectangle Box Selection mode";
        }

        private void BtnSelectPolygon_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select" });
            TxtStatus.Text = "Polygon Selection mode";
        }

        private void BtnSelectRadius_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select" });
            TxtStatus.Text = "Radius / Lasso Selection mode";
        }

        private void BtnClearSelection_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Selection cleared";
        #endregion

        #region Measurement Tools
        private void BtnMeasureDistance_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "measure_distance" });
            TxtStatus.Text = "Measure Distance Tool: Click on map to add points, double click to finish";
        }

        private void BtnMeasureArea_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "measure_area" });
            TxtStatus.Text = "Measure Area Tool: Click to draw polygon area, double click to finish";
        }

        private void BtnMeasureAngle_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Angle Measurement: Click vertex and reference arm to calculate azimuth & bearing.", "Measurement", MessageBoxButton.OK, MessageBoxImage.Information);
        #endregion
    }
}
