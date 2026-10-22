using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Views.Ribbon
{
    public partial class ToolsRibbonView : UserControl
    {
        public ToolsRibbonView()
        {
            InitializeComponent();
        }

        private MainWindow? Main => Application.Current.MainWindow as MainWindow;

        public void SwitchTab(string tabName)
        {
            if (PanelRibbonLidar != null)
                PanelRibbonLidar.Visibility = tabName == "LiDAR" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonVector != null)
                PanelRibbonVector.Visibility = tabName == "Vector" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonRaster != null)
                PanelRibbonRaster.Visibility = tabName == "Raster" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonSatellite != null)
                PanelRibbonSatellite.Visibility = tabName == "Satellite" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonProcessing != null)
                PanelRibbonProcessing.Visibility = tabName == "Processing" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonSettings != null)
                PanelRibbonSettings.Visibility = tabName == "Settings" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonPlugins != null)
                PanelRibbonPlugins.Visibility = tabName == "Plugins" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonHelp != null)
                PanelRibbonHelp.Visibility = tabName == "Help" ? Visibility.Visible : Visibility.Collapsed;
        }

        private void BtnAddLidar_Click(object s, RoutedEventArgs e) => Main?.BtnAddLidar_Click(s, e);
        private void ComboLidarColorBy_SelectionChanged(object s, SelectionChangedEventArgs e) => Main?.ComboLidarColorBy_SelectionChanged(s, e);
        private void BtnLidarClassifyGround_Click(object s, RoutedEventArgs e) => Main?.BtnLidarClassifyGround_Click(s, e);
        private void BtnLidarClassifyVeg_Click(object s, RoutedEventArgs e) => Main?.BtnLidarClassifyVeg_Click(s, e);
        private void BtnLidarClassifyBuildings_Click(object s, RoutedEventArgs e) => Main?.BtnLidarClassifyBuildings_Click(s, e);
        private void MenuLidarDtm_Click(object s, RoutedEventArgs e) => Main?.MenuLidarDtm_Click(s, e);
        private void MenuLidarChm_Click(object s, RoutedEventArgs e) => Main?.MenuLidarChm_Click(s, e);
        private void BtnLidarThin_Click(object s, RoutedEventArgs e) => Main?.BtnLidarThin_Click(s, e);
        private void MenuClipVector_Click(object s, RoutedEventArgs e) => Main?.MenuClipVector_Click(s, e);
        private void MenuBuffer_Click(object s, RoutedEventArgs e) => Main?.MenuBuffer_Click(s, e);
        private void MenuConvexHull_Click(object s, RoutedEventArgs e) => Main?.MenuConvexHull_Click(s, e);
        private void MenuCentroids_Click(object s, RoutedEventArgs e) => Main?.MenuCentroids_Click(s, e);
        private void MenuDissolve_Click(object s, RoutedEventArgs e) => Main?.MenuDissolve_Click(s, e);
        private void MenuVoronoi_Click(object s, RoutedEventArgs e) => Main?.MenuVoronoi_Click(s, e);
        private void MenuClipRaster_Click(object s, RoutedEventArgs e) => Main?.MenuClipRaster_Click(s, e);
        private void MenuRasterStats_Click(object s, RoutedEventArgs e) => Main?.MenuRasterStats_Click(s, e);
        private void MenuNdvi_Click(object s, RoutedEventArgs e) => Main?.MenuNdvi_Click(s, e);
        private void MenuNdwi_Click(object s, RoutedEventArgs e) => Main?.MenuNdwi_Click(s, e);
        private void MenuEvi_Click(object s, RoutedEventArgs e) => Main?.MenuEvi_Click(s, e);
        private void MenuNdbi_Click(object s, RoutedEventArgs e) => Main?.MenuNdbi_Click(s, e);
        private void MenuNbr_Click(object s, RoutedEventArgs e) => Main?.MenuNbr_Click(s, e);
        private void MenuFalseColor_Click(object s, RoutedEventArgs e) => Main?.MenuFalseColor_Click(s, e);
        private void MenuProcessingToolbox_Click(object s, RoutedEventArgs e) => Main?.MenuProcessingToolbox_Click(s, e);
        private void MenuPythonConsole_Click(object s, RoutedEventArgs e) => Main?.MenuPythonConsole_Click(s, e);
        private void MenuPythonStatus_Click(object s, RoutedEventArgs e) => Main?.MenuPythonStatus_Click(s, e);
        private void MenuGpuStatus_Click(object s, RoutedEventArgs e) => Main?.MenuGpuStatus_Click(s, e);
        private void MenuClearCache_Click(object s, RoutedEventArgs e) => Main?.MenuClearCache_Click(s, e);
        private void MenuDocs_Click(object s, RoutedEventArgs e) => Main?.MenuDocs_Click(s, e);
        private void MenuAbout_Click(object s, RoutedEventArgs e) => Main?.MenuAbout_Click(s, e);
    }
}
