using System;
using System.Diagnostics;
using System.IO;
using System.Windows;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.Raster;

namespace GeoStudio
{
    public partial class MainWindow
    {
        internal async void BtnAddRaster_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Open 100GB+ BigTIFF, GeoTIFF or DEM Raster",
                Filter = "GeoTIFF & BigTIFF (*.tif;*.tiff;*.dem;*.asc;*.vrt)|*.tif;*.tiff;*.dem;*.asc;*.vrt|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                try
                {
                    string selectedFile = dlg.FileName;
                    var sw = Stopwatch.StartNew();
                    if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Visible;
                    if (TxtBenchmarkFileName != null) TxtBenchmarkFileName.Text = Path.GetFileName(selectedFile);
                    if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = "Loading...";
                    if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = "Reading GDAL metadata & streaming viewport...";
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
                    if (TxtBenchmarkStatusIcon != null) TxtBenchmarkStatusIcon.Text = "⏳";
                    if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Streaming to GPU Canvas...";

                    TxtStatus.Text = $"Opening BigTIFF via GDAL: {Path.GetFileName(selectedFile)}...";

                    var meta = await System.Threading.Tasks.Task.Run(() => GdalRasterService.InspectMetadata(selectedFile));

                    long fileLoadMs = sw.ElapsedMilliseconds;
                    _activeRasterFilePath = selectedFile;

                    long fileLen = new FileInfo(selectedFile).Length;
                    string displaySize = fileLen >= 1024L * 1024 * 1024
                        ? $"{fileLen / (1024.0 * 1024 * 1024):F2} GB"
                        : $"{fileLen / (1024.0 * 1024):F1} MB";

                    string details = meta.IsElevation
                        ? $"DEM/DSM | {meta.Width:N0}x{meta.Height:N0} px | Elev: {meta.MinElevation:F1}m - {meta.MaxElevation:F1}m | {displaySize} | {meta.Projection}"
                        : $"GDAL BigTIFF | {meta.Width:N0}x{meta.Height:N0} px | {displaySize} | {meta.Projection}";

                    _activeRasterShaderMode = meta.IsElevation ? "atlas" : null;
                    _activeRasterPalette = meta.IsElevation ? "GLOBAL_MAPPER_ATLAS" : null;

                    var layer = new LayerItem
                    {
                        Id = Guid.NewGuid().ToString(),
                        Name = Path.GetFileName(selectedFile),
                        Type = LayerType.Raster,
                        FilePath = selectedFile,
                        FileSizeBytes = fileLen,
                        BoundingBox = meta.BoundingBox,
                        Details = details,
                        ColorHex = meta.IsElevation ? "#10B981" : "#D97706",
                        IsElevation = meta.IsElevation,
                        MinElevation = meta.MinElevation,
                        MaxElevation = meta.MaxElevation,
                        ShaderMode = _activeRasterShaderMode,
                        Palette = _activeRasterPalette
                    };
                    _activeRasterLayerId = layer.Id;
                    Layers.Add(layer);
                    UpdateLayerCount();

                    PostMessageToMap(new
                    {
                        action = "addRasterLayer",
                        id = layer.Id,
                        name = layer.Name,
                        filePath = selectedFile,
                        bounds = meta.BoundingBox,
                        width = meta.Width,
                        height = meta.Height,
                        imageUri = meta.PreviewUrl,
                        imageUrl = meta.PreviewUrl,
                        details = layer.Details,
                        fileLoadMs = fileLoadMs,
                        shaderMode = layer.ShaderMode,
                        palette = layer.Palette,
                        minElev = meta.MinElevation,
                        maxElev = meta.MaxElevation,
                        isElevation = meta.IsElevation
                    });

                    if (string.IsNullOrEmpty(meta.PreviewUrl))
                    {
                        TxtStatus.Text = meta.IsElevation
                            ? $"Loaded {layer.Name} ({meta.Width:N0}x{meta.Height:N0} px) • Generating Global Mapper 3D Shaded Relief in background..."
                            : $"Loaded {layer.Name} ({meta.Width:N0}x{meta.Height:N0} px) • Generating overview in background...";
                        if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
                    }
                    else
                    {
                        TxtStatus.Text = meta.IsElevation
                            ? $"Rendered: {layer.Name} (3D Shaded Relief | {meta.MinElevation:F1}m - {meta.MaxElevation:F1}m | {layer.DisplaySize})"
                            : $"Rendered: {layer.Name} ({meta.Width:N0}x{meta.Height:N0} px | {layer.DisplaySize})";
                    }
                    TxtCrs.Text = "CRS: " + meta.Projection;
                }
                catch (Exception ex)
                {
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                    TxtStatus.Text = $"GDAL reader warning: {ex.Message}";
                }
            }
        }
    }
}
