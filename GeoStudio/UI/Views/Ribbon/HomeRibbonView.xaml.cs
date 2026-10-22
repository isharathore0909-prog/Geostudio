using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Views.Ribbon
{
    public partial class HomeRibbonView : UserControl
    {
        public HomeRibbonView()
        {
            InitializeComponent();
        }

        private MainWindow? Main => Application.Current.MainWindow as MainWindow;

        public void SwitchTab(string tabName)
        {
            if (PanelRibbonHome != null)
                PanelRibbonHome.Visibility = tabName == "Home" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonFile != null)
                PanelRibbonFile.Visibility = (tabName == "File" || tabName == "Project") ? Visibility.Visible : Visibility.Collapsed;
        }

        private void MenuNewProject_Click(object s, RoutedEventArgs e) => Main?.MenuNewProject_Click(s, e);
        private void MenuProcessingToolbox_Click(object s, RoutedEventArgs e) => Main?.MenuProcessingToolbox_Click(s, e);
        private void MenuOpenProject_Click(object s, RoutedEventArgs e) => Main?.MenuOpenProject_Click(s, e);
        private void BtnPrint_Click(object s, RoutedEventArgs e) => Main?.BtnPrint_Click(s, e);
        private void BtnFileBrowser_Click(object s, RoutedEventArgs e) => Main?.BtnFileBrowser_Click(s, e);
        private void BtnAddRaster_Click(object s, RoutedEventArgs e) => Main?.BtnAddRaster_Click(s, e);
        private void BtnPan_Click(object s, RoutedEventArgs e) => Main?.BtnPan_Click(s, e);
        private void BtnZoomFull_Click(object s, RoutedEventArgs e) => Main?.BtnZoomFull_Click(s, e);
        private void BtnZoomIn_Click(object s, RoutedEventArgs e) => Main?.BtnZoomIn_Click(s, e);
        private void BtnZoomOut_Click(object s, RoutedEventArgs e) => Main?.BtnZoomOut_Click(s, e);
        private void BtnUndo_Click(object s, RoutedEventArgs e) => Main?.BtnUndo_Click(s, e);
        private void BtnRedo_Click(object s, RoutedEventArgs e) => Main?.BtnRedo_Click(s, e);
        private void BtnIdentify_Click(object s, RoutedEventArgs e) => Main?.BtnIdentify_Click(s, e);
        private void Btn3dMesh_Click(object s, RoutedEventArgs e) => Main?.Btn3dMesh_Click(s, e);
        private void BtnAddOsm_Click(object s, RoutedEventArgs e) => Main?.BtnAddOsm_Click(s, e);
        private void BtnAddVector_Click(object s, RoutedEventArgs e) => Main?.BtnAddVector_Click(s, e);
        private void BtnDatabase_Click(object s, RoutedEventArgs e) => Main?.BtnDatabase_Click(s, e);
        private void BtnSelectPointer_Click(object s, RoutedEventArgs e) => Main?.BtnSelectPointer_Click(s, e);
        private void BtnSelectPolygon_Click(object s, RoutedEventArgs e) => Main?.BtnSelectPolygon_Click(s, e);
        private void BtnClearSelection_Click(object s, RoutedEventArgs e) => Main?.BtnClearSelection_Click(s, e);
        private void BtnMeasureDistance_Click(object s, RoutedEventArgs e) => Main?.BtnMeasureDistance_Click(s, e);
        private void BtnSelectBox_Click(object s, RoutedEventArgs e) => Main?.BtnSelectBox_Click(s, e);
        private void MenuProfile_Click(object s, RoutedEventArgs e) => Main?.MenuProfile_Click(s, e);
        private void MenuSaveProject_Click(object s, RoutedEventArgs e) => Main?.MenuSaveProject_Click(s, e);
        private void BtnAddLidar_Click(object s, RoutedEventArgs e) => Main?.BtnAddLidar_Click(s, e);
        private void MenuClearCache_Click(object s, RoutedEventArgs e) => Main?.MenuClearCache_Click(s, e);
        private void MenuExit_Click(object s, RoutedEventArgs e) => Main?.MenuExit_Click(s, e);
    }
}
