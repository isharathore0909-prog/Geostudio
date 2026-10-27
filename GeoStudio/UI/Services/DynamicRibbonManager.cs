using System;
using System.Windows;
using GeoStudio.Models;

namespace GeoStudio.UI.Services
{
    public class DynamicRibbonManager
    {
        private readonly Window _mainWindow;
        private readonly PluginManagerService _pluginService;

        public DynamicRibbonManager(Window mainWindow)
        {
            _mainWindow = mainWindow ?? throw new ArgumentNullException(nameof(mainWindow));
            _pluginService = PluginManagerService.Instance;
            _pluginService.PluginStatusChanged += OnPluginStatusChanged;
        }

        public void InitializeRibbonState()
        {
            foreach (var plugin in _pluginService.AvailablePlugins)
            {
                ApplyPluginRibbonState(plugin);
            }
        }

        private void OnPluginStatusChanged(PluginManifest plugin)
        {
            _mainWindow.Dispatcher.Invoke(() => ApplyPluginRibbonState(plugin));
        }

        public void ApplyPluginRibbonState(PluginManifest plugin)
        {
            bool isInstalled = plugin.Status == PluginStatus.Installed;
            
            foreach (var panelName in plugin.AssociatedRibbonPanels)
            {
                var element = FindElementInWindow(panelName);
                if (element != null)
                {
                    element.Visibility = isInstalled ? Visibility.Visible : Visibility.Collapsed;
                    element.IsEnabled = isInstalled;
                }
            }
        }

        private UIElement? FindElementInWindow(string name)
        {
            var el = _mainWindow.FindName(name) as UIElement;
            if (el != null) return el;

            if (_mainWindow is MainWindow mw)
            {
                el = mw.RibbonTools?.FindName(name) as UIElement;
                if (el != null) return el;
                el = mw.RibbonAnalysis?.FindName(name) as UIElement;
                if (el != null) return el;
                el = mw.RibbonLayer?.FindName(name) as UIElement;
                if (el != null) return el;
                el = mw.RibbonGeneral?.FindName(name) as UIElement;
                if (el != null) return el;
            }
            return null;
        }
    }
}
