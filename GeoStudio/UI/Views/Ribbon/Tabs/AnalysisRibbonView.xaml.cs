using System.Windows;
using System.Windows.Controls;

namespace GeoStudio.UI.Views.Ribbon
{
    public partial class AnalysisRibbonView : UserControl
    {
        public AnalysisRibbonView()
        {
            InitializeComponent();
        }

        private MainWindow? Main => Application.Current.MainWindow as MainWindow;

        public void SwitchTab(string tabName)
        {
            if (PanelRibbonAnalyze != null)
                PanelRibbonAnalyze.Visibility = (tabName == "Analyze" || tabName == "Terrain") ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbonView != null)
                PanelRibbonView.Visibility = tabName == "View" ? Visibility.Visible : Visibility.Collapsed;
            if (PanelRibbon3D != null)
                PanelRibbon3D.Visibility = tabName == "3D" ? Visibility.Visible : Visibility.Collapsed;
        }

        private void MenuElevation_Click(object s, RoutedEventArgs e) => Main?.MenuElevation_Click(s, e);
        private void MenuHillshade_Click(object s, RoutedEventArgs e) => Main?.MenuHillshade_Click(s, e);
        private void MenuSlope_Click(object s, RoutedEventArgs e) => Main?.MenuSlope_Click(s, e);
        private void MenuAspect_Click(object s, RoutedEventArgs e) => Main?.MenuAspect_Click(s, e);
        private void MenuProfile_Click(object s, RoutedEventArgs e) => Main?.MenuProfile_Click(s, e);
        private void MenuContour_Click(object s, RoutedEventArgs e) => Main?.MenuContour_Click(s, e);
        private void MenuCutFill_Click(object s, RoutedEventArgs e) => Main?.MenuCutFill_Click(s, e);
        private void MenuWatershed_Click(object s, RoutedEventArgs e) => Main?.MenuWatershed_Click(s, e);
        private void MenuLulc_Click(object s, RoutedEventArgs e) => Main?.MenuLulc_Click(s, e);
        private void BtnZoomFull_Click(object s, RoutedEventArgs e) => Main?.BtnZoomFull_Click(s, e);
        private void BtnRefresh_Click(object s, RoutedEventArgs e) => Main?.BtnRefresh_Click(s, e);
        private void BtnSplit_Click(object s, RoutedEventArgs e) => Main?.BtnSplit_Click(s, e);
        private void BtnOverview_Click(object s, RoutedEventArgs e) => Main?.BtnOverview_Click(s, e);
        private void BtnBlend_Click(object s, RoutedEventArgs e)
        {
            if (s is Button btn && btn.ContextMenu != null)
            {
                btn.ContextMenu.PlacementTarget = btn;
                btn.ContextMenu.Placement = System.Windows.Controls.Primitives.PlacementMode.Bottom;
                btn.ContextMenu.IsOpen = true;
            }
        }
        private void MenuBlendMode_Click(object s, RoutedEventArgs e)
        {
            if (s is MenuItem mi && mi.Tag is string mode)
            {
                Main?.ApplyLayerBlendMode(mode);
            }
        }
        private void BtnTranspose_Click(object s, RoutedEventArgs e) => Main?.BtnTranspose_Click(s, e);
        private void Btn3dMesh_Click(object s, RoutedEventArgs e) => Main?.Btn3dMesh_Click(s, e);
    }
}
