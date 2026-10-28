using System;
using System.IO;
using System.Text.Json;
using System.Windows;
using GeoStudio.Python;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Dialogs.Raster
{
    public partial class LandsatLstWindow : Window
    {
        public LandsatLstWindow()
        {
            InitializeComponent();
            ShowInTaskbar = false;
        }

        private void BtnBrowseMtl_Click(object sender, RoutedEventArgs e)
        {
            if (FileDialogHelper.PromptOpenInto(TxtMtlPath, "Landsat MTL Files (*_MTL.txt)|*_MTL.txt|Text Files (*.txt)|*.txt|All Files (*.*)|*.*", "Select Landsat Collection 2 MTL File") is { } mtl)
                TryAutoFillBands(mtl);
        }

        private void BtnBrowseB10_Click(object sender, RoutedEventArgs e) =>
            FileDialogHelper.PromptOpenInto(TxtB10Path, "GeoTIFF (*.tif;*.tiff)|*.tif;*.tiff", "Select Landsat Band 10 Thermal GeoTIFF");

        private void BtnBrowseB11_Click(object sender, RoutedEventArgs e) =>
            FileDialogHelper.PromptOpenInto(TxtB11Path, "GeoTIFF (*.tif;*.tiff)|*.tif;*.tiff", "Select Landsat Band 11 Thermal GeoTIFF");

        private void TryAutoFillBands(string mtlPath)
        {
            if (string.IsNullOrEmpty(mtlPath) || !File.Exists(mtlPath)) return;
            string dir = Path.GetDirectoryName(mtlPath) ?? string.Empty;
            if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return;

            if (string.IsNullOrEmpty(TxtB10Path.Text) || !File.Exists(TxtB10Path.Text))
            {
                foreach (var f in Directory.GetFiles(dir, "*B10*.tif"))
                {
                    TxtB10Path.Text = f;
                    break;
                }
            }
            if (string.IsNullOrEmpty(TxtB11Path.Text) || !File.Exists(TxtB11Path.Text))
            {
                foreach (var f in Directory.GetFiles(dir, "*B11*.tif"))
                {
                    TxtB11Path.Text = f;
                    break;
                }
            }
        }

        private async void BtnRunCalibration_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                string mtl = TxtMtlPath.Text.Trim();
                if (string.IsNullOrEmpty(mtl) || !File.Exists(mtl))
                {
                    MessageBox.Show("Please select a valid Landsat Collection 2 MTL metadata file (*_MTL.txt).", "Landsat LST", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                TryAutoFillBands(mtl);
                string b10 = TxtB10Path.Text.Trim();
                string b11 = TxtB11Path.Text.Trim();

                BtnRunCalibration.IsEnabled = false;
                BtnRunCalibration.Content = "⏳ Calculating Split-Window LST...";
                ProgressBarLst.Visibility = Visibility.Visible;
                ProgressBarLst.Value = 10;
                TxtReport.Text = "Initializing USGS Landsat Split-Window LST calculation via Python GDAL pipeline...";

                var result = await PythonPipelineService.ExecuteTaskAsync(
                    task: "landsat_lst",
                    inputFile: mtl,
                    param1: b10,
                    param2: b11,
                    onProgress: (pct, msg) =>
                    {
                        Dispatcher.Invoke(() =>
                        {
                            ProgressBarLst.Value = pct;
                            TxtReport.Text = $"[{pct}%] {msg}";
                        });
                    });

                ProgressBarLst.Visibility = Visibility.Collapsed;
                BtnRunCalibration.IsEnabled = true;
                BtnRunCalibration.Content = "⚡ Run Calibration & Split-Window LST";

                if (result.Success && !string.IsNullOrEmpty(result.OutputFilePath) && File.Exists(result.OutputFilePath))
                {
                    string minStr = "N/A", maxStr = "N/A", meanStr = "N/A", pixStr = "N/A";
                    if (!string.IsNullOrEmpty(result.OutputData))
                    {
                        try
                        {
                            using var doc = JsonDocument.Parse(result.OutputData);
                            var root = doc.RootElement;
                            if (root.TryGetProperty("min_lst", out var minP)) minStr = $"{minP.GetDouble():F2}";
                            if (root.TryGetProperty("max_lst", out var maxP)) maxStr = $"{maxP.GetDouble():F2}";
                            if (root.TryGetProperty("mean_lst", out var meanP)) meanStr = $"{meanP.GetDouble():F2}";
                            if (root.TryGetProperty("valid_pixels", out var pixP)) pixStr = $"{pixP.GetInt64():N0}";
                        }
                        catch { }
                    }

                    TxtReport.Text =
                        "✓ Split-Window Land Surface Temperature (LST) Generated Successfully!\n\n" +
                        $"• Output File: {Path.GetFileName(result.OutputFilePath)}\n" +
                        $"• Full Path: {result.OutputFilePath}\n" +
                        $"• Surface Temperature: {minStr} °C to {maxStr} °C (Scene Mean: {meanStr} °C)\n" +
                        $"• Calibrated Valid Pixels: {pixStr}\n" +
                        "• Atmospheric Correction: Du/Sobrino Split-Window with dynamic FVC emissivity & QA cloud masking.\n\n" +
                        "✓ Successfully added layer to map canvas.";

                    var main = Owner as MainWindow ?? Application.Current.MainWindow as MainWindow;
                    if (main != null)
                    {
                        if (main.WindowState == WindowState.Minimized)
                        {
                            main.WindowState = WindowState.Normal;
                        }
                        await main.LoadRasterFile(result.OutputFilePath);
                        main.Activate();
                        Activate();
                    }
                }
                else
                {
                    TxtReport.Text = $"Calibration & LST processing failed:\n{result.ErrorMessage}";
                    MessageBox.Show($"LST processing failed:\n{result.ErrorMessage}", "Landsat LST Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                ProgressBarLst.Visibility = Visibility.Collapsed;
                BtnRunCalibration.IsEnabled = true;
                BtnRunCalibration.Content = "⚡ Run Calibration & Split-Window LST";
                TxtReport.Text = $"Unexpected error: {ex.Message}";
                MessageBox.Show($"Unexpected error: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            WindowHelper.RestoreAndFocusMainWindow(this);
        }
    }
}
