using System.Windows;
using System.Windows.Controls;
using GeoStudio.UI.Dialogs;

namespace GeoStudio
{
    public partial class MainWindow
    {
        #region Vector Digitizing Tools
        private bool _isEditingActive = false;

        internal void BtnToggleEdit_Click(object sender, RoutedEventArgs e)
        {
            _isEditingActive = !_isEditingActive;
            PostMessageToMap(new { action = "toggleEditing", active = _isEditingActive });
            TxtStatus.Text = _isEditingActive
                ? "✏️ Editing Mode ON: Vertex Tool active & snapping enabled"
                : "Editing Mode OFF: Standard navigation mode active";
        }

        internal void BtnDigitizePoint_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "digitize_point" });
            TxtStatus.Text = "Digitize Point: Click on map to place points";
        }

        internal void BtnDigitizeLine_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "digitize_line" });
            TxtStatus.Text = "Digitize Line: Click on map to add vertices, double click to finish line";
        }

        internal void BtnDigitizePolygon_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "digitize_polygon" });
            TxtStatus.Text = "Digitize Polygon: Click to draw polygon boundary, double click to close";
        }

        internal void BtnSplitGeometry_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "split" });
            TxtStatus.Text = "Split Tool: Draw a cutting line across any feature to split it, double-click to finish";
        }

        internal void BtnDeleteFeature_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "deleteSelectedFeature" });
            TxtStatus.Text = "Deleted selected feature";
        }

        internal void BtnVertexTool_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "vertex_tool" });
            TxtStatus.Text = "Vertex Tool active: Click and drag vertices to reshape; click edge to insert vertex; Alt+click to delete vertex";
        }

        internal void BtnUndoVertex_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "undoVertex" });
            TxtStatus.Text = "Undid last vertex / feature";
        }

        internal void BtnClearDigitized_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "clearDigitized" });
            TxtStatus.Text = "Cleared all digitized geometries";
        }

        internal void ComboSnapping_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isInitialized || TxtStatus == null) return;
            if (ComboSnapping.SelectedItem is ComboBoxItem item)
            {
                string text = item.Content?.ToString() ?? "";
                int tolerance = 10;
                if (text.Contains("Disabled", System.StringComparison.OrdinalIgnoreCase)) tolerance = 0;
                else if (text.Contains("5")) tolerance = 5;
                else if (text.Contains("10")) tolerance = 10;
                else if (text.Contains("20")) tolerance = 20;

                TxtStatus.Text = $"Snapping tolerance: {text}";
                PostMessageToMap(new { action = "setSnappingTolerance", tolerance = tolerance });
            }
        }
        #endregion

        #region Vector Spatial Algorithms
        internal void MenuBuffer_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new GeoprocessingWindow(this, "buffer");
            dlg.ShowDialog();
        }

        internal void MenuConvexHull_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new GeoprocessingWindow(this, "convex_hull");
            dlg.ShowDialog();
        }

        internal void MenuCentroids_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new GeoprocessingWindow(this, "centroids");
            dlg.ShowDialog();
        }

        internal void MenuVoronoi_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new GeoprocessingWindow(this, "voronoi");
            dlg.ShowDialog();
        }

        internal void MenuDissolve_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new GeoprocessingWindow(this, "dissolve");
            dlg.ShowDialog();
        }

        internal void MenuClipVector_Click(object sender, RoutedEventArgs e)
        {
            if (ActiveClipVectorWindow != null && ActiveClipVectorWindow.IsLoaded)
            {
                ActiveClipVectorWindow.SetMode("clip");
                ActiveClipVectorWindow.Activate();
                return;
            }

            var dlg = new GeoprocessingWindow(this, "clip");
            ActiveClipVectorWindow = dlg;
            dlg.Show();
        }
        #endregion
    }
}
