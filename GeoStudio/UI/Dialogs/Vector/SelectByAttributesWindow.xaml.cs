using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;

namespace GeoStudio.UI.Dialogs
{
    public partial class SelectByAttributesWindow : Window
    {
        private readonly Action<string?, string, string, string>? _onSelectWithLayer;
        private readonly List<LayerItem> _vectorLayers = new();
        private readonly Dictionary<string, Dictionary<string, List<string>>> _layerFieldValuesCache = new();

        public SelectByAttributesWindow(Action<string, string, string>? onSelect)
            : this(null, null, (layerId, field, op, val) => onSelect?.Invoke(field, op, val))
        {
        }

        public SelectByAttributesWindow(IEnumerable<LayerItem>? vectorLayers, LayerItem? currentLayer, Action<string?, string, string, string>? onSelect)
        {
            InitializeComponent();
            _onSelectWithLayer = onSelect;

            if (vectorLayers != null)
            {
                _vectorLayers.AddRange(vectorLayers);
            }

            PopulateLayers(currentLayer);
            UpdatePreview();
        }

        private void PopulateLayers(LayerItem? currentLayer)
        {
            if (CmbLayers == null) return;
            CmbLayers.Items.Clear();

            var allItem = new ComboBoxItem { Content = "All Loaded Vector Layers", Tag = null };
            CmbLayers.Items.Add(allItem);

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
                CmbLayers.Items.Add(item);

                if (currentLayer != null && (l.Id == currentLayer.Id || l.Name == currentLayer.Name))
                {
                    selectedItem = item;
                }
            }

            if (selectedItem != null)
            {
                CmbLayers.SelectedItem = selectedItem;
            }
            else if (CmbLayers.Items.Count > 1)
            {
                CmbLayers.SelectedIndex = 1; // Select first actual layer
            }
            else
            {
                CmbLayers.SelectedIndex = 0;
            }

            RefreshAttributeFields();
        }

