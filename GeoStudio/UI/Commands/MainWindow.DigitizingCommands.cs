using System.Windows;
using System.Windows.Controls;

namespace GeoStudio
{
    public partial class MainWindow
    {
        #region Vector Digitizing Tools
        private void BtnToggleEdit_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Digitizing Mode toggled (Snapping enabled)";

        private void BtnDigitizePoint_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "digitize_point" });
            TxtStatus.Text = "Digitize Point: Click on map to place points";
        }

        private void BtnDigitizeLine_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "digitize_line" });
            TxtStatus.Text = "Digitize Line: Click on map to add vertices, double click to finish line";
        }

        private void BtnDigitizePolygon_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "digitize_polygon" });
            TxtStatus.Text = "Digitize Polygon: Click to draw polygon boundary, double click to close";
        }

        private void BtnSplitGeometry_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Split Geometry tool active";

        private void BtnDeleteFeature_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "clearDigitized" });
            TxtStatus.Text = "Deleted digitized features";
        }

        private void BtnVertexTool_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Vertex Move / Edit Tool active";

        private void BtnUndoVertex_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Last vertex undone";

        private void BtnClearDigitized_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "clearDigitized" });
            TxtStatus.Text = "Cleared all digitized geometries";
        }

        private void ComboSnapping_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isInitialized || TxtStatus == null) return;
            if (ComboSnapping.SelectedItem is ComboBoxItem item)
            {
                TxtStatus.Text = $"Snapping mode: {item.Content}";
            }
        }
        #endregion

        #region Vector Spatial Algorithms
        private void MenuBuffer_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Geodesic Buffer Tool: Creates a 250m buffer around selected vector geometries.", "Vector Processing", MessageBoxButton.OK, MessageBoxImage.Information);

        private void MenuConvexHull_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Convex Hull: Computes the minimum convex enclosing polygon.", "Vector Processing", MessageBoxButton.OK, MessageBoxImage.Information);

        private void MenuCentroids_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Vector Centroids: Calculates the geometric center point for each polygon feature.", "Centroids", MessageBoxButton.OK, MessageBoxImage.Information);

        private void MenuVoronoi_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Voronoi Polygons: Constructs Thiessen polygon partition from point dataset.", "Voronoi", MessageBoxButton.OK, MessageBoxImage.Information);

        private void MenuDissolve_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Dissolve Boundaries: Merges contiguous vector polygons sharing identical attributes.", "Dissolve", MessageBoxButton.OK, MessageBoxImage.Information);

        private void MenuClipVector_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Clip Vector by Mask: Extracts vector geometries falling within boundary polygon.", "Clip Vector", MessageBoxButton.OK, MessageBoxImage.Information);
        #endregion
    }
}
