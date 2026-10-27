using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using GeoStudio.Models;
using GeoStudio.UI.Services;

namespace GeoStudio.UI.Dialogs.Plugins
{
    public partial class PluginManagerWindow : Window
    {
        private readonly PluginManagerService _service = PluginManagerService.Instance;
        private List<PluginManifest> _allPlugins = new();
        private bool _isLoaded = false;
        private readonly string? _initialFilterQuery;

        public PluginManagerWindow(string? initialFilterQuery = null)
        {
            _initialFilterQuery = initialFilterQuery;
            InitializeComponent();
            _isLoaded = true;

            _service.PluginStatusChanged += OnPluginStatusChanged;
            LoadPlugins();

            if (!string.IsNullOrEmpty(_initialFilterQuery) && TxtSearch != null)
            {
                TxtSearch.Text = _initialFilterQuery;
            }
        }

        private void LoadPlugins()
        {
            _service.DiscoverPlugins();
            _allPlugins = _service.AvailablePlugins.ToList();
            ApplyFilter();
        }

        private void OnPluginStatusChanged(PluginManifest plugin)
        {
            Dispatcher.Invoke(UpdateSummary);
        }

        private void Filter_Changed(object sender, RoutedEventArgs e)
        {
            if (!_isLoaded) return;
            ApplyFilter();
        }

        private void TxtSearch_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (!_isLoaded) return;
            ApplyFilter();
        }

        private void ApplyFilter()
        {
            if (!_isLoaded || PluginsItemsControl == null || _allPlugins == null) return;

            string query = (TxtSearch?.Text ?? string.Empty).Trim().ToLowerInvariant();
            bool filterInstalled = RadioInstalled?.IsChecked == true;
            bool filterAvailable = RadioAvailable?.IsChecked == true;

            var filtered = _allPlugins.Where(p =>
            {
                bool matchesQuery = string.IsNullOrEmpty(query) ||
                                    p.Name.ToLowerInvariant().Contains(query) ||
                                    p.Description.ToLowerInvariant().Contains(query) ||
                                    p.Category.ToLowerInvariant().Contains(query);

                if (!matchesQuery) return false;

                if (filterInstalled) return p.IsInstalled;
                if (filterAvailable) return !p.IsInstalled;
                return true;
            }).ToList();

            PluginsItemsControl.ItemsSource = filtered;
            UpdateSummary();
        }

        private void UpdateSummary()
        {
            if (TxtSummary == null || _allPlugins == null) return;
            int total = _allPlugins.Count;
            int installed = _allPlugins.Count(p => p.IsInstalled);
            TxtSummary.Text = $"Active Extensions: {installed} of {total} installed  •  100% Offline Air-Gapped";
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();

        protected override void OnClosed(EventArgs e)
        {
            _service.PluginStatusChanged -= OnPluginStatusChanged;
            base.OnClosed(e);
        }
    }
}
