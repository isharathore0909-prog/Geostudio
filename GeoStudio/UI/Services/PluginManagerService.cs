using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using GeoStudio.Models;

namespace GeoStudio.UI.Services
{
    public class PluginManagerService
    {
        private static PluginManagerService? _instance;
        public static PluginManagerService Instance => _instance ??= new PluginManagerService();

        public ObservableCollection<PluginManifest> AvailablePlugins { get; } = new();
        public event Action<PluginManifest>? PluginStatusChanged;

        private readonly string _pluginsDirectory;
        private readonly string _configFile;
        private readonly HashSet<string> _activePluginIds = new(StringComparer.OrdinalIgnoreCase);

        private PluginManagerService()
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            _pluginsDirectory = Path.Combine(baseDir, "Plugins");
            _configFile = Path.Combine(baseDir, "Config", "installed_plugins.json");

            // Ensure directories exist
            if (!Directory.Exists(_pluginsDirectory))
            {
                // Also check project-relative path if running in debug
                string altPath = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "Plugins"));
                if (Directory.Exists(altPath)) _pluginsDirectory = altPath;
                else Directory.CreateDirectory(_pluginsDirectory);
            }

            if (!File.Exists(_configFile))
            {
                string altConfig = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", "Config", "installed_plugins.json"));
                if (File.Exists(altConfig)) _configFile = altConfig;
            }

            LoadConfiguration();
            DiscoverPlugins();
        }

        private void LoadConfiguration()
        {
            _activePluginIds.Clear();
            if (File.Exists(_configFile))
            {
                try
                {
                    string json = File.ReadAllText(_configFile);
                    using var doc = JsonDocument.Parse(json);
                    if (doc.RootElement.TryGetProperty("active_plugins", out var activeArr) && activeArr.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var elem in activeArr.EnumerateArray())
                        {
                            string? id = elem.GetString();
                            if (!string.IsNullOrEmpty(id)) _activePluginIds.Add(id);
                        }
                    }
                }
                catch { }
            }
        }

        private void SaveConfiguration()
        {
            try
            {
                string? dir = Path.GetDirectoryName(_configFile);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);

                var data = new
                {
                    active_plugins = new List<string>(_activePluginIds),
                    last_updated = DateTime.UtcNow.ToString("o")
                };
                File.WriteAllText(_configFile, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }));
            }
            catch { }
        }

        public void DiscoverPlugins()
        {
            AvailablePlugins.Clear();
            if (!Directory.Exists(_pluginsDirectory)) return;

            foreach (string dir in Directory.GetDirectories(_pluginsDirectory))
            {
                string manifestPath = Path.Combine(dir, "plugin.json");
                if (File.Exists(manifestPath))
                {
                    try
                    {
                        string json = File.ReadAllText(manifestPath);
                        var manifest = JsonSerializer.Deserialize<PluginManifest>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                        if (manifest != null && !string.IsNullOrEmpty(manifest.Id))
                        {
                            manifest.Status = _activePluginIds.Contains(manifest.Id) ? PluginStatus.Installed : PluginStatus.NotInstalled;
                            AvailablePlugins.Add(manifest);
                        }
                    }
                    catch { }
                }
            }
        }

        public async Task<bool> TogglePluginAsync(PluginManifest plugin)
        {
            if (plugin.Status == PluginStatus.Installed)
            {
                return await UninstallPluginAsync(plugin);
            }
            else
            {
                return await InstallPluginAsync(plugin);
            }
        }

        public async Task<bool> InstallPluginAsync(PluginManifest plugin)
        {
            plugin.Status = PluginStatus.Installing;
            await Task.Delay(600); // Simulated smooth progress for responsive UI feel

            _activePluginIds.Add(plugin.Id);
            SaveConfiguration();

            plugin.Status = PluginStatus.Installed;
            PluginStatusChanged?.Invoke(plugin);
            return true;
        }

        public async Task<bool> UninstallPluginAsync(PluginManifest plugin)
        {
            plugin.Status = PluginStatus.Installing;
            await Task.Delay(350);

            _activePluginIds.Remove(plugin.Id);
            SaveConfiguration();

            plugin.Status = PluginStatus.NotInstalled;
            PluginStatusChanged?.Invoke(plugin);
            return true;
        }

        public bool IsPluginActive(string pluginId) => _activePluginIds.Contains(pluginId);
    }
}
