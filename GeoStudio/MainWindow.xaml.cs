using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Text.Json;
using System.Windows;
using Microsoft.Web.WebView2.Core;
using GeoStudio.Models;
using GeoStudio.Raster;
using GeoStudio.PointCloud;

namespace GeoStudio
{
    public partial class MainWindow : Window
    {
        public ObservableCollection<LayerItem> Layers { get; set; } = new ObservableCollection<LayerItem>();
        private bool _isMapReady = false;
        private bool _isInitialized = false;
        private System.Threading.CancellationTokenSource? _rasterCts = null;
        private string? _activeRasterFilePath = null;
        private string? _activeRasterLayerId = null;
        private string? _activeRasterShaderMode = null;
        private string? _activeRasterPalette = null;
        private UI.ElevationProfileWindow? _activeProfileWindow = null;
        private PointCloud.PointCloudBatch? _activePointCloudBatch = null;

        public MainWindow()
        {
            InitializeComponent();
            MapWebView.DefaultBackgroundColor = System.Drawing.Color.White;
            _isInitialized = true;
            LayersListControl.ItemsSource = Layers;
            Loaded += MainWindow_Loaded;
        }

        #region Tabbed Ribbon Navigation
        private void RibbonTab_Checked(object sender, RoutedEventArgs e)
        {
            if (sender is FrameworkElement fe && fe.Tag is string tag)
            {
                SwitchRibbonTab(tag);
            }
        }

        private void SwitchRibbonTab(string tabName)
        {
            if (PanelRibbonFile == null) return;

            PanelRibbonFile.Visibility = tabName == "File" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonEdit.Visibility = tabName == "Edit" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonView.Visibility = tabName == "View" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonLayer.Visibility = tabName == "Layer" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonSettings.Visibility = tabName == "Settings" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonPlugins.Visibility = tabName == "Plugins" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonVector.Visibility = tabName == "Vector" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonRaster.Visibility = tabName == "Raster" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonSatellite.Visibility = tabName == "Satellite" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonTerrain.Visibility = tabName == "Terrain" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonLidar.Visibility = tabName == "LiDAR" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonProcessing.Visibility = tabName == "Processing" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbon3D.Visibility = tabName == "3D" ? Visibility.Visible : Visibility.Collapsed;
            PanelRibbonHelp.Visibility = tabName == "Help" ? Visibility.Visible : Visibility.Collapsed;
        }

        private void Window_PreviewKeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            var ctrl = (System.Windows.Input.Keyboard.Modifiers & System.Windows.Input.ModifierKeys.Control) != 0;
            var shift = (System.Windows.Input.Keyboard.Modifiers & System.Windows.Input.ModifierKeys.Shift) != 0;
            var alt = (System.Windows.Input.Keyboard.Modifiers & System.Windows.Input.ModifierKeys.Alt) != 0;

