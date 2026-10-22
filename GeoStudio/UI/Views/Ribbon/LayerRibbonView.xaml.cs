using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Views.Ribbon
{
    public partial class LayerRibbonView : UserControl
    {
        public LayerRibbonView()
        {
            InitializeComponent();
        }

        private MainWindow? Main => Application.Current.MainWindow as MainWindow;

        public void SwitchTab(string tabName)
        {
            if (PanelRibbonData != null)
                PanelRibbonData.Visibility = (tabName == "Data" || tabName == "Layer") ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonStyle != null)
                PanelRibbonStyle.Visibility = tabName == "Style" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonEdit != null)
                PanelRibbonEdit.Visibility = tabName == "Edit" ? Visibility.Visible : Visibility.Collapsed;
        }

        private void BtnAddVector_Click(object s, RoutedEventArgs e) => Main?.BtnAddVector_Click(s, e);
        private void BtnAddRaster_Click(object s, RoutedEventArgs e) => Main?.BtnAddRaster_Click(s, e);
        private void BtnAddLidar_Click(object s, RoutedEventArgs e) => Main?.BtnAddLidar_Click(s, e);
        private void BtnAddOsm_Click(object s, RoutedEventArgs e) => Main?.BtnAddOsm_Click(s, e);
        private void BtnDatabase_Click(object s, RoutedEventArgs e) => Main?.BtnDatabase_Click(s, e);
        private void MenuRemoveLayer_Click(object s, RoutedEventArgs e) => Main?.MenuRemoveLayer_Click(s, e);
        private void ComboShader_SelectionChanged(object s, SelectionChangedEventArgs e) => Main?.ComboShader_SelectionChanged(s, e);
        private void ComboAtlas_SelectionChanged(object s, SelectionChangedEventArgs e) => Main?.ComboAtlas_SelectionChanged(s, e);
        private void BtnToggleEdit_Click(object s, RoutedEventArgs e) => Main?.BtnToggleEdit_Click(s, e);
        private void BtnDigitizePoint_Click(object s, RoutedEventArgs e) => Main?.BtnDigitizePoint_Click(s, e);
        private void BtnDigitizeLine_Click(object s, RoutedEventArgs e) => Main?.BtnDigitizeLine_Click(s, e);
        private void BtnDigitizePolygon_Click(object s, RoutedEventArgs e) => Main?.BtnDigitizePolygon_Click(s, e);
        private void BtnVertexTool_Click(object s, RoutedEventArgs e) => Main?.BtnVertexTool_Click(s, e);
        private void BtnUndoVertex_Click(object s, RoutedEventArgs e) => Main?.BtnUndoVertex_Click(s, e);
        private void BtnDeleteFeature_Click(object s, RoutedEventArgs e) => Main?.BtnDeleteFeature_Click(s, e);
        private void BtnSplitGeometry_Click(object s, RoutedEventArgs e) => Main?.BtnSplitGeometry_Click(s, e);
        private void BtnClearDigitized_Click(object s, RoutedEventArgs e) => Main?.BtnClearDigitized_Click(s, e);
    }
}
