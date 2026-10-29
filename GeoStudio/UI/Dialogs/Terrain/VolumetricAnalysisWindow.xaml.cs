using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.UI.Services;
using OSGeo.GDAL;

namespace GeoStudio.UI.Dialogs.Terrain
{
    public class StageStorageRow
    {
        public int StageIndex { get; set; }
        public double Elevation { get; set; }
        public double StageHeight { get; set; }
        public double AreaM2 { get; set; }
        public double AreaHa => AreaM2 / 10000.0;
        public double VolumeBelow { get; set; }
        public double CumulativeCapacity => VolumeBelow;
        public double MegaLiters => CumulativeCapacity / 1000.0;

        public string ElevationText => $"{Elevation:N2}";
        public string StageHeightText => $"{StageHeight:N2}";
        public string AreaM2Text => $"{AreaM2:N0}";
        public string AreaHaText => $"{AreaHa:N2}";
        public string VolumeBelowText => $"{VolumeBelow:N0}";
        public string CumulativeCapacityText => $"{CumulativeCapacity:N0}";
        public string MegaLitersText => $"{MegaLiters:N2}";
    }

    public partial class VolumetricAnalysisWindow : Window
    {
        private readonly List<LayerItem> _rasterLayers;
        private readonly ObservableCollection<StageStorageRow> _storageRows = new();
        private double _demMin = 0;
        private double _demMax = 0;
        private double _demMean = 0;

        public VolumetricAnalysisWindow(IEnumerable<LayerItem> layers)
        {
            InitializeComponent();
            GridStageStorage.ItemsSource = _storageRows;

            _rasterLayers = layers.Where(l => (l.Type == LayerType.Raster || l.Type == LayerType.Elevation) &&
                                              !string.IsNullOrEmpty(l.FilePath) && File.Exists(l.FilePath)).ToList();

            foreach (var r in _rasterLayers)
            {
                ComboDemSurface.Items.Add(r.Name);
            }

            if (ComboDemSurface.Items.Count > 0)
            {
                ComboDemSurface.SelectedIndex = 0;
            }
            else
            {
                TxtStatus.Text = "No valid elevation DEM raster layers loaded.";
            }
        }

        private async void ComboDemSurface_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboDemSurface.SelectedIndex < 0 || ComboDemSurface.SelectedIndex >= _rasterLayers.Count) return;
            var layer = _rasterLayers[ComboDemSurface.SelectedIndex];

