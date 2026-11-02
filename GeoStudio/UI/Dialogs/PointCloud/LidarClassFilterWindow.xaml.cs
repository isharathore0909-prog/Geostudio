
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.PointCloud;

namespace GeoStudio.UI.Dialogs.PointCloud
{
    public partial class LidarClassFilterWindow : Window
    {
        private readonly MainWindow _main;
        private string? _activeFilePath;
        private long _totalPoints = 0;
        private bool _isInitializing = false;
        public ObservableCollection<LidarClassItemViewModel> Classes { get; set; } = new();

        public LidarClassFilterWindow(MainWindow main, IEnumerable<byte>? initialSelection = null)
        {
            _isInitializing = true;
            _main = main;
            InitializeComponent();
            Owner = main;
            ListClasses.ItemsSource = Classes;
            LoadCurrentPointCloud(initialSelection);
            _isInitializing = false;

            if (ChkLiveUpdate?.IsChecked == true)
            {
                ApplyFilterToMap();
            }
        }

        private void LoadCurrentPointCloud(IEnumerable<byte>? initialSelection = null)
        {
            var ptLayer = _main.Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            if (ptLayer == null || string.IsNullOrEmpty(ptLayer.FilePath) || !File.Exists(ptLayer.FilePath))
            {
                BtnExport.IsEnabled = false;
                return;
            }

            _activeFilePath = ptLayer.FilePath;

            string outDir = Path.GetDirectoryName(_activeFilePath) ?? Path.GetTempPath();
            string baseName = Path.GetFileNameWithoutExtension(_activeFilePath);
            TxtExportPath.Text = Path.Combine(outDir, $"{baseName}_filtered.las");

            // Scan classification counts from active in-memory batch or file
            byte[]? activeBatchCls = _main.ActivePointCloudBatch?.c;
            var counts = LasPointCloudService.ScanClassificationCounts(_activeFilePath, activeBatchCls);

            _totalPoints = counts.Values.Sum();
            if (_totalPoints == 0 && ptLayer.FeatureCount > 0) _totalPoints = ptLayer.FeatureCount;

            // If initialSelection was not provided, check if layer already has active selections in sidebar
            if (initialSelection == null && ptLayer.LidarClasses != null && ptLayer.LidarClasses.Count > 0)
            {
                var selInSidebar = ptLayer.LidarClasses.Where(c => c.IsSelected).Select(c => c.ClassId).ToList();
                if (selInSidebar.Count < ptLayer.LidarClasses.Count)
                {
                    initialSelection = selInSidebar;
                }
            }

            HashSet<byte>? initSet = initialSelection != null ? new HashSet<byte>(initialSelection) : null;

            Classes.Clear();
            foreach (var kvp in counts.OrderBy(k => k.Key))
            {
                byte classId = kvp.Key;
                long count = kvp.Value;
                double pct = _totalPoints > 0 ? (count * 100.0 / _totalPoints) : 0.0;
                var meta = LasPointCloudService.GetClassMeta(classId);

                bool isSelected = initSet == null || initSet.Contains(classId);

                Classes.Add(new LidarClassItemViewModel
                {
                    ClassId = classId,
                    Name = meta.Name,
                    ColorHex = meta.ColorHex,
                    PointCount = count,
                    Percentage = pct,
                    IsSelected = isSelected
                });
            }

            UpdateVisibleSummary();
        }

        public void SyncFromMap(IEnumerable<byte> activeClasses)
        {
            _isInitializing = true;
            try
            {
                var set = new HashSet<byte>(activeClasses);
                foreach (var item in Classes)
                {
                    item.IsSelected = set.Contains(item.ClassId);
                }
                UpdateVisibleSummary();
            }
            finally
            {
                _isInitializing = false;
            }
        }

        private void UpdateVisibleSummary()
        {
            // Point counts are displayed on each row item
        }

