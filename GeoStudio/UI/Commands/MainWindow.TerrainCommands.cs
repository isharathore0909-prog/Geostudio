using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Python;
using GeoStudio.DuckDB;
using GeoStudio.Raster;
using GeoStudio.Models;
using GeoStudio.UI;

namespace GeoStudio
{
    public partial class MainWindow
    {
        #region Terrain & Elevation Shader Handlers

        private async void ApplyActiveShader(string shaderMode, string? paletteName = null)
        {
            var activeLayer = Layers.LastOrDefault(l => l.Type == LayerType.Raster);
            if (activeLayer == null || string.IsNullOrEmpty(activeLayer.FilePath) || !File.Exists(activeLayer.FilePath))
            {
                TxtStatus.Text = "Please load a DEM / Elevation raster layer first.";
                return;
            }

            if (string.IsNullOrEmpty(paletteName))
            {
                string atlasText = (ComboAtlas.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "Atlas";
                if (atlasText.Contains("Terrain")) paletteName = "TERRAIN";
                else if (atlasText.Contains("Magma")) paletteName = "MAGMA";
                else if (atlasText.Contains("Viridis")) paletteName = "VIRIDIS";
                else paletteName = "GLOBAL_MAPPER_ATLAS";
            }

            string filePath = activeLayer.FilePath;
            _activeRasterFilePath = filePath;
            _activeRasterLayerId = activeLayer.Id;
            _activeRasterShaderMode = shaderMode;
            _activeRasterPalette = paletteName;
            activeLayer.ShaderMode = shaderMode;
            activeLayer.Palette = paletteName;
            activeLayer.IsElevation = true;

            TxtStatus.Text = $"Computing {shaderMode.ToUpperInvariant()} shader for {activeLayer.Name}...";
            if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;

            var sw = Stopwatch.StartNew();
            try
            {
                var meta = await Task.Run(() => GdalRasterService.ApplyTerrainShader(filePath, shaderMode, paletteName));
                long calcMs = sw.ElapsedMilliseconds;

                if (!string.IsNullOrEmpty(meta.PreviewUrl))
                {
                    if (meta.MinElevation != 0 || meta.MaxElevation != 0)
                    {
                        activeLayer.MinElevation = meta.MinElevation;
                        activeLayer.MaxElevation = meta.MaxElevation;
                    }

                    PostMessageToMap(new
                    {
                        action = "updateRasterOverview",
                        id = activeLayer.Id,
                        name = activeLayer.Name,
                        bounds = meta.BoundingBox,
                        imageUrl = meta.PreviewUrl,
                        shaderMode = shaderMode,
                        palette = paletteName,
                        minElev = activeLayer.MinElevation,
                        maxElev = activeLayer.MaxElevation,
                        isElevation = true
                    });
                    TxtStatus.Text = $"Applied {shaderMode.ToUpperInvariant()} to {activeLayer.Name} in {calcMs}ms • Real-time elevation engine ready";
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Terrain shader error: {ex.Message}";
            }
            finally
            {
                if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
            }
        }

        private void ComboShader_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isInitialized || TxtStatus == null || ComboShader.SelectedItem == null) return;
            string text = (ComboShader.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "";
            if (text.Contains("Shader ▾")) return;

            string mode = "atlas";
            if (text.Contains("Atlas")) mode = "atlas";
            else if (text.Contains("Elevation")) mode = "terrain";
            else if (text.Contains("Slope")) mode = "slope";
            else if (text.Contains("Aspect")) mode = "aspect";
            else if (text.Contains("Hillshade")) mode = "hillshade";
            else if (text.Contains("TRI")) mode = "tri";
            else if (text.Contains("TPI")) mode = "tpi";
            else if (text.Contains("TWI")) mode = "twi";
            else if (text.Contains("Curvature")) mode = "curvature";

            ApplyActiveShader(mode);
        }

        private void ComboAtlas_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (!_isInitialized || TxtStatus == null || ComboAtlas.SelectedItem == null) return;
            string text = (ComboAtlas.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "";
            if (text.Contains("Atlas ▾")) return;

            string palette = "GLOBAL_MAPPER_ATLAS";
            if (text.Contains("Terrain")) palette = "TERRAIN";
            else if (text.Contains("Magma")) palette = "MAGMA";
            else if (text.Contains("Viridis")) palette = "VIRIDIS";

            ApplyActiveShader("atlas", palette);
        }

        private void MenuElevation_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("atlas", "GLOBAL_MAPPER_ATLAS");

        private void MenuHillshade_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("hillshade");

        private void MenuSlope_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("slope");

        private void MenuAspect_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("aspect");

        private void MenuTri_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("tri");

        private void MenuTpi_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("tpi");

        private void MenuTwi_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("twi");

        private void MenuCurvature_Click(object sender, RoutedEventArgs e) =>
            ApplyActiveShader("curvature");

        private void MenuProfile_Click(object sender, RoutedEventArgs e)
        {
            var activeRaster = Layers.LastOrDefault(l => l.Type == LayerType.Raster);
            if (activeRaster == null || string.IsNullOrEmpty(activeRaster.FilePath) || !File.Exists(activeRaster.FilePath))
            {
                MessageBox.Show("Please load a DEM / Elevation raster layer first.", "Elevation Profile", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            PostMessageToMap(new { action = "clearProfileLine" });
            PostMessageToMap(new { action = "setTool", tool = "elevation_profile" });
            TxtStatus.Text = $"Elevation Profile tool active: Click two points across {activeRaster.Name} on map canvas to extract cross-section transect.";
        }

        private void MenuContour_Click(object sender, RoutedEventArgs e)
        {
            var rasterLayers = Layers.Where(l => l.Type == LayerType.Raster && !string.IsNullOrEmpty(l.FilePath) && File.Exists(l.FilePath)).ToList();
            if (rasterLayers.Count == 0)
            {
                MessageBox.Show("Please load a DEM / Elevation raster layer first.", "Contour Generator", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var activeRaster = (_activeRasterLayerId != null ? FindLayer(_activeRasterLayerId) : null)
                ?? rasterLayers.LastOrDefault();

            var win = new ContourWindow(rasterLayers, activeRaster, (contourFilePath, colorHex, zoomTo, interval) =>
            {
                LoadVectorFile(contourFilePath, customColor: colorHex, isContour: true, zoomTo: zoomTo, contourInterval: interval);
                TxtStatus.Text = $"Contours generated and rendered on canvas: {Path.GetFileName(contourFilePath)}";
            });
            win.Owner = this;
            win.ShowDialog();
        }

        private void MenuCutFill_Click(object sender, RoutedEventArgs e)
        {
            var rasterLayers = Layers.Where(l => l.Type == LayerType.Raster).ToList();
            if (rasterLayers.Count == 0)
            {
                MessageBox.Show("Please load at least one DEM elevation raster surface (e.g. DTM or DSM) to compute Cut & Fill earthwork volumes.", "Cut & Fill Volume", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var win = new CutFillWindow(rasterLayers);
            win.Owner = this;
            win.ShowDialog();
        }

        private void MenuWatershed_Click(object sender, RoutedEventArgs e) =>
            MessageBox.Show("Watershed Drainage Basin Analysis: Computes flow direction, flow accumulation, and hydrologic pour points.", "Watershed Analysis", MessageBoxButton.OK, MessageBoxImage.Information);

        private void Btn3dMesh_Click(object sender, RoutedEventArgs e)
        {
            TxtStatus.Text = "Launching interactive 3D Point Cloud / Terrain Workstation...";
            string? targetFile = Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud)?.FilePath ?? _activeRasterFilePath;
            PythonPipelineService.Launch3DViewer(targetFile);
        }
        #endregion
    }
}
