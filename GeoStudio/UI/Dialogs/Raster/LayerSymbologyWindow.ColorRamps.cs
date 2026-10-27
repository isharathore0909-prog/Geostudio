using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Raster.Services;

namespace GeoStudio.UI.Dialogs.Raster
{
    public partial class LayerSymbologyWindow
    {
        private static readonly Random _rng = new();

        private static readonly Dictionary<string, (byte R, byte G, byte B)[]> PredefinedRamps = new(StringComparer.OrdinalIgnoreCase)
        {
            ["Blues"] = new[] { ((byte)247, (byte)251, (byte)255), ((byte)8, (byte)48, (byte)107) },
            ["Cividis"] = new[] { ((byte)0, (byte)32, (byte)77), ((byte)124, (byte)123, (byte)120), ((byte)255, (byte)234, (byte)70) },
            ["Greens"] = new[] { ((byte)247, (byte)252, (byte)245), ((byte)0, (byte)68, (byte)27) },
            ["Greys"] = new[] { ((byte)255, (byte)255, (byte)255), ((byte)0, (byte)0, (byte)0) },
            ["Magma"] = new[] { ((byte)0, (byte)0, (byte)4), ((byte)182, (byte)54, (byte)121), ((byte)251, (byte)136, (byte)97), ((byte)252, (byte)253, (byte)191) },
            ["Mako"] = new[] { ((byte)11, (byte)4, (byte)5), ((byte)59, (byte)154, (byte)178), ((byte)222, (byte)245, (byte)229) },
            ["RdGy"] = new[] { ((byte)178, (byte)24, (byte)43), ((byte)255, (byte)255, (byte)255), ((byte)77, (byte)77, (byte)77) },
            ["Reds"] = new[] { ((byte)255, (byte)245, (byte)240), ((byte)103, (byte)0, (byte)13) },
            ["Rocket"] = new[] { ((byte)3, (byte)5, (byte)26), ((byte)230, (byte)81, (byte)100), ((byte)250, (byte)235, (byte)221) },
            ["Spectral"] = new[] { ((byte)158, (byte)1, (byte)66), ((byte)254, (byte)224, (byte)139), ((byte)94, (byte)79, (byte)162) },
            ["Turbo"] = new[] { ((byte)48, (byte)18, (byte)59), ((byte)40, (byte)187, (byte)236), ((byte)162, (byte)252, (byte)60), ((byte)251, (byte)128, (byte)34), ((byte)122, (byte)4, (byte)3) },
            ["Viridis"] = new[] { ((byte)68, (byte)1, (byte)84), ((byte)33, (byte)144, (byte)140), ((byte)253, (byte)231, (byte)37) }
        };

        private void ComboColorRamp_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboColorRamp?.SelectedItem is not ComboBoxItem item) return;
            string tag = item.Tag as string ?? "Viridis";

            if (tag == "shuffle")
            {
                ShuffleRandomColors();
                return;
            }