        private void ApplyFilterToMap()
        {
            if (_isInitializing || _main == null) return;
            if (ChkLiveUpdate?.IsChecked != true) return;
            if (Classes.Count == 0) return;

            var selectedIds = Classes.Where(c => c.IsSelected).Select(c => c.ClassId).ToList();

            if (selectedIds.Count == Classes.Count)
            {
                // All classes are selected -> disable filter restriction completely so all points render
                _main.FilterLidarClasses(null);
            }
            else
            {
                _main.FilterLidarClasses(selectedIds);
            }

            SyncToSidebar(selectedIds);
        }

        private void SyncToSidebar(List<byte> selectedIds)
        {
            var ptLayer = _main?.Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            if (ptLayer?.LidarClasses == null || ptLayer.LidarClasses.Count == 0) return;

            var selSet = new HashSet<byte>(selectedIds);
            foreach (var item in ptLayer.LidarClasses)
            {
                item.IsSelected = selSet.Contains(item.ClassId);
            }
        }

        private void ClassCheckbox_Click(object sender, RoutedEventArgs e)
        {
            UpdateVisibleSummary();
            ApplyFilterToMap();
        }

        private void BtnPresetAll_Click(object sender, RoutedEventArgs e)
        {
            foreach (var c in Classes) c.IsSelected = true;
            UpdateVisibleSummary();
            ApplyFilterToMap();
        }

        private void BtnPresetGround_Click(object sender, RoutedEventArgs e)
        {
            foreach (var c in Classes) c.IsSelected = (c.ClassId == 2 || c.ClassId == 8);
            UpdateVisibleSummary();
            ApplyFilterToMap();
        }

        private void BtnPresetVeg_Click(object sender, RoutedEventArgs e)
        {
            foreach (var c in Classes) c.IsSelected = (c.ClassId >= 3 && c.ClassId <= 5);
            UpdateVisibleSummary();
            ApplyFilterToMap();
        }

        private void BtnPresetBuildings_Click(object sender, RoutedEventArgs e)
        {
            foreach (var c in Classes) c.IsSelected = (c.ClassId == 6);
            UpdateVisibleSummary();
            ApplyFilterToMap();
        }

        private void BtnPresetNone_Click(object sender, RoutedEventArgs e)
        {
            foreach (var c in Classes) c.IsSelected = false;
            UpdateVisibleSummary();
            ApplyFilterToMap();
        }

        private void ChkLiveUpdate_Changed(object sender, RoutedEventArgs e)
        {
            if (_isInitializing || _main == null) return;
            if (ChkLiveUpdate?.IsChecked == true)
            {
                ApplyFilterToMap();
            }
            else
            {
                _main.FilterLidarClasses(null); // Show all on map if live update disabled
            }
        }

        private void ComboExportFormat_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (TxtExportPath == null || ComboExportFormat?.SelectedItem is not System.Windows.Controls.ComboBoxItem item) return;
            string tag = item.Tag?.ToString() ?? "las";
            string currentPath = TxtExportPath.Text;
            if (string.IsNullOrEmpty(currentPath)) return;

            string dir = Path.GetDirectoryName(currentPath) ?? Path.GetTempPath();
            string name = Path.GetFileNameWithoutExtension(currentPath);

            string newExt = tag switch
            {
                "tiff" => ".tif",
                "png" => ".png",
                _ => ".las"
            };

            TxtExportPath.Text = Path.Combine(dir, $"{name}{newExt}");
        }

