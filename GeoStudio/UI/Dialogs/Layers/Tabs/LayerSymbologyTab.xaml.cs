using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.Raster.Services;

namespace GeoStudio.UI.Dialogs.Layers.Tabs
{
    public partial class LayerSymbologyTab : UserControl
    {
        private MainWindow? _main;
        private LayerItem? _layer;
        private readonly ObservableCollection<RasterClassItem> _classes = new();

        public LayerSymbologyTab()
        {
            InitializeComponent();
            GridClasses.ItemsSource = _classes;
        }

        public void BindLayer(MainWindow main, LayerItem layer)
        {
            _main = main;
            _layer = layer;
            LoadDefaultPreset();
        }

        public void LoadDefaultPreset()
        {
            _classes.Clear();
            var preset = RasterSymbologyService.GetLulc22Preset();
            if (preset != null)
            {
                foreach (var item in preset) _classes.Add(item);
            }
        }

        private void ComboColorRamp_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboColorRamp?.SelectedItem is ComboBoxItem item)
            {
                string tag = item.Tag?.ToString() ?? "Viridis";
                _classes.Clear();
                var classes = tag == "dw9" ? RasterSymbologyService.GetDynamicWorldPreset() : RasterSymbologyService.GetLulc22Preset();
                if (classes != null)
                {
                    foreach (var c in classes) _classes.Add(c);
                }
            }
        }

        private void BtnClassify_Click(object sender, RoutedEventArgs e)
        {
            LoadDefaultPreset();
            MessageBox.Show("Classified values successfully updated.", "Symbology", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void BtnOpenFullSymbology_Click(object sender, RoutedEventArgs e)
        {
            if (_main != null && _layer != null)
            {
                var dlg = new Raster.LayerSymbologyWindow(_main, _layer);
                dlg.ShowDialog();
            }
        }
    }
}