            ApplyColorRamp(tag, ChkInvertRamp?.IsChecked == true);
        }

        private void ChkInvertRamp_Click(object sender, RoutedEventArgs e)
        {
            if (ComboColorRamp?.SelectedItem is ComboBoxItem item)
            {
                string tag = item.Tag as string ?? "Viridis";
                ApplyColorRamp(tag, ChkInvertRamp.IsChecked == true);
            }
        }

        private void ApplyColorRamp(string rampName, bool invert)
        {
            if (_classes.Count == 0) return;

            if (rampName == "random")
            {
                ShuffleRandomColors();
                return;
            }

            if (rampName == "lulc22")
            {
                _classes.Clear();
                foreach (var c in RasterSymbologyService.GetLulc22Preset()) _classes.Add(c);
                return;
            }

            if (rampName == "dw9")
            {
                _classes.Clear();
                foreach (var c in RasterSymbologyService.GetDynamicWorldPreset()) _classes.Add(c);
                return;
            }

            if (!PredefinedRamps.TryGetValue(rampName, out var stops) || stops == null || stops.Length < 2)
                stops = PredefinedRamps["Viridis"];

            if (invert)
            {
                stops = stops.Reverse().ToArray();
            }

            int n = _classes.Count;
            for (int i = 0; i < n; i++)
            {
                var item = _classes[i];
                if (item.Value == 0) continue; // Keep background transparent

                double t = n > 1 ? (double)i / (n - 1) : 0.5;
                var (r, g, b) = InterpolateRamp(stops, t);

                item.R = r;
                item.G = g;
                item.B = b;
                item.A = 255;
                item.ColorHex = $"#{r:X2}{g:X2}{b:X2}";
            }

            // Refresh DataGrid
            var snapshot = _classes.ToList();
            _classes.Clear();
            foreach (var c in snapshot) _classes.Add(c);
        }

        private static (byte R, byte G, byte B) InterpolateRamp((byte R, byte G, byte B)[] stops, double t)
        {
            t = Math.Clamp(t, 0.0, 1.0);
            double scaled = t * (stops.Length - 1);
            int idx = (int)Math.Floor(scaled);
            int nextIdx = Math.Min(idx + 1, stops.Length - 1);
            double frac = scaled - idx;

            byte r = (byte)(stops[idx].R + frac * (stops[nextIdx].R - stops[idx].R));
            byte g = (byte)(stops[idx].G + frac * (stops[nextIdx].G - stops[idx].G));
            byte b = (byte)(stops[idx].B + frac * (stops[nextIdx].B - stops[idx].B));
            return (r, g, b);
        }

        private void ShuffleRandomColors()
        {
            foreach (var item in _classes)
            {
                if (item.Value == 0) continue;
                byte r = (byte)_rng.Next(30, 245);
                byte g = (byte)_rng.Next(30, 245);
                byte b = (byte)_rng.Next(30, 245);
                item.R = r;
                item.G = g;
                item.B = b;
                item.A = 255;
                item.ColorHex = $"#{r:X2}{g:X2}{b:X2}";
            }

            var snapshot = _classes.ToList();
            _classes.Clear();
            foreach (var c in snapshot) _classes.Add(c);
        }

        private void BtnAddClass_Click(object sender, RoutedEventArgs e)
        {
            int nextVal = _classes.Count > 0 ? _classes.Max(c => c.Value) + 1 : 1;
            byte r = (byte)_rng.Next(40, 230);
            byte g = (byte)_rng.Next(40, 230);
            byte b = (byte)_rng.Next(40, 230);
            _classes.Add(new RasterClassItem
            {
                Value = nextVal,
                Label = $"Class {nextVal}",
                ColorHex = $"#{r:X2}{g:X2}{b:X2}",
                R = r, G = g, B = b, A = 255,
                IsVisible = true
            });
        }

        private void BtnRemoveClass_Click(object sender, RoutedEventArgs e)
        {
            if (GridClasses.SelectedItem is RasterClassItem selected)
            {
                _classes.Remove(selected);
            }
        }

        private void PickSingleColor()
        {
            byte r = 59, g = 130, b = 246;
            var cc = new CHOOSECOLOR();
            cc.lStructSize = System.Runtime.InteropServices.Marshal.SizeOf(cc);
            cc.hwndOwner = new System.Windows.Interop.WindowInteropHelper(this).Handle;
            cc.rgbResult = r | (g << 8) | (b << 16);
            cc.Flags = 0x00000001 | 0x00000002;

            var handle = System.Runtime.InteropServices.GCHandle.Alloc(_customColors, System.Runtime.InteropServices.GCHandleType.Pinned);
            try
            {
                cc.lpCustColors = handle.AddrOfPinnedObject();
                if (ChooseColor(ref cc))
                {
                    r = (byte)(cc.rgbResult & 0xFF);
                    g = (byte)((cc.rgbResult >> 8) & 0xFF);
                    b = (byte)((cc.rgbResult >> 16) & 0xFF);
                    BtnSingleColorPick.Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(r, g, b));
                    BtnSingleColorPick.Content = $"#{r:X2}{g:X2}{b:X2}";
                }
            }
            finally
            {
                handle.Free();
            }
        }
    }
}