            TxtStatus.Text = $"Inspecting elevation profile for {layer.Name}...";
            try
            {
                var (minZ, maxZ, meanZ) = await Task.Run(() => SampleQuickElevationStats(layer.FilePath));
                _demMin = minZ;
                _demMax = maxZ;
                _demMean = meanZ;

                if (ComboDatumMode.SelectedIndex == 0) // Mean
                {
                    TxtCustomDatum.Text = $"{meanZ:F2}";
                }
                else if (ComboDatumMode.SelectedIndex == 1) // Min
                {
                    TxtCustomDatum.Text = $"{minZ:F2}";
                }

                TxtStatus.Text = $"Ready to calculate volumetrics for {layer.Name}. Range: {minZ:F1}m to {maxZ:F1}m.";
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Error reading raster metadata: {ex.Message}";
            }
        }

        private void ComboDatumMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (TxtCustomDatum == null) return;
            switch (ComboDatumMode.SelectedIndex)
            {
                case 0: // Mean
                    TxtCustomDatum.IsEnabled = false;
                    TxtCustomDatum.Text = $"{_demMean:F2}";
                    break;
                case 1: // Min
                    TxtCustomDatum.IsEnabled = false;
                    TxtCustomDatum.Text = $"{_demMin:F2}";
                    break;
                case 2: // Custom
                    TxtCustomDatum.IsEnabled = true;
                    TxtCustomDatum.Focus();
                    break;
            }
        }

        private async void BtnCompute_Click(object sender, RoutedEventArgs e)
        {
            if (ComboDemSurface.SelectedIndex < 0 || ComboDemSurface.SelectedIndex >= _rasterLayers.Count)
            {
                MessageBox.Show("Please select a valid DEM elevation surface.", "Volumetric Analysis", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var layer = _rasterLayers[ComboDemSurface.SelectedIndex];
            double datum = _demMean;
            if (double.TryParse(TxtCustomDatum.Text, out double customVal))
            {
                datum = customVal;
            }

            int numStages = 25;
            if (ComboStageSteps.SelectedIndex == 0) numStages = 15;
            else if (ComboStageSteps.SelectedIndex == 2) numStages = 50;

            TxtStatus.Text = $"Computing 3D volumetrics & {numStages} stage-storage capacity levels...";
            _storageRows.Clear();
            BtnExportCsv.IsEnabled = false;

            try
            {
                var result = await Task.Run(() => ComputeVolumetricsAndStorage(layer.FilePath, datum, numStages));

                foreach (var step in result.steps)
                {
                    _storageRows.Add(step);
                }

                TxtTableInfo.Text = $"{_storageRows.Count} hypsometric stages calculated ({result.validCells:N0} cells computed in {result.elapsedMs}ms)";
                TxtStatus.Text = $"Volumetric analysis complete! Full capacity: {result.volBelow / 1000.0:N1} ML ({result.elapsedMs}ms).";
                BtnExportCsv.IsEnabled = true;
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Volumetric calculation error: {ex.Message}";
                MessageBox.Show($"Error computing volumetric analysis: {ex.Message}", "Analysis Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private (double minZ, double maxZ, double meanZ) SampleQuickElevationStats(string filePath)
        {
            using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
            if (ds == null) throw new Exception("Could not open raster.");
            var band = ds.GetRasterBand(1);
            band.GetStatistics(0, 1, out double min, out double max, out double mean, out double _);
            return (min, max, mean);
        }

        private (double volAbove, double volBelow, double netVol, double totalAreaM2, double minZ, double maxZ, double meanZ, int validCells, List<StageStorageRow> steps, long elapsedMs)
            ComputeVolumetricsAndStorage(string filePath, double datum, int numStages)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            using var ds = Gdal.Open(filePath, Access.GA_ReadOnly);
            if (ds == null) throw new Exception("Could not open raster with GDAL.");

            int w = Math.Min(ds.RasterXSize, 2048);
            int h = (int)Math.Max(1, Math.Round((double)ds.RasterYSize / ds.RasterXSize * w));

            var band = ds.GetRasterBand(1);
            float[] buf = new float[w * h];
            band.ReadRaster(0, 0, ds.RasterXSize, ds.RasterYSize, buf, w, h, 0, 0);

            double[] gt = new double[6];
            ds.GetGeoTransform(gt);
            double cellW = Math.Abs(gt[1]) * ((double)ds.RasterXSize / w);
            double cellH = Math.Abs(gt[5]) * ((double)ds.RasterYSize / h);
            if (cellW <= 0) cellW = 1.0;
            if (cellH <= 0) cellH = 1.0;
            double cellArea = cellW * cellH;

            band.GetNoDataValue(out double nodata, out int hasNoData);

            double minZ = double.MaxValue;
            double maxZ = double.MinValue;
            double sumZ = 0;
            int validCount = 0;

            for (int i = 0; i < buf.Length; i++)
            {
                float z = buf[i];
                if (float.IsNaN(z) || float.IsInfinity(z)) continue;
                if (hasNoData != 0 && Math.Abs(z - nodata) < 1e-4) continue;
                if (z < -1000 || z > 50000) continue;

                if (z < minZ) minZ = z;
                if (z > maxZ) maxZ = z;
                sumZ += z;
                validCount++;
            }

            if (validCount == 0) throw new Exception("No valid elevation cells found in the DEM.");

            double meanZ = sumZ / validCount;
            double totalAreaM2 = validCount * cellArea;

            // Volumetrics relative to Datum
            double volAbove = 0;
            double volBelow = 0;

            for (int i = 0; i < buf.Length; i++)
            {
                float z = buf[i];
                if (float.IsNaN(z) || float.IsInfinity(z)) continue;
                if (hasNoData != 0 && Math.Abs(z - nodata) < 1e-4) continue;
                if (z < -1000 || z > 50000) continue;

                double diff = z - datum;
                if (diff > 0) volAbove += diff * cellArea;
                else if (diff < 0) volBelow += Math.Abs(diff) * cellArea;
            }

            double netVol = volAbove - volBelow;

            // Compute Hypsometric Stage-Storage Curve
            var steps = new List<StageStorageRow>();
            double range = maxZ - minZ;
            double stepSize = range / Math.Max(1, numStages);

            for (int s = 0; s <= numStages; s++)
            {
                double stageElev = minZ + (s * stepSize);
                double stageHeight = stageElev - minZ;
                double inundatedCells = 0;
                double stageVol = 0;

                for (int i = 0; i < buf.Length; i++)
                {
                    float z = buf[i];
                    if (float.IsNaN(z) || float.IsInfinity(z)) continue;
                    if (hasNoData != 0 && Math.Abs(z - nodata) < 1e-4) continue;
                    if (z < -1000 || z > 50000) continue;

                    if (z <= stageElev)
                    {
                        inundatedCells++;
                        stageVol += (stageElev - z) * cellArea;
                    }
                }

                steps.Add(new StageStorageRow
                {
                    StageIndex = s + 1,
                    Elevation = stageElev,
                    StageHeight = stageHeight,
                    AreaM2 = inundatedCells * cellArea,
                    VolumeBelow = stageVol
                });
            }

            sw.Stop();
            return (volAbove, volBelow, netVol, totalAreaM2, minZ, maxZ, meanZ, validCount, steps, sw.ElapsedMilliseconds);
        }

        private void BtnExportCsv_Click(object sender, RoutedEventArgs e)
        {
            if (_storageRows.Count == 0) return;

            if (FileDialogHelper.PromptSave("CSV Spreadsheet (*.csv)|*.csv", $"Stage_Storage_{DateTime.Now:yyyyMMdd_HHmm}.csv", "Export Stage-Storage Capacity Curve") is not { } savePath)
                return;

            try
            {
                var sb = new StringBuilder();
                sb.AppendLine("Stage_Index,Elevation_m,Stage_Height_m,Surface_Area_m2,Surface_Area_ha,Volume_Below_m3,Cumulative_Capacity_m3,Storage_MegaLiters");
                foreach (var r in _storageRows)
                {
                    sb.AppendLine($"{r.StageIndex},{r.Elevation:F3},{r.StageHeight:F3},{r.AreaM2:F2},{r.AreaHa:F4},{r.VolumeBelow:F2},{r.CumulativeCapacity:F2},{r.MegaLiters:F3}");
                }
                File.WriteAllText(savePath, sb.ToString(), Encoding.UTF8);
                MessageBox.Show($"Stage-Storage curve successfully exported to:\n{savePath}", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to export CSV: {ex.Message}", "Export Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