        private void BtnBrowseExport_Click(object sender, RoutedEventArgs e)
        {
            int filterIdx = (ComboExportFormat?.SelectedIndex ?? 0) + 1;
            var dlg = new SaveFileDialog
            {
                Title = "Export Filtered Point Cloud / Raster",
                Filter = "ASPRS LiDAR LAS (*.las)|*.las|GeoTIFF Surface Raster (*.tif;*.tiff)|*.tif;*.tiff|PNG Image (*.png)|*.png|All Files (*.*)|*.*",
                FilterIndex = filterIdx,
                FileName = Path.GetFileName(TxtExportPath.Text)
            };
            if (dlg.ShowDialog() == true)
            {
                TxtExportPath.Text = dlg.FileName;
                string ext = Path.GetExtension(dlg.FileName).ToLowerInvariant();
                if (ComboExportFormat != null)
                {
                    if (ext == ".tif" || ext == ".tiff") ComboExportFormat.SelectedIndex = 1;
                    else if (ext == ".png") ComboExportFormat.SelectedIndex = 2;
                    else if (ext == ".las") ComboExportFormat.SelectedIndex = 0;
                }
            }
        }

        private async void BtnExport_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_activeFilePath) || !File.Exists(_activeFilePath))
            {
                MessageBox.Show("No active point cloud dataset available.", "Export Points", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var selectedIds = Classes.Where(c => c.IsSelected).Select(c => c.ClassId).ToHashSet();
            if (selectedIds.Count == 0)
            {
                MessageBox.Show("Please select at least one classification to export.", "Export Points", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            string outPath = TxtExportPath.Text.Trim();
            if (string.IsNullOrEmpty(outPath))
            {
                MessageBox.Show("Please specify a valid output destination file path.", "Export Points", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            BtnExport.IsEnabled = false;
            ProgressExport.Visibility = Visibility.Visible;
            TxtProgressStatus.Visibility = Visibility.Visible;
            ProgressExport.Value = 5;
            TxtProgressStatus.Text = "Starting export of selected classes...";
            TxtFooterStatus.Text = "Exporting data...";

            try
            {
                string ext = Path.GetExtension(outPath).ToLowerInvariant();
                bool isRaster = ext == ".tif" || ext == ".tiff" || ext == ".png";

                var (resultPath, written) = await Task.Run(() =>
                {
                    if (isRaster)
                    {
                        string fmt = (ext == ".png") ? "png" : "tiff";
                        return LasSurfaceRasterizerService.ExportClassifiedRaster(
                            _activeFilePath,
                            outPath,
                            selectedIds,
                            fmt,
                            (pct, msg) =>
                            {
                                Dispatcher.Invoke(() =>
                                {
                                    ProgressExport.Value = pct;
                                    TxtProgressStatus.Text = $"{msg} ({pct}%)";
                                    TxtFooterStatus.Text = msg;
                                });
                            });
                    }
                    else
                    {
                        return LasSurfaceRasterizerService.ExportClassifiedLas(
                            _activeFilePath,
                            outPath,
                            selectedIds,
                            (pct, msg) =>
                            {
                                Dispatcher.Invoke(() =>
                                {
                                    ProgressExport.Value = pct;
                                    TxtProgressStatus.Text = $"{msg} ({pct}%)";
                                    TxtFooterStatus.Text = msg;
                                });
                            });
                    }
                });

                ProgressExport.Value = 100;
                TxtProgressStatus.Text = $"Successfully exported {written:N0} points to {Path.GetFileName(resultPath)}";
                TxtFooterStatus.Text = $"Export Complete: {written:N0} points processed.";

                if (ChkAddLayerOnComplete.IsChecked == true && File.Exists(resultPath))
                {
                    if (isRaster)
                    {
                        await _main.LoadRasterFile(resultPath);
                    }
                    else
                    {
                        _main.LoadLidarFile(resultPath);
                    }
                }

                MessageBox.Show(
                    $"Filtered data exported successfully!\n\nFile: {resultPath}\nFormat: {(isRaster ? (ext == ".png" ? "PNG Image" : "GeoTIFF DEM") : "ASPRS LAS")}\nPoints Processed: {written:N0}\nSelected Classes: {string.Join(", ", selectedIds)}",
                    "Export Complete",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                TxtProgressStatus.Text = $"Export error: {ex.Message}";
                TxtFooterStatus.Text = "Export failed.";
                MessageBox.Show($"Failed to export: {ex.Message}", "Export Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                BtnExport.IsEnabled = true;
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
