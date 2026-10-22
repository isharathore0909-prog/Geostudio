using System.Windows;
using System.Windows.Controls;

namespace GeoStudio
{
    public partial class MainWindow
    {
        public ComboBox ComboShader => RibbonLayer?.ComboShader!;
        public ComboBox ComboAtlas => RibbonLayer?.ComboAtlas!;
        public ComboBox ComboLidarColorBy => RibbonTools?.ComboLidarColorBy!;
        public ComboBox ComboSnapping => RibbonTools?.ComboSnapping!;

        public FrameworkElement? PanelRibbonHome => RibbonGeneral?.PanelRibbonHome;
        public FrameworkElement? PanelRibbonFile => RibbonGeneral?.PanelRibbonFile;
        public FrameworkElement? PanelRibbonData => RibbonLayer?.PanelRibbonData;
        public FrameworkElement? PanelRibbonLayer => RibbonLayer?.PanelRibbonLayer;
        public FrameworkElement? PanelRibbonStyle => RibbonLayer?.PanelRibbonStyle;
        public FrameworkElement? PanelRibbonEdit => RibbonLayer?.PanelRibbonEdit;
        public FrameworkElement? PanelRibbonAnalyze => RibbonAnalysis?.PanelRibbonAnalyze;
        public FrameworkElement? PanelRibbonTerrain => RibbonAnalysis?.PanelRibbonTerrain;
        public FrameworkElement? PanelRibbonView => RibbonAnalysis?.PanelRibbonView;
        public FrameworkElement? PanelRibbon3D => RibbonAnalysis?.PanelRibbon3D;
        public FrameworkElement? PanelRibbonLidar => RibbonTools?.PanelRibbonLidar;
        public FrameworkElement? PanelRibbonVector => RibbonTools?.PanelRibbonVector;
        public FrameworkElement? PanelRibbonRaster => RibbonTools?.PanelRibbonRaster;
        public FrameworkElement? PanelRibbonSatellite => RibbonTools?.PanelRibbonSatellite;
        public FrameworkElement? PanelRibbonProcessing => RibbonTools?.PanelRibbonProcessing;
        public FrameworkElement? PanelRibbonSettings => RibbonTools?.PanelRibbonSettings;
        public FrameworkElement? PanelRibbonPlugins => RibbonTools?.PanelRibbonPlugins;
        public FrameworkElement? PanelRibbonHelp => RibbonTools?.PanelRibbonHelp;
    }
}
