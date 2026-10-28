using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using GeoStudio.Raster.Services;

namespace GeoStudio.UI.Dialogs.Raster
{
    public partial class LayerSymbologyWindow
    {
        private void BtnColorPick_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.DataContext is RasterClassItem item)
            {
                string? hex = GeoStudio.UI.Services.ColorDialogHelper.PromptColorHex(item.ColorHex, this);
                if (!string.IsNullOrEmpty(hex))
                {
                    var c = (Color)ColorConverter.ConvertFromString(hex);
                    item.R = c.R; item.G = c.G; item.B = c.B; item.A = 255;
                    item.ColorHex = hex;

                    int idx = _classes.IndexOf(item);
                    if (idx >= 0)
                    {
                        _classes.RemoveAt(idx);
                        _classes.Insert(idx, item);
                    }
                }
            }
        }

        private void SliderBrightness_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (TxtBrightness != null && SliderBrightness != null)
                TxtBrightness.Text = $"{SliderBrightness.Value:F0}";
            DispatchLiveLayerRendering();
        }

        private void SliderContrast_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (TxtContrast != null && SliderContrast != null)
                TxtContrast.Text = $"{SliderContrast.Value:F0}";
            DispatchLiveLayerRendering();
        }

        private void SliderGamma_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (TxtGamma != null && SliderGamma != null)
                TxtGamma.Text = $"{SliderGamma.Value:F2}";
            DispatchLiveLayerRendering();
        }

        private void SliderSaturation_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (TxtSaturation != null && SliderSaturation != null)
                TxtSaturation.Text = $"{SliderSaturation.Value:F0}";
            DispatchLiveLayerRendering();
        }

        private void ComboBlendMode_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            DispatchLiveLayerRendering();
        }

        private void ChkInvertColors_Click(object sender, RoutedEventArgs e)
        {
            DispatchLiveLayerRendering();
        }

        private void ComboGrayscale_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            DispatchLiveLayerRendering();
        }

        private void BtnResetRendering_Click(object sender, RoutedEventArgs e)
        {
            if (SliderBrightness != null) SliderBrightness.Value = 0;
            if (SliderContrast != null) SliderContrast.Value = 0;
            if (SliderGamma != null) SliderGamma.Value = 1.0;
            if (SliderSaturation != null) SliderSaturation.Value = 0;
            if (ChkInvertColors != null) ChkInvertColors.IsChecked = false;
            if (ComboBlendMode != null) ComboBlendMode.SelectedIndex = 0;
            if (ComboGrayscale != null) ComboGrayscale.SelectedIndex = 0;
            DispatchLiveLayerRendering();
        }

        private void DispatchLiveLayerRendering()
        {
            if (!IsLoaded || _main == null) return;
            string blend = (ComboBlendMode?.SelectedItem as ComboBoxItem)?.Content as string ?? "Normal";
            string filter = BuildCssFilterString();
            _main.PostMessageToMap(new
            {
                action = "updateRasterLayerRendering",
                blendMode = blend,
                filter = filter
            });
        }

        private string BuildCssFilterString()
        {
            double br = 1.0 + ((SliderBrightness?.Value ?? 0) / 100.0);
            double ct = 1.0 + ((SliderContrast?.Value ?? 0) / 100.0);
            double sat = 1.0 + ((SliderSaturation?.Value ?? 0) / 100.0);
            double gamma = SliderGamma?.Value ?? 1.0;
            bool inv = ChkInvertColors?.IsChecked == true;
            string gray = (ComboGrayscale?.SelectedItem as ComboBoxItem)?.Content as string ?? "Off";

            if (Math.Abs(gamma - 1.0) > 0.01)
            {
                br *= Math.Pow(1.25, gamma - 1.0);
            }

            string filter = $"brightness({Math.Max(0.01, br):F2}) contrast({Math.Max(0.01, ct):F2}) saturate({Math.Max(0, sat):F2})";
            if (inv) filter += " invert(100%)";
            if (gray != "Off") filter += " grayscale(100%)";
            return filter;
        }
    }
}
