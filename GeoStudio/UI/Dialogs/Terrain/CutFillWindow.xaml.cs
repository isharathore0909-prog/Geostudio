using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using GeoStudio.Models;
using GeoStudio.UI.Services;
using OSGeo.GDAL;

namespace GeoStudio.UI
{
    public partial class CutFillWindow : Window
    {
        private readonly List<LayerItem> _rasterLayers;
        private double _cutVol = 0;
        private double _fillVol = 0;
        private double _netVol = 0;
        private double _cutArea = 0;
        private double _fillArea = 0;
        private double _totalArea = 0;
        private double _ratio = 0;
        private double _meanThick = 0;

        public CutFillWindow(IEnumerable<LayerItem> layers)
        {
            InitializeComponent();
            _rasterLayers = layers.Where(l => l.Type == LayerType.Raster && !string.IsNullOrEmpty(l.FilePath)).ToList();

            foreach (var r in _rasterLayers)
            {
                ComboBaseSurface.Items.Add(r.Name);
                ComboCompSurface.Items.Add(r.Name);
            }

            if (ComboBaseSurface.Items.Count > 0) ComboBaseSurface.SelectedIndex = 0;
            if (ComboCompSurface.Items.Count > 1) ComboCompSurface.SelectedIndex = 1;
            else if (ComboCompSurface.Items.Count > 0) ComboCompSurface.SelectedIndex = 0;
        }

