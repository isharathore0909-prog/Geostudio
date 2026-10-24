using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using GeoStudio.Models;

namespace GeoStudio.UI.Dialogs
{
    public partial class TransposeFieldsWindow : Window
    {
        private readonly List<LayerItem> _vectorLayers;
        private readonly Action<string>? _onTransposeReady;
        private string? _customInputFilePath;

        public TransposeFieldsWindow(List<LayerItem> vectorLayers, LayerItem? selectedLayer = null, Action<string>? onTransposeReady = null)
        {
            InitializeComponent();
            _vectorLayers = vectorLayers ?? new List<LayerItem>();
            _onTransposeReady = onTransposeReady;

            PopulateLayerCombo(selectedLayer);
        }

        private void PopulateLayerCombo(LayerItem? selectedLayer)
        {
            ComboInputLayer.Items.Clear();
            foreach (var l in _vectorLayers)
            {
                var item = new ComboBoxItem
                {
                    Content = $"📁  {l.Name} ({(l.FeatureCount > 0 ? $"{l.FeatureCount:N0} features" : "Vector")})",
                    Tag = l.FilePath,
                    DataContext = l
                };
                ComboInputLayer.Items.Add(item);
                if (selectedLayer != null && (l.Id == selectedLayer.Id || l.FilePath == selectedLayer.FilePath))
                {
                    ComboInputLayer.SelectedItem = item;
                }
            }

            if (ComboInputLayer.SelectedItem == null && ComboInputLayer.Items.Count > 0)
            {
                ComboInputLayer.SelectedIndex = 0;
            }
        }

        private void ComboInputLayer_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            var item = ComboInputLayer.SelectedItem as ComboBoxItem;
            var layer = item?.DataContext as LayerItem;
            string? filePath = layer?.FilePath ?? (item?.Tag as string);
            if (!string.IsNullOrEmpty(filePath) && File.Exists(filePath))
            {
                LoadFieldsFromPath(filePath);
            }
        }

