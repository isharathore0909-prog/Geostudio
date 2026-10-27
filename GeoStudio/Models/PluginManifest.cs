using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace GeoStudio.Models
{
    public enum PluginStatus
    {
        NotInstalled,
        Installing,
        Installed,
        Disabled
    }

    public class PluginManifest : INotifyPropertyChanged
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string Version { get; set; } = "1.0.0";
        public string Category { get; set; } = "General";
        public string Description { get; set; } = string.Empty;
        public string IconEmoji { get; set; } = "🧩";
        public string IconPath { get; set; } = string.Empty;
        public double DownloadSizeMb { get; set; } = 0.0;
        public string EngineType { get; set; } = "Python";
        public List<string> Dependencies { get; set; } = new();
        public List<string> AssociatedRibbonPanels { get; set; } = new();

        private PluginStatus _status = PluginStatus.NotInstalled;
        public PluginStatus Status
        {
            get => _status;
            set
            {
                if (_status != value)
                {
                    _status = value;
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(IsInstalled));
                    OnPropertyChanged(nameof(ActionButtonText));
                    OnPropertyChanged(nameof(StatusBadgeText));
                    OnPropertyChanged(nameof(StatusBadgeColor));
                }
            }
        }

        public bool IsInstalled => Status == PluginStatus.Installed;
        public string ActionButtonText => Status switch
        {
            PluginStatus.Installed => "Uninstall",
            PluginStatus.Installing => "Installing...",
            _ => "Install"
        };

        public string StatusBadgeText => Status switch
        {
            PluginStatus.Installed => "ACTIVE",
            PluginStatus.Installing => "DOWNLOADING",
            _ => "AVAILABLE"
        };

        public string StatusBadgeColor => Status switch
        {
            PluginStatus.Installed => "#10B981",
            PluginStatus.Installing => "#F59E0B",
            _ => "#64748B"
        };

        public event PropertyChangedEventHandler? PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string? propName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propName));
        }
    }
}