        private async void BtnCompute_Click(object sender, RoutedEventArgs e)
        {
            if (ComboBaseSurface.SelectedIndex < 0 || ComboCompSurface.SelectedIndex < 0)
            {
                MessageBox.Show("Please select both a base surface and a comparison surface.", "Cut & Fill", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var baseLayer = _rasterLayers[ComboBaseSurface.SelectedIndex];
            var compLayer = _rasterLayers[ComboCompSurface.SelectedIndex];

            TxtStatus.Text = $"Calculating earthwork difference between {baseLayer.Name} and {compLayer.Name}...";

            try
            {
                var result = await Task.Run(() => ComputeVolumetric(baseLayer.FilePath, compLayer.FilePath));

                _cutVol = result.cutVol;
                _fillVol = result.fillVol;
                _netVol = result.netVol;
                _cutArea = result.cutArea;
                _fillArea = result.fillArea;
                _totalArea = result.totalArea;
                _ratio = result.ratio;
                _meanThick = result.meanThick;

                TileCut.Value = $"{_cutVol:N2} m³";
                TileCut.Subtext = $"Area: {_cutArea:N1} m² ({_cutArea / 10000.0:F2} ha)";

                TileFill.Value = $"{_fillVol:N2} m³";
                TileFill.Subtext = $"Area: {_fillArea:N1} m² ({_fillArea / 10000.0:F2} ha)";

                TileNet.Value = $"{_netVol:N2} m³";
                TileNet.Subtext = _netVol > 0 ? "Status: Excess Excavation (Cut Surplus)" :
                                        _netVol < 0 ? "Status: Embankment Deficit (Fill Required)" : "Status: Balanced";

                TileRatio.Value = double.IsInfinity(_ratio) ? "∞" : $"{_ratio:F3}";
                TileMeanThick.Value = $"{_meanThick:F2} m";
                TileTotalArea.Value = $"{_totalArea / 10000.0:F2} ha ({_totalArea:N0} m²)";

                TxtStatus.Text = $"Earthwork calculation complete ({result.sampledCells:N0} survey cells computed in {result.elapsedMs}ms).";
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Calculation error: {ex.Message}";
                MessageBox.Show($"Error computing Cut & Fill: {ex.Message}", "Calculation Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private (double cutVol, double fillVol, double netVol, double cutArea, double fillArea, double totalArea, double ratio, double meanThick, int sampledCells, long elapsedMs)
            ComputeVolumetric(string basePath, string compPath)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            using var dsBase = Gdal.Open(basePath, Access.GA_ReadOnly);
            using var dsComp = Gdal.Open(compPath, Access.GA_ReadOnly);

            if (dsBase == null || dsComp == null)
                throw new Exception("Could not open one of the DEM raster datasets via GDAL.");

            int w = Math.Min(dsBase.RasterXSize, 2048);
            int h = (int)Math.Max(1, Math.Round((double)dsBase.RasterYSize / dsBase.RasterXSize * w));

            var bBase = dsBase.GetRasterBand(1);
            var bComp = dsComp.GetRasterBand(1);

            float[] bufBase = new float[w * h];
            float[] bufComp = new float[w * h];

            bBase.ReadRaster(0, 0, dsBase.RasterXSize, dsBase.RasterYSize, bufBase, w, h, 0, 0);
            bComp.ReadRaster(0, 0, dsComp.RasterXSize, dsComp.RasterYSize, bufComp, w, h, 0, 0);

            double[] gt = new double[6];
            dsBase.GetGeoTransform(gt);
            double cellW = Math.Abs(gt[1]) * ((double)dsBase.RasterXSize / w);
            double cellH = Math.Abs(gt[5]) * ((double)dsBase.RasterYSize / h);
            if (cellW <= 0) cellW = 1.0;
            if (cellH <= 0) cellH = 1.0;
            double cellArea = cellW * cellH;

            bBase.GetNoDataValue(out double ndBase, out int hasNdBase);
            bComp.GetNoDataValue(out double ndComp, out int hasNdComp);

            double cutV = 0;
            double fillV = 0;
            double cutA = 0;
            double fillA = 0;
            double sumDz = 0;
            int validCells = 0;

            for (int i = 0; i < bufBase.Length; i++)
            {
                float zB = bufBase[i];
                float zC = bufComp[i];

                if (float.IsNaN(zB) || float.IsNaN(zC) || float.IsInfinity(zB) || float.IsInfinity(zC)) continue;
                if (hasNdBase != 0 && Math.Abs(zB - ndBase) < 1e-4) continue;
                if (hasNdComp != 0 && Math.Abs(zC - ndComp) < 1e-4) continue;
                if (zB < -1000 || zB > 50000 || zC < -1000 || zC > 50000) continue;

                double dz = zB - zC; // positive = base higher than comp (cut), negative = base lower than comp (fill)
                sumDz += dz;
                validCells++;

                if (dz > 0.001)
                {
                    cutV += dz * cellArea;
                    cutA += cellArea;
                }
                else if (dz < -0.001)
                {
                    fillV += Math.Abs(dz) * cellArea;
                    fillA += cellArea;
                }
            }

            double netV = cutV - fillV;
            double totA = cutA + fillA;
            double rat = fillV > 0 ? (cutV / fillV) : (cutV > 0 ? double.PositiveInfinity : 1.0);
            double meanTh = validCells > 0 ? (sumDz / validCells) : 0;

            sw.Stop();
            return (cutV, fillV, netV, cutA, fillA, totA, rat, meanTh, validCells, sw.ElapsedMilliseconds);
        }

        private void BtnExport_Click(object sender, RoutedEventArgs e)
        {
            if (FileDialogHelper.PromptSave("CSV Files (*.csv)|*.csv", "cut_fill_earthwork_summary.csv", "Save Cut & Fill Earthwork Report") is not { } savePath)
                return;

            using var sw = new StreamWriter(savePath);
                sw.WriteLine("Metric,Value,Unit");
                sw.WriteLine($"Base Surface,{ComboBaseSurface.SelectedItem},");
                sw.WriteLine($"Comparison Surface,{ComboCompSurface.SelectedItem},");
                sw.WriteLine($"Cut Volume (Excavation),{_cutVol:F3},m3");
                sw.WriteLine($"Fill Volume (Embankment),{_fillVol:F3},m3");
                sw.WriteLine($"Net Earthwork Volume,{_netVol:F3},m3");
                sw.WriteLine($"Cut Area,{_cutArea:F2},m2");
                sw.WriteLine($"Fill Area,{_fillArea:F2},m2");
                sw.WriteLine($"Total Survey Area,{_totalArea:F2},m2");
                sw.WriteLine($"Cut / Fill Ratio,{_ratio:F4},");
                sw.WriteLine($"Mean Thickness (ΔZ),{_meanThick:F3},m");

                MessageBox.Show("Cut & Fill earthwork report exported to CSV successfully.", "Export Complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