            if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.N) { MenuNewProject_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.O) { MenuOpenProject_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.S) { MenuSaveProject_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.P) { BtnPrint_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.Z) { BtnUndo_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.Y) { BtnRedo_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.E) { BtnToggleEdit_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && !shift && !alt && e.Key == System.Windows.Input.Key.Q) { MenuExit_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && shift && !alt && e.Key == System.Windows.Input.Key.R) { BtnAddRaster_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && shift && !alt && e.Key == System.Windows.Input.Key.V) { BtnAddVector_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && shift && !alt && e.Key == System.Windows.Input.Key.F) { BtnZoomFull_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && shift && !alt && e.Key == System.Windows.Input.Key.W) { BtnSplit_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && alt && !shift && e.Key == System.Windows.Input.Key.P) { MenuPythonConsole_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (ctrl && alt && !shift && e.Key == System.Windows.Input.Key.T) { MenuProcessingToolbox_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (e.Key == System.Windows.Input.Key.F5) { BtnRefresh_Click(this, new RoutedEventArgs()); e.Handled = true; }
            else if (e.Key == System.Windows.Input.Key.F6) { BtnIdentify_Click(this, new RoutedEventArgs()); e.Handled = true; }
        }
        #endregion

        private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            InitializeTelemetry();
            Environment.SetEnvironmentVariable("WEBVIEW2_DEFAULT_BACKGROUND_COLOR", "0xFFFFFFFF");
            try
            {
                UpdateLayerCount();

                string mapEngineDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "WebView", "MapEngine");
                if (!Directory.Exists(mapEngineDir))
                    mapEngineDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Resources", "MapEngine");
                if (!Directory.Exists(mapEngineDir))
                    mapEngineDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "WebView", "MapEngine"));
                if (!Directory.Exists(mapEngineDir))
                    mapEngineDir = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "Resources", "MapEngine"));

                bool initialized = false;
                for (int attempt = 0; attempt < 3 && !initialized; attempt++)
                {
                    try
                    {
                        string folder = attempt == 0
                            ? Path.Combine(Path.GetTempPath(), "GeoStudio", $"WV2_{Environment.ProcessId}")
                            : Path.Combine(Path.GetTempPath(), "GeoStudio", $"WV2_{Guid.NewGuid():N}");

                        Directory.CreateDirectory(folder);
                        var options = new CoreWebView2EnvironmentOptions();
                        options.AdditionalBrowserArguments = "--enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist --enable-webgl --default-background-color=0xFFFFFFFF";
                        var env = await CoreWebView2Environment.CreateAsync(null, folder, options);
                        var controllerOptions = env.CreateCoreWebView2ControllerOptions();
                        controllerOptions.DefaultBackgroundColor = System.Drawing.Color.White;
                        await MapWebView.EnsureCoreWebView2Async(env, controllerOptions);
                        MapWebView.DefaultBackgroundColor = System.Drawing.Color.White;
                        initialized = true;
                    }
                    catch
                    {
                        await System.Threading.Tasks.Task.Delay(150);
                    }
                }

                if (MapWebView.CoreWebView2 != null)
                {
                    MapWebView.CoreWebView2.WebMessageReceived += CoreWebView2_WebMessageReceived;
                    await MapWebView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(
                        "document.documentElement.style.backgroundColor = '#ffffff'; if (document.body) document.body.style.backgroundColor = '#ffffff';"
                    );
                    MapWebView.NavigationCompleted += (s, args) =>
                    {
                        Dispatcher.InvokeAsync(async () =>
                        {
                            await System.Threading.Tasks.Task.Delay(80);
                            MapWebView.Visibility = Visibility.Visible;
                            MapLoadingOverlay.Visibility = Visibility.Collapsed;
                        });
                    };

                    GdalRasterService.OverviewReady += (filePath, previewUrl) =>
                    {
                        Dispatcher.InvokeAsync(() =>
                        {
                            if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                            if (_activeRasterFilePath == filePath)
                            {
                                TxtStatus.Text = $"Rendered: {Path.GetFileName(filePath)} (Overview ready)";
                                var activeLyr = Layers.FirstOrDefault(l => l.Id == _activeRasterLayerId);
                                PostMessageToMap(new
                                {
                                    action = "updateRasterOverview",
                                    id = _activeRasterLayerId,
                                    imageUrl = previewUrl,
                                    imageUri = previewUrl,
                                    shaderMode = _activeRasterShaderMode,
                                    palette = _activeRasterPalette,
                                    minElev = activeLyr?.MinElevation ?? 0,
                                    maxElev = activeLyr?.MaxElevation ?? 0,
                                    isElevation = activeLyr?.IsElevation ?? false
                                });
                            }
                        });
                    };

                    string rasterCacheDir = GdalRasterService.GetCacheDirectory();
                    MapWebView.CoreWebView2.SetVirtualHostNameToFolderMapping(
                        "cache.geostudio.local",
                        rasterCacheDir,
                        Microsoft.Web.WebView2.Core.CoreWebView2HostResourceAccessKind.Allow);

                    if (Directory.Exists(mapEngineDir))
                    {
                        MapWebView.CoreWebView2.SetVirtualHostNameToFolderMapping(
                            "geostudio.local",
                            mapEngineDir,
                            Microsoft.Web.WebView2.Core.CoreWebView2HostResourceAccessKind.Allow);

                        MapWebView.CoreWebView2.Navigate("http://geostudio.local/index.html");
                    }
                    else
                    {
                        string htmlPath = Path.Combine(mapEngineDir, "index.html");
                        if (File.Exists(htmlPath))
                        {
                            MapWebView.CoreWebView2.Navigate(new Uri(htmlPath).AbsoluteUri);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                TxtStatus.Text = $"Map initialization warning: {ex.Message}";
            }
        }

        private void PostMessageToMap(object payload)
        {
            if (!_isMapReady || MapWebView.CoreWebView2 == null) return;
            string json = JsonSerializer.Serialize(payload);
            MapWebView.CoreWebView2.PostWebMessageAsJson(json);
        }
    }
}