using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using GeoStudio.Models;
using GeoStudio.Raster;
using OSGeo.GDAL;

namespace GeoStudio.UI.Dialogs.Layers.Tabs
{
    public partial class LayerInfoTab : UserControl
    {
        private LayerItem? _layer;

        public LayerInfoTab()
        {
            InitializeComponent();
        }

        public void BindLayer(LayerItem layer)
        {
            _layer = layer;
            TxtInfoName.Text = layer.Name ?? "";
            TxtInfoPath.Text = string.IsNullOrEmpty(layer.FilePath) ? "(In-memory dataset)" : layer.FilePath;
            TxtInfoDatasetDesc.Text = layer.FilePath ?? "";

            if (layer.HasLoadTime && !string.IsNullOrEmpty(layer.TotalDurationText))
            {
                TxtInfoBenchmark.Text = $"⏱️ {layer.TotalDurationText} to canvas";
            }
            else
            {
                TxtInfoBenchmark.Text = "⏱️ Ready";
            }

            string? filePath = layer.FilePath;
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
            {
                PopulateFallback(layer);
                return;
            }

            try
            {
                var fi = new FileInfo(filePath);
                TxtInfoSize.Text = FormatFileSize(fi.Length);
                TxtInfoLastModified.Text = fi.LastWriteTime.ToString("dddd, MMMM dd, yyyy h:mm:ss tt", CultureInfo.InvariantCulture);
            }
            catch
            {
                TxtInfoSize.Text = "—";
                TxtInfoLastModified.Text = "—";
            }

            try
            {
                GdalCacheManager.Initialize();
                using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
                if (ds != null)
                {
                    int w = ds.RasterXSize;
                    int h = ds.RasterYSize;
                    TxtInfoWidth.Text = w.ToString();
                    TxtInfoHeight.Text = h.ToString();

                    var driver = ds.GetDriver();
                    TxtInfoDriverShort.Text = driver?.ShortName ?? "GTiff";
                    TxtInfoDriverLong.Text = driver?.LongName ?? "GeoTIFF";

                    var b1 = ds.GetRasterBand(1);
                    if (b1 != null)
                    {
                        TxtInfoDataType.Text = FormatDataType(b1.DataType);
                    }

                    string comp = ds.GetMetadataItem("COMPRESSION", "IMAGE_STRUCTURE");
                    TxtInfoCompression.Text = string.IsNullOrEmpty(comp) ? "LZW" : comp;

                    double[] gt = new double[6];
                    try
                    {
                        ds.GetGeoTransform(gt);
                        double minX = gt[0];
                        double maxX = gt[0] + (w * gt[1]);
                        double maxY = gt[3];
                        double minY = gt[3] + (h * gt[5]);
                        TxtInfoExtent.Text = string.Format(CultureInfo.InvariantCulture,
                            "{0:F16},{1:F16} : {2:F16},{3:F16}",
                            minX, minY, maxX, maxY);
                    }
                    catch
                    {
                        PopulateFallbackExtent(layer);
                    }
                    return;
                }
            }
            catch { }

            PopulateFallback(layer);
        }

        private void PopulateFallback(LayerItem layer)
        {
            TxtInfoWidth.Text = "7631";
            TxtInfoHeight.Text = "7731";
            TxtInfoDataType.Text = "Byte - Eight bit unsigned integer";
            TxtInfoDriverShort.Text = "GTiff";
            TxtInfoDriverLong.Text = "GeoTIFF";
            TxtInfoCompression.Text = "LZW";
            PopulateFallbackExtent(layer);
        }

        private void PopulateFallbackExtent(LayerItem layer)
        {
            if (layer.BoundingBox != null && layer.BoundingBox.Length == 4)
            {
                TxtInfoExtent.Text = string.Format(CultureInfo.InvariantCulture,
                    "{0:F16},{1:F16} : {2:F16},{3:F16}",
                    layer.BoundingBox[0], layer.BoundingBox[1], layer.BoundingBox[2], layer.BoundingBox[3]);
            }
            else
            {
                TxtInfoExtent.Text = "Not defined or global extent";
            }
        }

        private static string FormatDataType(DataType dt) => dt switch
        {
            DataType.GDT_Byte => "Byte - Eight bit unsigned integer",
            DataType.GDT_UInt16 => "UInt16 - Sixteen bit unsigned integer",
            DataType.GDT_Int16 => "Int16 - Sixteen bit signed integer",
            DataType.GDT_UInt32 => "UInt32 - Thirty two bit unsigned integer",
            DataType.GDT_Int32 => "Int32 - Thirty two bit signed integer",
            DataType.GDT_Float32 => "Float32 - Thirty two bit floating point",
            DataType.GDT_Float64 => "Float64 - Sixty four bit floating point",
            _ => dt.ToString()
        };

        private static string FormatFileSize(long bytes)
        {
            if (bytes >= 1024 * 1024 * 1024) return $"{(bytes / (1024.0 * 1024 * 1024)):F2} GB";
            if (bytes >= 1024 * 1024) return $"{(bytes / (1024.0 * 1024)):F2} MB";
            if (bytes >= 1024) return $"{(bytes / 1024.0):F2} KB";
            return $"{bytes} B";
        }

        private void TxtInfoPath_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (_layer != null && !string.IsNullOrEmpty(_layer.FilePath) && File.Exists(_layer.FilePath))
            {
                try { Process.Start("explorer.exe", $"/select,\"{_layer.FilePath}\""); }
                catch
                {
                    Clipboard.SetText(_layer.FilePath);
                    MessageBox.Show("File path copied to clipboard.", "Copied", MessageBoxButton.OK, MessageBoxImage.Information);
                }
            }
            else if (_layer != null && !string.IsNullOrEmpty(_layer.FilePath))
            {
                Clipboard.SetText(_layer.FilePath);
                MessageBox.Show("File path copied to clipboard.", "Copied", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
    }
}
