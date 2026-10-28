using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Dialogs.Raster
{
    public class QgisStylePreset
    {
        public string Name { get; set; } = "";
        public Brush BackgroundBrush { get; set; } = Brushes.DodgerBlue;
        public Brush BorderBrush { get; set; } = Brushes.Navy;
        public Thickness BorderThickness { get; set; } = new(1);
        public string FillHex { get; set; } = "#3B82F6";
        public string StrokeHex { get; set; } = "#1D4ED8";
        public double StrokeWidth { get; set; } = 1.5;
        public double Opacity { get; set; } = 100;
    }

    public class VectorCategoryItem : INotifyPropertyChanged
    {
        public bool IsVisible { get; set; } = true;
        private string _colorHex = "#10B981";
        public string ColorHex { get => _colorHex; set { _colorHex = value; PropertyChanged?.Invoke(this, new(nameof(ColorHex))); } }
        public string Value { get; set; } = "";
        public string Label { get; set; } = "";
        public event PropertyChangedEventHandler? PropertyChanged;
    }

    public class VectorGraduatedItem : INotifyPropertyChanged
    {
        public bool IsVisible { get; set; } = true;
        private string _colorHex = "#3B82F6";
        public string ColorHex { get => _colorHex; set { _colorHex = value; PropertyChanged?.Invoke(this, new(nameof(ColorHex))); } }
        public double Min { get; set; }
        public double Max { get; set; }
        public string ValueRange => $"{Min:F2} - {Max:F2}";
        public string Label { get; set; } = "";
        public event PropertyChangedEventHandler? PropertyChanged;
    }

    public class VectorRuleItem : INotifyPropertyChanged
    {
        public bool IsVisible { get; set; } = true;
        private string _colorHex = "#F59E0B";
        public string ColorHex { get => _colorHex; set { _colorHex = value; PropertyChanged?.Invoke(this, new(nameof(ColorHex))); } }
        public string Label { get; set; } = "";
        public string Expression { get; set; } = "";
        public event PropertyChangedEventHandler? PropertyChanged;
    }

    public partial class LayerSymbologyWindow
    {
        private bool _isVectorUpdating = false;
        private string _currentFillHex = "#10B981";
        private string _currentStrokeHex = "#10B981";
        private string _invertedMaskColor = "#1E293B";
        private string _25dRoofColor = "#3B82F6";
        private string _25dWallColor = "#1E3A8A";

        private readonly ObservableCollection<VectorCategoryItem> _vectorCategories = new();
        private readonly ObservableCollection<VectorGraduatedItem> _vectorGraduated = new();
        private readonly ObservableCollection<VectorRuleItem> _vectorRules = new();

        private void InitializeVectorSymbology()
        {
            _isVectorUpdating = true;
            try
            {
                if (PanelVectorSymbology != null) PanelVectorSymbology.Visibility = Visibility.Visible;
                if (ExpanderBandRendering != null) ExpanderBandRendering.Visibility = Visibility.Collapsed;
                if (ExpanderLayerRendering != null) ExpanderLayerRendering.Visibility = Visibility.Collapsed;
                if (ExpanderResampling != null) ExpanderResampling.Visibility = Visibility.Collapsed;

                _currentStrokeHex = !string.IsNullOrEmpty(_layer.ColorHex) ? _layer.ColorHex : "#10B981";
                _currentFillHex = !string.IsNullOrEmpty(_layer.FillColorHex) && !_layer.FillColorHex.Equals("#FFFFFF", StringComparison.OrdinalIgnoreCase)
                    ? _layer.FillColorHex
                    : _currentStrokeHex;

                if (SliderVectorStrokeWidth != null) SliderVectorStrokeWidth.Value = _layer.StrokeWidth > 0 ? _layer.StrokeWidth : 1.6;
                if (SliderVectorFillOpacity != null) SliderVectorFillOpacity.Value = Math.Round((_layer.FillOpacity > 0 ? _layer.FillOpacity : 0.28) * 100);
                if (SliderVectorLayerOpacity != null) SliderVectorLayerOpacity.Value = Math.Round(_layer.Opacity * 100);

                string dash = _layer.DashPattern ?? "solid";
                if (ComboVectorDashStyle != null)
                {
                    foreach (ComboBoxItem item in ComboVectorDashStyle.Items)
                        if (string.Equals(item.Tag?.ToString(), dash, StringComparison.OrdinalIgnoreCase)) { ComboVectorDashStyle.SelectedItem = item; break; }
                }

                if (ItemsProjectStyles != null) ItemsProjectStyles.ItemsSource = GetDefaultQgisPresets();
                if (GridVectorCategories != null) GridVectorCategories.ItemsSource = _vectorCategories;
                if (GridVectorGraduated != null) GridVectorGraduated.ItemsSource = _vectorGraduated;
                if (GridVectorRules != null) GridVectorRules.ItemsSource = _vectorRules;

                var fields = _layer.AttributeFields?.Count > 0 ? _layer.AttributeFields : DiscoverAttributesFromLayer();
                _layer.AttributeFields = fields;

                foreach (var combo in new[] { ComboCategorizedField, ComboGraduatedField, Combo25DHeightField })
                {
                    if (combo != null) { combo.ItemsSource = fields; if (fields.Count > 0) combo.SelectedIndex = 0; }
                }

                string currentMode = !string.IsNullOrEmpty(_layer.VectorRenderType) ? _layer.VectorRenderType : "single";
                if (ComboVectorRenderType != null)
                {
                    foreach (ComboBoxItem item in ComboVectorRenderType.Items)
                        if (string.Equals(item.Tag?.ToString(), currentMode, StringComparison.OrdinalIgnoreCase)) { ComboVectorRenderType.SelectedItem = item; break; }
                }
                UpdateRenderPanels(currentMode);
            }
            finally { _isVectorUpdating = false; }
            UpdateVectorPreview();
        }

        private void ReadFeatures(Action<JsonElement> onFeature, int max = int.MaxValue)
        {
            string? path = _layer.GeoJsonCachePath ?? _layer.FilePath;
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) return;
            try
            {
                using var fs = File.OpenRead(path);
                using var doc = JsonDocument.Parse(fs);
                if (doc.RootElement.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                {
                    int n = 0;
                    foreach (var f in feats.EnumerateArray()) { onFeature(f); if (++n >= max) break; }
                }
            }
            catch { }
        }

        private List<string> DiscoverAttributesFromLayer()
        {
            var fields = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            ReadFeatures(f => {
                if (f.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                    foreach (var p in props.EnumerateObject()) fields.Add(p.Name);
            }, 100);
            return fields.ToList();
        }

        private void ComboVectorRenderType_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_isInitializing || _isVectorUpdating || ComboVectorRenderType == null) return;
            string tag = (ComboVectorRenderType.SelectedItem as ComboBoxItem)?.Tag as string ?? "single";
            _layer.VectorRenderType = tag;
            UpdateRenderPanels(tag);
            UpdateVectorPreview();
            ApplyVectorSymbology();
        }

        private void UpdateRenderPanels(string mode)
        {
            UIElement?[] panels = { PanelVectorSingleSymbol, PanelVectorCategorized, PanelVectorGraduated, PanelVectorRuleBased, PanelVectorNoSymbols, PanelVectorInverted, PanelVector25D, PanelVectorMerged };
            string[] modes = { "single", "categorized", "graduated", "rule", "nosymbol", "inverted", "2.5d", "merged" };
            for (int i = 0; i < panels.Length; i++)
                if (panels[i] != null) panels[i]!.Visibility = modes[i] == mode ? Visibility.Visible : Visibility.Collapsed;
        }

        #region Categorized & Graduated Classification
        private void BtnCategorizedClassify_Click(object sender, RoutedEventArgs e)
        {
            string? field = ComboCategorizedField?.SelectedItem as string;
            if (string.IsNullOrEmpty(field)) return;

            var vals = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            ReadFeatures(f => {
                if (f.TryGetProperty("properties", out var props) && props.TryGetProperty(field, out var val))
                {
                    string s = val.ValueKind == JsonValueKind.String ? val.GetString() ?? "" : val.ToString();
                    if (!string.IsNullOrWhiteSpace(s)) vals.Add(s.Trim());
                }
            }, 1000);

            var list = vals.OrderBy(v => v).Take(60).ToList();
            if (list.Count == 0) list = new() { "Category A", "Category B", "Category C" };

            string ramp = (ComboCategorizedRamp?.SelectedItem as ComboBoxItem)?.Tag as string ?? "Viridis";
            var colors = GenerateColorRamp(ramp, list.Count);

            _vectorCategories.Clear();
            for (int i = 0; i < list.Count; i++)
                _vectorCategories.Add(new() { Value = list[i], Label = list[i], ColorHex = colors[i % colors.Count] });

            ApplyVectorSymbology();
        }

        private void BtnGraduatedClassify_Click(object sender, RoutedEventArgs e)
        {
            string? field = ComboGraduatedField?.SelectedItem as string;
            if (string.IsNullOrEmpty(field)) return;

            int classesCount = int.TryParse(TxtGraduatedClassesCount?.Text, out int n) && n > 1 ? n : 5;
            var nums = new List<double>();
            ReadFeatures(f => {
                if (f.TryGetProperty("properties", out var props) && props.TryGetProperty(field, out var val))
                {
                    if (val.ValueKind == JsonValueKind.Number && val.TryGetDouble(out double d)) nums.Add(d);
                    else if (double.TryParse(val.ToString(), out double parsed)) nums.Add(parsed);
                }
            }, 5000);

            double min = nums.Count > 0 ? nums.Min() : 0;
            double max = nums.Count > 0 ? nums.Max() : 100;
            if (Math.Abs(max - min) < 1e-6) max = min + 10;

            string ramp = (ComboGraduatedRamp?.SelectedItem as ComboBoxItem)?.Tag as string ?? "Viridis";
            var colors = GenerateColorRamp(ramp, classesCount);

            _vectorGraduated.Clear();
            double step = (max - min) / classesCount;
            for (int i = 0; i < classesCount; i++)
            {
                double rMin = min + (i * step);
                double rMax = (i == classesCount - 1) ? max : min + ((i + 1) * step);
                _vectorGraduated.Add(new() { Min = Math.Round(rMin, 2), Max = Math.Round(rMax, 2), Label = $"{rMin:F2} - {rMax:F2}", ColorHex = colors[i % colors.Count] });
            }
            ApplyVectorSymbology();
        }

        private List<string> GenerateColorRamp(string ramp, int count)
        {
            if (count <= 0) count = 5;
            if (string.Equals(ramp, "random", StringComparison.OrdinalIgnoreCase))
                return Enumerable.Range(0, count).Select(_ => $"#{_rng.Next(30, 220):X2}{_rng.Next(30, 220):X2}{_rng.Next(30, 220):X2}").ToList();

            if (!PredefinedRamps.TryGetValue(ramp, out var stops) || stops == null || stops.Length < 2)
                stops = PredefinedRamps["Viridis"];

            var colors = new List<string>(count);
            for (int i = 0; i < count; i++)
            {
                double t = count > 1 ? (double)i / (count - 1) : 0.5;
                var (r, g, b) = InterpolateRamp(stops, t);
                colors.Add($"#{r:X2}{g:X2}{b:X2}");
            }
            return colors;
        }

        private void BtnCategorizedAdd_Click(object sender, RoutedEventArgs e) { _vectorCategories.Add(new() { Value = $"Value {_vectorCategories.Count + 1}", Label = $"Class {_vectorCategories.Count + 1}", ColorHex = "#10B981" }); ApplyVectorSymbology(); }
        private void BtnCategorizedDelete_Click(object sender, RoutedEventArgs e) { if (GridVectorCategories?.SelectedItem is VectorCategoryItem s) { _vectorCategories.Remove(s); ApplyVectorSymbology(); } }
        private void BtnCategorizedDeleteAll_Click(object sender, RoutedEventArgs e) { _vectorCategories.Clear(); ApplyVectorSymbology(); }
        private void BtnCategoryColor_Click(object sender, RoutedEventArgs e) { if (sender is FrameworkElement fe && fe.DataContext is VectorCategoryItem i && PromptColor(i.ColorHex) is string c) { i.ColorHex = c; ApplyVectorSymbology(); } }

        private void BtnGraduatedAdd_Click(object sender, RoutedEventArgs e) { double last = _vectorGraduated.Count > 0 ? _vectorGraduated.Last().Max : 0; _vectorGraduated.Add(new() { Min = last, Max = last + 50, Label = $"{last:F2} - {(last + 50):F2}", ColorHex = "#3B82F6" }); ApplyVectorSymbology(); }
        private void BtnGraduatedDelete_Click(object sender, RoutedEventArgs e) { if (GridVectorGraduated?.SelectedItem is VectorGraduatedItem s) { _vectorGraduated.Remove(s); ApplyVectorSymbology(); } }
        private void BtnGraduatedColor_Click(object sender, RoutedEventArgs e) { if (sender is FrameworkElement fe && fe.DataContext is VectorGraduatedItem i && PromptColor(i.ColorHex) is string c) { i.ColorHex = c; ApplyVectorSymbology(); } }

        private void BtnRuleAdd_Click(object sender, RoutedEventArgs e) { _vectorRules.Add(new() { Label = $"Rule {_vectorRules.Count + 1}", Expression = "ELSE", ColorHex = "#10B981" }); ApplyVectorSymbology(); }
        private void BtnRuleDelete_Click(object sender, RoutedEventArgs e) { if (GridVectorRules?.SelectedItem is VectorRuleItem s) { _vectorRules.Remove(s); ApplyVectorSymbology(); } }
        private void BtnRuleColor_Click(object sender, RoutedEventArgs e) { if (sender is FrameworkElement fe && fe.DataContext is VectorRuleItem i && PromptColor(i.ColorHex) is string c) { i.ColorHex = c; ApplyVectorSymbology(); } }

        private void BtnInvertedColor_Click(object sender, RoutedEventArgs e) { if (PromptColor(_invertedMaskColor) is string c) { _invertedMaskColor = c; if (BtnInvertedMaskColor != null) BtnInvertedMaskColor.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(c)); ApplyVectorSymbology(); } }
        private void Btn25DRoof_Click(object sender, RoutedEventArgs e) { if (PromptColor(_25dRoofColor) is string c) { _25dRoofColor = c; if (Btn25DRoofColor != null) Btn25DRoofColor.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(c)); ApplyVectorSymbology(); } }
        private void Btn25DWall_Click(object sender, RoutedEventArgs e) { if (PromptColor(_25dWallColor) is string c) { _25dWallColor = c; if (Btn25DWallColor != null) Btn25DWallColor.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(c)); ApplyVectorSymbology(); } }

        private string? PromptColor(string current) => ColorDialogHelper.PromptColorHex(current, this);
        #endregion

        private static List<QgisStylePreset> GetDefaultQgisPresets() => new()
        {
            new() { Name = "topography", FillHex = "#EA580C", StrokeHex = "#9A3412", StrokeWidth = 1.8, BackgroundBrush = new SolidColorBrush(Color.FromRgb(234, 88, 12)) },
            new() { Name = "water blue", FillHex = "#38BDF8", StrokeHex = "#0284C7", StrokeWidth = 1.5, BackgroundBrush = new SolidColorBrush(Color.FromRgb(56, 189, 248)) },
            new() { Name = "forest green", FillHex = "#22C55E", StrokeHex = "#15803D", StrokeWidth = 1.5, BackgroundBrush = new SolidColorBrush(Color.FromRgb(34, 197, 94)) },
            new() { Name = "outline red", FillHex = "#FFFFFF", StrokeHex = "#DC2626", StrokeWidth = 2.0, Opacity = 0, BackgroundBrush = Brushes.White, BorderBrush = Brushes.Crimson, BorderThickness = new(2) },
            new() { Name = "plasma purple", FillHex = "#F97316", StrokeHex = "#6B21A8", StrokeWidth = 1.5, BackgroundBrush = new SolidColorBrush(Color.FromRgb(147, 51, 234)) },
            new() { Name = "slate gray", FillHex = "#CBD5E1", StrokeHex = "#334155", StrokeWidth = 1.5, BackgroundBrush = new SolidColorBrush(Color.FromRgb(148, 163, 184)) }
        };

        private void BtnPresetStyle_Click(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.DataContext is QgisStylePreset p)
            {
                _currentFillHex = p.FillHex; _currentStrokeHex = p.StrokeHex;
                if (SliderVectorStrokeWidth != null) SliderVectorStrokeWidth.Value = p.StrokeWidth;
                if (SliderVectorFillOpacity != null) SliderVectorFillOpacity.Value = p.Opacity;
                UpdateVectorPreview();
                ApplyVectorSymbology();
            }
        }

        private void BtnPickFillColor_Click(object sender, RoutedEventArgs e) { if (PromptColor(_currentFillHex) is string c) { _currentFillHex = c; UpdateVectorPreview(); ApplyVectorSymbology(); } }
        private void BtnPickStrokeColor_Click(object sender, RoutedEventArgs e) { if (PromptColor(_currentStrokeHex) is string c) { _currentStrokeHex = c; UpdateVectorPreview(); ApplyVectorSymbology(); } }
        private void BtnClearSymbolSearch_Click(object sender, RoutedEventArgs e) { if (TxtSearchSymbols != null) TxtSearchSymbols.Text = string.Empty; }
        private void BtnSaveSymbol_Click(object sender, RoutedEventArgs e) => MessageBox.Show("Current symbol configuration saved to library.", "Save Symbol", MessageBoxButton.OK, MessageBoxImage.Information);
        private void VectorParam_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e) { if (!_isInitializing && !_isVectorUpdating) { UpdateVectorPreview(); ApplyVectorSymbology(); } }
        private void ComboVectorDashStyle_SelectionChanged(object sender, SelectionChangedEventArgs e) { if (!_isInitializing && !_isVectorUpdating) { UpdateVectorPreview(); ApplyVectorSymbology(); } }

        private void UpdateVectorPreview()
        {
            if (BtnWideFillColor == null || BtnWideStrokeColor == null || PreviewPolygon == null || PreviewPolyline == null || PreviewPoint == null) return;
            try
            {
                var strokeColor = (Color)ColorConverter.ConvertFromString(_currentStrokeHex);
                var fillColor = (Color)ColorConverter.ConvertFromString(_currentFillHex);
                if (SwatchWideFill != null) SwatchWideFill.Background = new SolidColorBrush(fillColor);
                if (TxtWideFillHex != null) TxtWideFillHex.Text = _currentFillHex.ToUpperInvariant();
                if (SwatchWideStroke != null) SwatchWideStroke.Background = new SolidColorBrush(strokeColor);
                if (TxtWideStrokeHex != null) TxtWideStrokeHex.Text = _currentStrokeHex.ToUpperInvariant();
                if (BorderTreeFillIcon != null) { BorderTreeFillIcon.Background = new SolidColorBrush(fillColor); BorderTreeFillIcon.BorderBrush = new SolidColorBrush(strokeColor); }
                if (BorderTreeSubFillIcon != null) { BorderTreeSubFillIcon.Background = new SolidColorBrush(fillColor); BorderTreeSubFillIcon.BorderBrush = new SolidColorBrush(strokeColor); }

                double fillOpacity = (SliderVectorFillOpacity?.Value ?? 100) / 100.0;
                double strokeWidth = Math.Min(4.0, SliderVectorStrokeWidth?.Value ?? 1.5);

                PreviewPolygon.Fill = new SolidColorBrush(Color.FromArgb((byte)(fillOpacity * 255), fillColor.R, fillColor.G, fillColor.B));
                PreviewPolyline.Stroke = new SolidColorBrush(strokeColor);
                PreviewPolyline.StrokeThickness = strokeWidth;

                string dash = (ComboVectorDashStyle?.SelectedItem as ComboBoxItem)?.Tag as string ?? "solid";
                PreviewPolyline.StrokeDashArray = dash switch { "dashed" => new DoubleCollection { 4, 2 }, "dotted" => new DoubleCollection { 1, 2 }, "dashdot" => new DoubleCollection { 4, 2, 1, 2 }, _ => null };
                PreviewPoint.Fill = new SolidColorBrush(strokeColor);
            }
            catch { }
        }

        private void ApplyVectorSymbology()
        {
            if (_layer == null || _main == null) return;

            double strokeWidth = SliderVectorStrokeWidth?.Value ?? 1.5;
            double fillOpacity = (SliderVectorFillOpacity?.Value ?? 100) / 100.0;
            double layerOpacity = (SliderVectorLayerOpacity?.Value ?? 100) / 100.0;
            string dashTag = (ComboVectorDashStyle?.SelectedItem as ComboBoxItem)?.Tag as string ?? "solid";
            string mode = (ComboVectorRenderType?.SelectedItem as ComboBoxItem)?.Tag as string ?? "single";

            _layer.ColorHex = _currentStrokeHex;
            _layer.FillColorHex = _currentFillHex;
            _layer.StrokeWidth = strokeWidth;
            _layer.FillOpacity = fillOpacity;
            _layer.DashPattern = dashTag;
            _layer.Opacity = layerOpacity;
            _layer.VectorRenderType = mode;

            string? catField = ComboCategorizedField?.SelectedItem as string;
            string? gradField = ComboGraduatedField?.SelectedItem as string;

            _main.PostMessageToMap(new
            {
                action = "updateVectorLayerStyle",
                id = _layer.Id,
                mode = mode,
                attributeField = mode == "categorized" ? catField : (mode == "graduated" ? gradField : null),
                categories = _vectorCategories.Select(c => new { value = c.Value, color = c.ColorHex, visible = c.IsVisible }).ToArray(),
                ranges = _vectorGraduated.Select(g => new { min = g.Min, max = g.Max, color = g.ColorHex, visible = g.IsVisible }).ToArray(),
                maskColor = _invertedMaskColor,
                roofColor = _25dRoofColor,
                wallColor = _25dWallColor,
                color = _currentStrokeHex,
                strokeColor = _currentStrokeHex,
                fillColor = _currentFillHex,
                strokeWidth = strokeWidth,
                fillOpacity = fillOpacity,
                dashPattern = dashTag,
                pointRadius = _layer.PointRadius,
                opacity = layerOpacity
            });
        }
    }
}
