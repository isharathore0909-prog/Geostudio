using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using GeoStudio.Models;

namespace GeoStudio.UI.Views.Sidebar
{
    public partial class LayerSidebarView : UserControl
    {
        public LayerSidebarView()
        {
            InitializeComponent();
        }

        private MainWindow? Main => Application.Current.MainWindow as MainWindow;

        private void LayerItem_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ClickCount == 2)
            {
                // Do not trigger options if the user was double-clicking directly on the checkbox
                if (e.OriginalSource is DependencyObject dep && FindVisualParent<CheckBox>(dep) != null)
                {
                    return;
                }

                e.Handled = true;
                if (sender is FrameworkElement fe && fe.DataContext is LayerItem layer)
                {
                    Main?.OpenLayerOptions(layer);
                }
            }
        }

        private void MenuLayerOptions_Click(object s, RoutedEventArgs e)
        {
            if (s is FrameworkElement fe && fe.DataContext is LayerItem layer)
            {
                Main?.OpenLayerOptions(layer);
            }
        }

        private static T? FindVisualParent<T>(DependencyObject? child) where T : DependencyObject
        {
            while (child != null)
            {
                if (child is T parent) return parent;
                child = VisualTreeHelper.GetParent(child);
            }
            return null;
        }

        private void BtnSymbology_Click(object s, RoutedEventArgs e) => Main?.BtnSymbology_Click(s, e);
        private void MenuSymbology_Click(object s, RoutedEventArgs e) => Main?.BtnSymbology_Click(s, e);
        private void BtnZoomToLayer_Click(object s, RoutedEventArgs e) => Main?.BtnZoomToLayer_Click(s, e);
        private void BtnRemoveLayer_Click(object s, RoutedEventArgs e) => Main?.BtnRemoveLayer_Click(s, e);
        private void LayerCheckBox_Checked(object s, RoutedEventArgs e) => Main?.LayerCheckBox_Checked(s, e);
        private void LayerCheckBox_Unchecked(object s, RoutedEventArgs e) => Main?.LayerCheckBox_Unchecked(s, e);
        private void LayerOpacity_ValueChanged(object s, RoutedPropertyChangedEventArgs<double> e) => Main?.LayerOpacity_ValueChanged(s, e);

        private void TxtSearchLayers_TextChanged(object s, TextChangedEventArgs e) => Main?.TxtSearchLayers_TextChanged(s, e);
        private void BtnAddVector_Click(object s, RoutedEventArgs e) => Main?.BtnAddVector_Click(s, e);
        private void BtnAddRaster_Click(object s, RoutedEventArgs e) => Main?.BtnAddRaster_Click(s, e);
        private void BtnAddOsm_Click(object s, RoutedEventArgs e) => Main?.BtnAddOsm_Click(s, e);
        private void BtnToggleTelemetry_Click(object s, RoutedEventArgs e) => Main?.BtnToggleTelemetry_Click(s, e);
        private void MenuToggleGpu_Click(object s, RoutedEventArgs e) => Main?.MenuToggleGpu_Click(s, e);

        private void LidarClassItem_Click(object sender, RoutedEventArgs e)
        {
            // The CheckBox.Tag is bound to the parent LayerItem via RelativeSource.
            // Fall back to visual-tree search if Tag is not set (design-time or fallback).
            LayerItem? layer = null;
            if (sender is FrameworkElement fe)
            {
                layer = fe.Tag as LayerItem
                     ?? FindVisualParent<Border>(fe)?.DataContext as LayerItem;
            }
            if (layer == null) return;

            var activeClasses = System.Linq.Enumerable.ToList(
                System.Linq.Enumerable.Select(
                    System.Linq.Enumerable.Where(layer.LidarClasses, c => c.IsSelected),
                    c => c.ClassId));
            Main?.FilterLidarClasses(activeClasses);
        }

        private void BtnLidarTreeAll_Click(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.Tag is LayerItem layer)
            {
                foreach (var c in layer.LidarClasses) c.IsSelected = true;
                Main?.FilterLidarClasses(System.Linq.Enumerable.Select(layer.LidarClasses, c => c.ClassId));
            }
        }

        private void BtnLidarTreeGround_Click(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.Tag is LayerItem layer)
            {
                foreach (var c in layer.LidarClasses) c.IsSelected = (c.ClassId == 2 || c.ClassId == 8);
                Main?.FilterLidarClasses(new byte[] { 2, 8 });
            }
        }

        private void BtnLidarTreeVeg_Click(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.Tag is LayerItem layer)
            {
                foreach (var c in layer.LidarClasses) c.IsSelected = (c.ClassId >= 3 && c.ClassId <= 5);
                Main?.FilterLidarClasses(new byte[] { 3, 4, 5 });
            }
        }

        private void BtnLidarTreeBuildings_Click(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.Tag is LayerItem layer)
            {
                foreach (var c in layer.LidarClasses) c.IsSelected = (c.ClassId == 6);
                Main?.FilterLidarClasses(new byte[] { 6 });
            }
        }

        private void BtnLidarTreeNone_Click(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.Tag is LayerItem layer)
            {
                foreach (var c in layer.LidarClasses) c.IsSelected = false;
                Main?.FilterLidarClasses(System.Array.Empty<byte>());
            }
        }

        private void BtnMenuLidarExport_Click(object sender, RoutedEventArgs e)
        {
            LayerItem? layer = (sender as FrameworkElement)?.DataContext as LayerItem
                            ?? (sender as FrameworkElement)?.Tag as LayerItem
                            ?? Main?.Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            if (layer != null)
            {
                layer.IsClassificationActive = true;
                layer.IsLidarTreeExpanded = true;
                var sel = System.Linq.Enumerable.ToList(
                    System.Linq.Enumerable.Select(
                        System.Linq.Enumerable.Where(layer.LidarClasses, c => c.IsSelected),
                        c => c.ClassId));
                Main?.OpenLidarFilterDialog(sel);
            }
        }

        private void BtnLidarTreeExport_Click(object sender, RoutedEventArgs e)
        {
            LayerItem? layer = (sender as FrameworkElement)?.DataContext as LayerItem
                            ?? (sender as FrameworkElement)?.Tag as LayerItem
                            ?? Main?.Layers.FirstOrDefault(l => l.Type == LayerType.PointCloud);
            if (layer != null)
            {
                var sel = System.Linq.Enumerable.ToList(
                    System.Linq.Enumerable.Select(
                        System.Linq.Enumerable.Where(layer.LidarClasses, c => c.IsSelected),
                        c => c.ClassId));
                Main?.OpenLidarFilterDialog(sel);
            }
        }
    }
}
