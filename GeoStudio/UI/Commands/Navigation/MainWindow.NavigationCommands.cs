using System;
using System.Collections.Generic;
using System.Windows;
using GeoStudio.UI.Dialogs;

namespace GeoStudio
{
    public partial class MainWindow
    {
        #region Extent History State
        private readonly Stack<(double lon, double lat, double zoom)> _undoExtents = new();
        private readonly Stack<(double lon, double lat, double zoom)> _redoExtents = new();
        private (double lon, double lat, double zoom)? _currentExtent = (76.515, 24.762, 5.0);
        private bool _isNavigatingHistory = false;

        internal void RecordViewportExtent(double lon, double lat, double zoom)
        {
            if (!_isNavigatingHistory)
            {
                if (_currentExtent.HasValue)
                {
                    var cur = _currentExtent.Value;
                    if (Math.Abs(cur.lon - lon) > 0.005 || Math.Abs(cur.lat - lat) > 0.005 || Math.Abs(cur.zoom - zoom) > 0.25)
                    {
                        _undoExtents.Push(cur);
                        _redoExtents.Clear();
                    }
                }
            }
            _currentExtent = (lon, lat, zoom);
            _isNavigatingHistory = false;
        }

        internal void BtnPreviousExtent_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "previousExtent" });
        }

        internal void BtnNextExtent_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "nextExtent" });
        }
        #endregion

        #region Map Navigation Commands
        internal void BtnPan_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "pan" });
            TxtStatus.Text = "Pan tool active (Drag map to navigate)";
        }

        internal void BtnBookmarks_Click(object sender, RoutedEventArgs e)
        {
            var win = new BookmarksWindow(_currentExtent, (lon, lat, zoom) =>
            {
                PostMessageToMap(new { action = "setCenterZoom", lon = lon, lat = lat, zoom = zoom });
                TxtStatus.Text = $"Jumped to bookmark location (Zoom {zoom:F1}x)";
            });
            win.Owner = this;
            win.ShowDialog();
        }

        internal void BtnZoomIn_Click(object sender, RoutedEventArgs e) => PostMessageToMap(new { action = "zoomIn" });
        
        internal void BtnZoomOut_Click(object sender, RoutedEventArgs e) => PostMessageToMap(new { action = "zoomOut" });
        
        internal void BtnZoomFull_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "zoomFull" });
            TxtStatus.Text = "Zoomed to full layer extent";
        }

        internal void BtnGoToXy_Click(object sender, RoutedEventArgs e)
        {
            var win = new GoToXyWindow((lon, lat, zoom, label) =>
            {
                PostMessageToMap(new { action = "goToCoord", lon = lon, lat = lat, zoom = zoom, label = label });
                TxtStatus.Text = $"Jumped to coordinates: Lat {lat:F5}°, Lon {lon:F5}° (Zoom {zoom:F1}x)";
            });
            win.Owner = this;
            win.ShowDialog();
        }

        internal void BtnFindPlace_Click(object sender, RoutedEventArgs e)
        {
            var win = new FindPlaceWindow((lon, lat, zoom, name) =>
            {
                PostMessageToMap(new { action = "goToCoord", lon = lon, lat = lat, zoom = zoom, label = name });
                TxtStatus.Text = $"Jumped to place: {name} (Lat {lat:F4}°, Lon {lon:F4}°)";
            });
            win.Owner = this;
            win.ShowDialog();
        }

        internal void BtnRefresh_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "refresh" });
            TxtStatus.Text = "Map display refreshed";
        }

        internal void BtnSplit_Click(object sender, RoutedEventArgs e)
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

        internal void BtnOverview_Click(object sender, RoutedEventArgs e) =>
            TxtStatus.Text = "Overview inset map toggled";

        internal void ApplyLayerBlendMode(string modeName)
        {
            PostMessageToMap(new { action = "setBlendMode", mode = modeName });
            TxtStatus.Text = $"Layer Blend Mode: {modeName}";
        }

        internal void BtnTranspose_Click(object sender, RoutedEventArgs e)
        {
            var vectorLayers = System.Linq.Enumerable.ToList(System.Linq.Enumerable.Where(Layers, l => l.Type == Models.LayerType.Vector));
            var activeVector = System.Linq.Enumerable.FirstOrDefault(vectorLayers);

            var win = new GeoStudio.UI.Dialogs.TransposeFieldsWindow(vectorLayers, activeVector, (transposedPath) =>
            {
                if (!string.IsNullOrEmpty(transposedPath) && System.IO.File.Exists(transposedPath))
                {
                    LoadVectorFile(transposedPath);
                    TxtStatus.Text = $"Loaded transposed dataset: {System.IO.Path.GetFileName(transposedPath)}";
                }
            });
            win.Owner = this;
            win.ShowDialog();
        }
        #endregion

        #region Feature Selection Tools
        internal void BtnIdentify_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "identify" });
            TxtStatus.Text = "Identify Tool active: Click on any feature or map area to inspect properties";
        }

        internal void BtnSelectPointer_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select" });
            TxtStatus.Text = "Feature Selection active: Click a feature to select";
        }

        internal void BtnSelectBox_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "zoom_box" });
            TxtStatus.Text = "Zoom Box mode active: Drag a rectangle to zoom into that region";
        }

        internal void BtnSelectPolygon_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "select_polygon" });
            TxtStatus.Text = "Polygon Selection mode: Click to draw bounding polygon, double-click to finish";
        }

        internal void BtnSelectByAttributes_Click(object sender, RoutedEventArgs e)
        {
            var vectorLayers = System.Linq.Enumerable.ToList(System.Linq.Enumerable.Where(Layers, l => l.Type == Models.LayerType.Vector));
            var activeLayer = System.Linq.Enumerable.FirstOrDefault(vectorLayers, l => l.IsVisible);

            var win = new SelectByAttributesWindow(vectorLayers, activeLayer, (layerId, field, op, val) =>
            {
                PostMessageToMap(new { action = "selectByAttribute", layerId = layerId, key = field, op = op, value = val });
                TxtStatus.Text = $"Querying features where {field} {op} '{val}'...";
            });
            win.Owner = this;
            win.ShowDialog();
        }

        internal void BtnClearSelection_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "clearSelection" });
            TxtStatus.Text = "Selection cleared";
        }

        internal void BtnZoomToSelection_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "zoomToSelected" });
            TxtStatus.Text = "Zoomed to selected feature(s)";
        }

        internal void BtnOpenAttributeTable_Click(object sender, RoutedEventArgs e)
        {
            var vectorLayers = System.Linq.Enumerable.ToList(System.Linq.Enumerable.Where(Layers, l => l.Type == Models.LayerType.Vector));
            var activeLayer = System.Linq.Enumerable.FirstOrDefault(vectorLayers, l => l.IsVisible) ?? System.Linq.Enumerable.FirstOrDefault(vectorLayers);

            var win = new AttributeTableWindow(vectorLayers, activeLayer, (id) =>
            {
                PostMessageToMap(new { action = "zoomToSelected" });
            });
            win.Owner = this;
            win.Show();
            TxtStatus.Text = activeLayer != null 
                ? $"Attribute Table opened for {activeLayer.Name} ({(activeLayer.FeatureCount > 0 ? $"{activeLayer.FeatureCount:N0} records" : "vector")})" 
                : "Attribute Table opened";
        }
        #endregion

        #region Measurement & Inspection Tools
        internal void BtnMeasureDistance_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "measure_distance" });
            TxtStatus.Text = "Measure Distance Tool: Click on map to add points, double click to finish";
        }

        internal void BtnMeasureArea_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "measure_area" });
            TxtStatus.Text = "Measure Area Tool: Click to draw polygon area, double click to finish";
        }

        internal void BtnMeasureAngle_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Angle Measurement: Click vertex and reference arm to calculate azimuth & bearing.", "Measurement", MessageBoxButton.OK, MessageBoxImage.Information);

        internal void BtnLocate_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "locate" });
            TxtStatus.Text = "Locate Tool active: Click on map to drop pinpoint marker and copy coordinates";
        }

        internal void BtnZoomBox_Click(object sender, RoutedEventArgs e)
        {
            PostMessageToMap(new { action = "setTool", tool = "zoom_box" });
            TxtStatus.Text = "Zoom Box active: Drag a rectangle to zoom in";
        }
        #endregion

        #region Panels & Workspace Commands
        internal void BtnToggleSidebar_Click(object sender, RoutedEventArgs e)
        {
            if (SidebarControl != null)
            {
                if (SidebarControl.Visibility == Visibility.Visible)
                {
                    SidebarControl.Visibility = Visibility.Collapsed;
                    if (FindName("SidebarColumn") is System.Windows.Controls.ColumnDefinition col)
                    {
                        col.Width = new GridLength(0);
                    }
                    TxtStatus.Text = "Browser and Layers panel collapsed";
                }
                else
                {
                    SidebarControl.Visibility = Visibility.Visible;
                    if (FindName("SidebarColumn") is System.Windows.Controls.ColumnDefinition col)
                    {
                        col.Width = new GridLength(280);
                    }
                    TxtStatus.Text = "Browser and Layers panel opened";
                }
            }
        }
        #endregion
    }
}
