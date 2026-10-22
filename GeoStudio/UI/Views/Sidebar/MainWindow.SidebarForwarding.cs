using System.Windows;
using System.Windows.Controls;
using System.Windows.Shapes;

namespace GeoStudio
{
    public partial class MainWindow
    {
        public ItemsControl LayersListControl => SidebarControl?.LayersListControl!;
        public TextBlock? TxtLayerCount => SidebarControl?.TxtLayerCount;
        public TextBox TxtSearchLayers => SidebarControl?.TxtSearchLayers!;

        public Border? CardBenchmark => SidebarControl?.CardBenchmark;
        public TextBlock? TxtBenchmarkFileName => SidebarControl?.TxtBenchmarkFileName;
        public TextBlock? TxtBenchmarkTotalTime => SidebarControl?.TxtBenchmarkTotalTime;
        public TextBlock? TxtBenchmarkBreakdown => SidebarControl?.TxtBenchmarkBreakdown;
        public ProgressBar? ProgressBarFileLoad => SidebarControl?.ProgressBarFileLoad;
        public TextBlock? TxtBenchmarkStatusIcon => SidebarControl?.TxtBenchmarkStatusIcon;
        public TextBlock? TxtBenchmarkStatus => SidebarControl?.TxtBenchmarkStatus;

        public TextBlock? TxtCpuUsage => SidebarControl?.TxtCpuUsage;
        public ProgressBar? ProgressCpu => SidebarControl?.ProgressCpu;
        public TextBlock? TxtMemoryUsage => SidebarControl?.TxtMemoryUsage;
        public TextBlock? TxtMemoryPeak => SidebarControl?.TxtMemoryPeak;
        public TextBlock? TxtGpuFps => SidebarControl?.TxtGpuFps;
        public TextBlock? TxtGpuFrameTime => SidebarControl?.TxtGpuFrameTime;

        public Border? BadgeInteraction => SidebarControl?.BadgeInteraction;
        public TextBlock? TxtInteractionType => SidebarControl?.TxtInteractionType;
        public TextBlock? TxtInteractionDetails => SidebarControl?.TxtInteractionDetails;
        public TextBlock? TxtActiveElements => SidebarControl?.TxtActiveElements;

        public Ellipse? LiveIndicatorDot => SidebarControl?.LiveIndicatorDot;
        public Button? BtnToggleTelemetry => SidebarControl?.BtnToggleTelemetry;
        public StackPanel? TelemetryContentPanel => SidebarControl?.TelemetryContentPanel;
    }
}
