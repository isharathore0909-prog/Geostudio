using System;
using System.Collections.Generic;
using System.Data;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.Win32;
using GeoStudio.Models;

namespace GeoStudio.UI.Dialogs
{
    public partial class AttributeTableWindow : Window
    {
        private DataTable _dataTable = new();
        private readonly Action<string>? _onZoomToFeature;
        private readonly List<LayerItem> _vectorLayers = new();

        public AttributeTableWindow(IEnumerable<IDictionary<string, object>>? records, Action<string>? onZoomToFeature = null)
        {
            InitializeComponent();
            _onZoomToFeature = onZoomToFeature;
            if (CmbTargetLayer != null) CmbTargetLayer.Visibility = Visibility.Collapsed;
            LoadRecords(records);
        }

        public AttributeTableWindow(IEnumerable<LayerItem>? layers, LayerItem? activeLayer, Action<string>? onZoomToFeature = null)
        {
            InitializeComponent();
            _onZoomToFeature = onZoomToFeature;

            if (layers != null)
            {
                _vectorLayers.AddRange(layers);
            }

            PopulateLayerSelector(activeLayer);
        }

        private void PopulateLayerSelector(LayerItem? activeLayer)
        {
            if (CmbTargetLayer == null) return;
            CmbTargetLayer.Items.Clear();

            if (_vectorLayers.Count == 0)
            {
                CmbTargetLayer.Visibility = Visibility.Collapsed;
                LoadRecords(null);
                return;
            }

            CmbTargetLayer.Visibility = Visibility.Visible;
            ComboBoxItem? selectedItem = null;

            foreach (var l in _vectorLayers)
            {
                string label = $"{l.Name} ({(l.FeatureCount > 0 ? $"{l.FeatureCount:N0} features" : "Vector")})";
                var item = new ComboBoxItem
                {
                    Content = label,
                    Tag = l.Id,
                    DataContext = l
                };
                CmbTargetLayer.Items.Add(item);

                if (activeLayer != null && (l.Id == activeLayer.Id || l.Name == activeLayer.Name))
                {
                    selectedItem = item;
                }
            }

            if (selectedItem != null)
            {
                CmbTargetLayer.SelectedItem = selectedItem;
            }
            else
            {
                CmbTargetLayer.SelectedIndex = 0;
            }

            LoadCurrentLayerData();
        }

        private void CmbTargetLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            LoadCurrentLayerData();
        }

        private void LoadCurrentLayerData()
        {
            var selectedItem = CmbTargetLayer?.SelectedItem as ComboBoxItem;
            var layer = selectedItem?.DataContext as LayerItem;

            if (layer != null)
            {
                var records = LoadRecordsFromVectorLayer(layer);
                if (records.Count > 0)
                {
                    if (TxtLayerSummary != null)
                    {
                        TxtLayerSummary.Text = $"Showing {records.Count:N0} attribute records for {layer.Name}";
                    }
                    LoadRecords(records);
                    return;
                }
            }

            LoadRecords(null);
        }