        private void CmbLayers_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            RefreshAttributeFields();
            UpdatePreview();
        }

        private void RefreshAttributeFields()
        {
            if (CmbField == null) return;

            var selectedItem = CmbLayers.SelectedItem as ComboBoxItem;
            var targetLayer = selectedItem?.DataContext as LayerItem;

            var fields = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            if (targetLayer != null)
            {
                EnsureLayerAttributes(targetLayer);
                foreach (var f in targetLayer.AttributeFields)
                {
                    fields.Add(f);
                }
            }
            else
            {
                foreach (var l in _vectorLayers)
                {
                    EnsureLayerAttributes(l);
                    foreach (var f in l.AttributeFields)
                    {
                        fields.Add(f);
                    }
                }
            }

            CmbField.Items.Clear();

            if (fields.Count > 0)
            {
                foreach (var f in fields.OrderBy(x => x))
                {
                    CmbField.Items.Add(f);
                }

                // Pick sensible default attribute (NAME, MATERIAL, TYPE, ID, ELEV or first)
                string? preferred = fields.FirstOrDefault(f => f.Equals("MATERIAL", StringComparison.OrdinalIgnoreCase))
                                 ?? fields.FirstOrDefault(f => f.Contains("MATERIAL", StringComparison.OrdinalIgnoreCase))
                                 ?? fields.FirstOrDefault(f => f.Equals("NAME", StringComparison.OrdinalIgnoreCase))
                                 ?? fields.FirstOrDefault(f => f.Equals("TYPE", StringComparison.OrdinalIgnoreCase))
                                 ?? fields.FirstOrDefault(f => f.Equals("ELEV", StringComparison.OrdinalIgnoreCase))
                                 ?? fields.FirstOrDefault();

                CmbField.SelectedItem = preferred ?? CmbField.Items[0];
                CmbField.Text = preferred ?? CmbField.Items[0]?.ToString() ?? "";

                if (TxtFieldHint != null)
                {
                    TxtFieldHint.Text = $"✓ {fields.Count} attribute field(s) detected in {(targetLayer?.Name ?? "loaded layers")}";
                    TxtFieldHint.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(16, 185, 129));
                }
            }
            else
            {
                CmbField.Text = "ELEV";
                if (TxtFieldHint != null)
                {
                    TxtFieldHint.Text = "e.g. MATERIAL, NAME, TYPE, ELEV, ID";
                    TxtFieldHint.Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(148, 163, 184));
                }
            }

            RefreshUniqueValues();
        }

        private void RefreshUniqueValues()
        {
            if (CmbValue == null || CmbField == null) return;

            string field = CmbField.Text.Trim();
            if (string.IsNullOrEmpty(field) && CmbField.SelectedItem != null)
            {
                field = CmbField.SelectedItem.ToString() ?? "";
            }

            if (string.IsNullOrEmpty(field))
            {
                CmbValue.Items.Clear();
                if (TxtValueCountHint != null) TxtValueCountHint.Text = "";
                return;
            }

            var selectedItem = CmbLayers.SelectedItem as ComboBoxItem;
            var targetLayer = selectedItem?.DataContext as LayerItem;

            var uniqueValues = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            if (targetLayer != null)
            {
                var valuesMap = GetLayerFieldValues(targetLayer);
                if (valuesMap.TryGetValue(field, out var vals))
                {
                    foreach (var v in vals) uniqueValues.Add(v);
                }
                else
                {
                    // Fallback case-insensitive search in map
                    var key = valuesMap.Keys.FirstOrDefault(k => k.Equals(field, StringComparison.OrdinalIgnoreCase));
                    if (key != null && valuesMap.TryGetValue(key, out var matchVals))
                    {
                        foreach (var v in matchVals) uniqueValues.Add(v);
                    }
                }
            }
            else
            {
                // All layers
                foreach (var l in _vectorLayers)
                {
                    var valuesMap = GetLayerFieldValues(l);
                    var key = valuesMap.Keys.FirstOrDefault(k => k.Equals(field, StringComparison.OrdinalIgnoreCase));
                    if (key != null && valuesMap.TryGetValue(key, out var vals))
                    {
                        foreach (var v in vals) uniqueValues.Add(v);
                    }
                }
            }

            CmbValue.Items.Clear();

            if (uniqueValues.Count > 0)
            {
                var sorted = uniqueValues.OrderBy(x => x).ToList();
                foreach (var v in sorted)
                {
                    CmbValue.Items.Add(v);
                }

                // Preselect first unique value
                CmbValue.SelectedItem = sorted[0];
                CmbValue.Text = sorted[0];

                if (TxtValueCountHint != null)
                {
                    TxtValueCountHint.Text = $"({uniqueValues.Count:N0} unique values available ▾)";
                }
            }
            else
            {
                if (TxtValueCountHint != null)
                {
                    TxtValueCountHint.Text = "(Type custom value)";
                }
            }

            UpdatePreview();
        }

        private Dictionary<string, List<string>> GetLayerFieldValues(LayerItem layer)
        {
            if (_layerFieldValuesCache.TryGetValue(layer.Id, out var cached))
            {
                return cached;
            }

            var result = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
            if (string.IsNullOrEmpty(layer.FilePath) || !File.Exists(layer.FilePath))
            {
                _layerFieldValuesCache[layer.Id] = result;
                return result;
            }

            try
            {
                using var fs = File.OpenRead(layer.FilePath);
                using var doc = JsonDocument.Parse(fs);
                if (doc.RootElement.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                {
                    var sets = new Dictionary<string, HashSet<string>>(StringComparer.OrdinalIgnoreCase);

                    foreach (var f in feats.EnumerateArray())
                    {
                        if (f.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                        {
                            foreach (var prop in props.EnumerateObject())
                            {
                                if (!sets.TryGetValue(prop.Name, out var set))
                                {
                                    set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                                    sets[prop.Name] = set;
                                }

                                string? val = prop.Value.ValueKind switch
                                {
                                    JsonValueKind.String => prop.Value.GetString(),
                                    JsonValueKind.Number => prop.Value.GetRawText(),
                                    JsonValueKind.True => "true",
                                    JsonValueKind.False => "false",
                                    _ => null
                                };

                                if (!string.IsNullOrWhiteSpace(val) && set.Count < 500)
                                {
                                    set.Add(val.Trim());
                                }
                            }
                        }
                    }

                    foreach (var kv in sets)
                    {
                        result[kv.Key] = kv.Value.OrderBy(x => x).ToList();
                    }
                }
            }
            catch { }

            _layerFieldValuesCache[layer.Id] = result;
            return result;
        }

        private void EnsureLayerAttributes(LayerItem layer)
        {
            if (layer.AttributeFields != null && layer.AttributeFields.Count > 0) return;
            var valuesMap = GetLayerFieldValues(layer);
            layer.AttributeFields = valuesMap.Keys.ToList();
        }

        private void CmbField_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (CmbField.SelectedItem != null)
            {
                CmbField.Text = CmbField.SelectedItem.ToString();
            }
            RefreshUniqueValues();
        }

        private void CmbValue_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (CmbValue.SelectedItem != null)
            {
                CmbValue.Text = CmbValue.SelectedItem.ToString();
            }
            UpdatePreview();
        }

        private void UpdatePreview()
        {
            if (TxtExpressionPreview == null || CmbField == null || CmbOperator == null || CmbValue == null) return;

            string field = CmbField.Text.Trim();
            if (string.IsNullOrEmpty(field) && CmbField.SelectedItem != null)
            {
                field = CmbField.SelectedItem.ToString() ?? "";
            }

            string op = (CmbOperator.SelectedItem as ComboBoxItem)?.Tag as string ?? "=";
            string val = CmbValue.Text.Trim();
            if (string.IsNullOrEmpty(val) && CmbValue.SelectedItem != null)
            {
                val = CmbValue.SelectedItem.ToString() ?? "";
            }

            if (op == "contains")
            {
                TxtExpressionPreview.Text = $"WHERE {field} LIKE '%{val}%'";
            }
            else
            {
                TxtExpressionPreview.Text = $"WHERE {field} {op} '{val}'";
            }
        }

        private void UpdatePreview_TextChanged(object sender, TextChangedEventArgs e) => UpdatePreview();

        private void CmbOperator_SelectionChanged(object sender, SelectionChangedEventArgs e) => UpdatePreview();

        private void BtnSelect_Click(object sender, RoutedEventArgs e)
        {
            string field = CmbField.Text.Trim();
            if (string.IsNullOrEmpty(field) && CmbField.SelectedItem != null)
            {
                field = CmbField.SelectedItem.ToString() ?? "";
            }

            if (string.IsNullOrEmpty(field))
            {
                MessageBox.Show("Please select or enter an attribute field name.", "Missing Field", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            string? targetLayerId = (CmbLayers.SelectedItem as ComboBoxItem)?.Tag as string;
            string op = (CmbOperator.SelectedItem as ComboBoxItem)?.Tag as string ?? "=";
            string val = CmbValue.Text.Trim();
            if (string.IsNullOrEmpty(val) && CmbValue.SelectedItem != null)
            {
                val = CmbValue.SelectedItem.ToString() ?? "";
            }

            _onSelectWithLayer?.Invoke(targetLayerId, field, op, val);
            Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e) => Close();
    }
}
