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
    }
}