        private static List<IDictionary<string, object>> LoadRecordsFromVectorLayer(LayerItem layer)
        {
            var records = new List<IDictionary<string, object>>();
            if (string.IsNullOrEmpty(layer.FilePath) || !File.Exists(layer.FilePath)) return records;

            try
            {
                using var fs = File.OpenRead(layer.FilePath);
                using var doc = JsonDocument.Parse(fs);
                if (doc.RootElement.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                {
                    int fid = 1;
                    foreach (var feat in feats.EnumerateArray())
                    {
                        var row = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
                        row["FID"] = fid++;
                        row["Layer"] = layer.Name;

                        if (feat.TryGetProperty("geometry", out var geom) && geom.TryGetProperty("type", out var geomType))
                        {
                            row["Geometry"] = geomType.GetString() ?? "Feature";
                        }

                        if (feat.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                        {
                            foreach (var prop in props.EnumerateObject())
                            {
                                object val = prop.Value.ValueKind switch
                                {
                                    JsonValueKind.String => prop.Value.GetString() ?? "",
                                    JsonValueKind.Number => prop.Value.TryGetInt64(out var i) ? (object)i : prop.Value.GetDouble(),
                                    JsonValueKind.True => true,
                                    JsonValueKind.False => false,
                                    JsonValueKind.Null => "",
                                    _ => prop.Value.GetRawText()
                                };
                                row[prop.Name] = val;
                            }
                        }
                        records.Add(row);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to load vector records from {layer.FilePath}: {ex.Message}");
            }

            return records;
        }

        public void LoadRecords(IEnumerable<IDictionary<string, object>>? records)
        {
            _dataTable = new DataTable();

            if (records == null || !records.Any())
            {
                // Fallback only if no layers loaded
                _dataTable.Columns.Add("FID", typeof(int));
                _dataTable.Columns.Add("Layer", typeof(string));
                _dataTable.Columns.Add("Status", typeof(string));

                _dataTable.Rows.Add(1, "No Vector Data", "Load a vector dataset (GeoJSON/SHP) to view attribute records.");
            }
            else
            {
                var recordList = records.ToList();
                var allKeys = new List<string>();

                // Ensure FID, Layer, Geometry are first
                if (recordList.Any(r => r.ContainsKey("FID"))) allKeys.Add("FID");
                if (recordList.Any(r => r.ContainsKey("Layer"))) allKeys.Add("Layer");
                if (recordList.Any(r => r.ContainsKey("Geometry"))) allKeys.Add("Geometry");

                foreach (var r in recordList)
                {
                    foreach (var k in r.Keys)
                    {
                        if (!allKeys.Contains(k, StringComparer.OrdinalIgnoreCase))
                        {
                            allKeys.Add(k);
                        }
                    }
                }

                foreach (var key in allKeys)
                {
                    _dataTable.Columns.Add(key, typeof(string));
                }

                foreach (var r in recordList)
                {
                    var row = _dataTable.NewRow();
                    foreach (var k in allKeys)
                    {
                        row[k] = r.TryGetValue(k, out var val) ? (val?.ToString() ?? "") : "";
                    }
                    _dataTable.Rows.Add(row);
                }
            }

            GridAttributes.ItemsSource = _dataTable.DefaultView;
            TxtRowCount.Text = $"{_dataTable.Rows.Count:N0} feature records loaded";
        }

        private void TxtFilter_TextChanged(object sender, TextChangedEventArgs e)
        {
            string filter = TxtFilter.Text.Trim();
            if (string.IsNullOrEmpty(filter))
            {
                _dataTable.DefaultView.RowFilter = "";
            }
            else
            {
                try
                {
                    var clauses = new List<string>();
                    foreach (DataColumn col in _dataTable.Columns)
                    {
                        if (col.DataType == typeof(string))
                        {
                            clauses.Add($"[{col.ColumnName}] LIKE '%{filter.Replace("'", "''")}%'");
                        }
                    }
                    _dataTable.DefaultView.RowFilter = string.Join(" OR ", clauses);
                }
                catch
                {
                    _dataTable.DefaultView.RowFilter = "";
                }
            }
            TxtRowCount.Text = $"{_dataTable.DefaultView.Count:N0} of {_dataTable.Rows.Count:N0} records matching";
        }

        private void BtnZoomToSelectedRow_Click(object sender, RoutedEventArgs e)
        {
            if (GridAttributes.SelectedItem is DataRowView drv)
            {
                string id = drv.Row.Table.Columns.Contains("FID") ? drv.Row["FID"].ToString() ?? "" : "";
                _onZoomToFeature?.Invoke(id);
            }
        }

        private void GridAttributes_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            BtnZoomToSelectedRow_Click(sender, e);
        }

        private void BtnExportCsv_Click(object sender, RoutedEventArgs e)
        {
            if (_dataTable.Rows.Count == 0)
            {
                MessageBox.Show("No records available to export.", "Export CSV", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var dlg = new SaveFileDialog
            {
                Title = "Export Attributes to CSV",
                Filter = "CSV Files (*.csv)|*.csv|All Files (*.*)|*.*",
                FileName = $"attributes_{DateTime.Now:yyyyMMdd_HHmmss}.csv"
            };

            if (dlg.ShowDialog() == true)
            {
                try
                {
                    using var sw = new StreamWriter(dlg.FileName);
                    var colNames = _dataTable.Columns.Cast<DataColumn>().Select(c => $"\"{c.ColumnName.Replace("\"", "\"\"")}\"");
                    sw.WriteLine(string.Join(",", colNames));

                    foreach (DataRowView drv in _dataTable.DefaultView)
                    {
                        var fields = drv.Row.ItemArray.Select(field => $"\"{field?.ToString()?.Replace("\"", "\"\"") ?? ""}\"");
                        sw.WriteLine(string.Join(",", fields));
                    }

                    MessageBox.Show($"Successfully exported {_dataTable.DefaultView.Count} records to:\n{dlg.FileName}", "Export Successful", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Failed to export CSV: {ex.Message}", "Export Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