        private void BtnBrowseInput_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Select Vector Dataset to Transpose",
                Filter = "All Vector & Tabular Files (*.geojson;*.json;*.csv;*.shp)|*.geojson;*.json;*.csv;*.shp|GeoJSON (*.geojson)|*.geojson|CSV Files (*.csv)|*.csv|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                _customInputFilePath = dlg.FileName;
                var item = new ComboBoxItem
                {
                    Content = $"📄  {Path.GetFileName(dlg.FileName)}",
                    Tag = dlg.FileName,
                    IsSelected = true
                };
                ComboInputLayer.Items.Insert(0, item);
                ComboInputLayer.SelectedIndex = 0;
                LoadFieldsFromPath(dlg.FileName);
            }
        }

        private void LoadFieldsFromPath(string filePath)
        {
            ListAvailableFields.Items.Clear();
            ListTransposeFields.Items.Clear();
            ListKeepFields.Items.Clear();

            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            var discoveredFields = new List<string>();

            try
            {
                if (ext == ".csv")
                {
                    using var reader = new StreamReader(filePath);
                    string? headerLine = reader.ReadLine();
                    if (!string.IsNullOrEmpty(headerLine))
                    {
                        var parts = headerLine.Split(new[] { ',', ';', '\t' });
                        foreach (var p in parts)
                        {
                            string clean = p.Trim('\"', ' ', '\r', '\n');
                            if (!string.IsNullOrWhiteSpace(clean)) discoveredFields.Add(clean);
                        }
                    }
                }
                else if (ext == ".geojson" || ext == ".json")
                {
                    using var fs = File.OpenRead(filePath);
                    using var doc = JsonDocument.Parse(fs);
                    if (doc.RootElement.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var feat in feats.EnumerateArray())
                        {
                            if (feat.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                            {
                                foreach (var p in props.EnumerateObject())
                                {
                                    if (!discoveredFields.Contains(p.Name, StringComparer.OrdinalIgnoreCase))
                                    {
                                        discoveredFields.Add(p.Name);
                                    }
                                }
                            }
                            if (discoveredFields.Count > 0) break;
                        }
                    }
                }
                else
                {
                    // Attempt OGR reflection if MaxRev.Gdal is loaded
                    try
                    {
                        using var ds = OSGeo.OGR.Ogr.Open(filePath, 0);
                        if (ds != null && ds.GetLayerCount() > 0)
                        {
                            var lyr = ds.GetLayerByIndex(0);
                            var defn = lyr.GetLayerDefn();
                            int count = defn.GetFieldCount();
                            for (int i = 0; i < count; i++)
                            {
                                discoveredFields.Add(defn.GetFieldDefn(i).GetName());
                            }
                        }
                    }
                    catch { }
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Error reading fields: {ex.Message}";
            }

            // Fallback: check if the LayerItem has AttributeFields
            if (discoveredFields.Count == 0 && ComboInputLayer.SelectedItem is ComboBoxItem cbi && cbi.DataContext is LayerItem li && li.AttributeFields.Count > 0)
            {
                discoveredFields.AddRange(li.AttributeFields);
            }

            foreach (var f in discoveredFields)
            {
                if (f.Equals("fid", StringComparison.OrdinalIgnoreCase) || f.Equals("ogc_fid", StringComparison.OrdinalIgnoreCase))
                    continue;
                ListAvailableFields.Items.Add(f);
            }

            // Setup default output path
            string defaultDir = Path.GetDirectoryName(filePath) ?? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
            string baseName = Path.GetFileNameWithoutExtension(filePath);
            TxtOutputPath.Text = Path.Combine(defaultDir, $"{baseName}_transposed.csv");

            TxtStatus.Text = $"Found {ListAvailableFields.Items.Count} fields available for transpose.";
        }

        private void BtnAddTranspose_Click(object sender, RoutedEventArgs e)
        {
            var selected = ListAvailableFields.SelectedItems.Cast<object>().ToList();
            foreach (var item in selected)
            {
                string val = item.ToString() ?? "";
                if (!ListTransposeFields.Items.Contains(val) && !ListKeepFields.Items.Contains(val))
                {
                    ListTransposeFields.Items.Add(val);
                }
            }
        }

        private void BtnAddKeep_Click(object sender, RoutedEventArgs e)
        {
            var selected = ListAvailableFields.SelectedItems.Cast<object>().ToList();
            foreach (var item in selected)
            {
                string val = item.ToString() ?? "";
                if (!ListTransposeFields.Items.Contains(val) && !ListKeepFields.Items.Contains(val))
                {
                    ListKeepFields.Items.Add(val);
                }
            }
        }

        private void BtnRemoveField_Click(object sender, RoutedEventArgs e)
        {
            var selTrans = ListTransposeFields.SelectedItems.Cast<object>().ToList();
            foreach (var item in selTrans) ListTransposeFields.Items.Remove(item);

            var selKeep = ListKeepFields.SelectedItems.Cast<object>().ToList();
            foreach (var item in selKeep) ListKeepFields.Items.Remove(item);
        }

        private void BtnBrowseOutput_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new SaveFileDialog
            {
                Title = "Save Transposed Output Table",
                Filter = "CSV Files (*.csv)|*.csv|GeoJSON Dataset (*.geojson)|*.geojson|All Files (*.*)|*.*",
                FileName = Path.GetFileName(TxtOutputPath.Text)
            };

            if (dlg.ShowDialog() == true)
            {
                TxtOutputPath.Text = dlg.FileName;
            }
        }

        private async void BtnRun_Click(object sender, RoutedEventArgs e)
        {
            string? inputPath = _customInputFilePath;
            if (string.IsNullOrEmpty(inputPath) && ComboInputLayer.SelectedItem is ComboBoxItem item)
            {
                var layer = item.DataContext as LayerItem;
                inputPath = layer?.FilePath ?? (item.Tag as string);
            }

            if (string.IsNullOrEmpty(inputPath) || !File.Exists(inputPath))
            {
                MessageBox.Show("Please select or browse a valid vector dataset.", "Transpose Fields", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var transposeFields = ListTransposeFields.Items.Cast<string>().ToList();
            if (transposeFields.Count == 0)
            {
                MessageBox.Show("Please add at least one field to the 'Fields to Transpose' list.", "Transpose Fields", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var keepFields = ListKeepFields.Items.Cast<string>().ToList();
            string transposedColName = string.IsNullOrWhiteSpace(TxtTransposedFieldName.Text) ? "Attribute" : TxtTransposedFieldName.Text.Trim();
            string valueColName = string.IsNullOrWhiteSpace(TxtValueFieldName.Text) ? "Value" : TxtValueFieldName.Text.Trim();
            string outputPath = TxtOutputPath.Text.Trim();

            if (string.IsNullOrEmpty(outputPath))
            {
                MessageBox.Show("Please specify an output file path.", "Transpose Fields", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            BtnRun.IsEnabled = false;
            ProgressBarTranspose.Visibility = Visibility.Visible;
            TxtStatus.Text = "Running Transpose (Melt) operation...";

            try
            {
                int rowCount = await Task.Run(() => ExecuteTransposition(inputPath, transposeFields, keepFields, transposedColName, valueColName, outputPath));

                ProgressBarTranspose.Visibility = Visibility.Collapsed;
                TxtStatus.Text = $"✓ Completed: {rowCount:N0} transposed rows written to {Path.GetFileName(outputPath)}";

                var res = MessageBox.Show(
                    $"Transpose Fields Completed Successfully!\n\n" +
                    $"Output Rows: {rowCount:N0}\n" +
                    $"Destination: {outputPath}\n\n" +
                    $"Would you like to load the transposed dataset into GeoStudio now?",
                    "Transpose Fields", MessageBoxButton.YesNo, MessageBoxImage.Information);

                if (res == MessageBoxResult.Yes)
                {
                    _onTransposeReady?.Invoke(outputPath);
                    Close();
                }
            }
            catch (Exception ex)
            {
                ProgressBarTranspose.Visibility = Visibility.Collapsed;
                TxtStatus.Text = $"Error: {ex.Message}";
                MessageBox.Show($"Failed to transpose fields: {ex.Message}", "Transpose Fields Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                BtnRun.IsEnabled = true;
            }
        }

        private static int ExecuteTransposition(
            string inputPath,
            List<string> transposeFields,
            List<string> keepFields,
            string transposedColName,
            string valueColName,
            string outputPath)
        {
            string ext = Path.GetExtension(inputPath).ToLowerInvariant();
            var rows = new List<Dictionary<string, object?>>();

            if (ext == ".csv")
            {
                using var reader = new StreamReader(inputPath);
                string? header = reader.ReadLine();
                if (header != null)
                {
                    var cols = header.Split(new[] { ',', ';', '\t' }).Select(c => c.Trim('\"', ' ')).ToArray();
                    string? line;
                    while ((line = reader.ReadLine()) != null)
                    {
                        var vals = line.Split(new[] { ',', ';', '\t' });
                        var row = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
                        for (int i = 0; i < cols.Length && i < vals.Length; i++)
                        {
                            row[cols[i]] = vals[i].Trim('\"', ' ');
                        }
                        rows.Add(row);
                    }
                }
            }
            else
            {
                // GeoJSON or OGR
                using var fs = File.OpenRead(inputPath);
                using var doc = JsonDocument.Parse(fs);
                if (doc.RootElement.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                {
                    foreach (var feat in feats.EnumerateArray())
                    {
                        var row = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
                        if (feat.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                        {
                            foreach (var p in props.EnumerateObject())
                            {
                                row[p.Name] = p.Value.ValueKind switch
                                {
                                    JsonValueKind.String => p.Value.GetString(),
                                    JsonValueKind.Number => p.Value.GetRawText(),
                                    JsonValueKind.True => "true",
                                    JsonValueKind.False => "false",
                                    _ => p.Value.GetRawText()
                                };
                            }
                        }
                        rows.Add(row);
                    }
                }
            }

            if (rows.Count == 0)
            {
                throw new InvalidOperationException("No records found in the input dataset.");
            }

            // Perform Melt / Transposition
            var outputRows = new List<Dictionary<string, object?>>();
            foreach (var r in rows)
            {
                foreach (var tf in transposeFields)
                {
                    var newRow = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
                    foreach (var kf in keepFields)
                    {
                        newRow[kf] = r.TryGetValue(kf, out var v) ? v : null;
                    }
                    newRow[transposedColName] = tf;
                    newRow[valueColName] = r.TryGetValue(tf, out var val) ? val : null;
                    outputRows.Add(newRow);
                }
            }

            // Write Output (CSV format by default or if .csv)
            string outDir = Path.GetDirectoryName(outputPath) ?? "";
            if (!string.IsNullOrEmpty(outDir) && !Directory.Exists(outDir)) Directory.CreateDirectory(outDir);

            using var sw = new StreamWriter(outputPath, false, Encoding.UTF8);
            var allOutputHeaders = new List<string>(keepFields) { transposedColName, valueColName };
            sw.WriteLine(string.Join(",", allOutputHeaders.Select(h => $"\"{EscapeCsv(h)}\"")));

            foreach (var row in outputRows)
            {
                var lineVals = allOutputHeaders.Select(h =>
                {
                    string v = row.TryGetValue(h, out var val) && val != null ? val.ToString() ?? "" : "";
                    return $"\"{EscapeCsv(v)}\"";
                });
                sw.WriteLine(string.Join(",", lineVals));
            }

            return outputRows.Count;
        }

        private static string EscapeCsv(string s) => s.Replace("\"", "\"\"");

        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}
