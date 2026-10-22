using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Views.Sidebar
{
    public partial class LayerSidebarView : UserControl
    {
        public LayerSidebarView()
        {
            InitializeComponent();
        }

        private MainWindow? Main => Application.Current.MainWindow as MainWindow;

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
    }
}
