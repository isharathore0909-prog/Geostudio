using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace GeoStudio.Models
{
    public enum LayerType
    {
        Vector,
        Raster,
        PointCloud,
        Basemap,
        Elevation
    }

    public class LayerItem : INotifyPropertyChanged
    {
        private string _id = Guid.NewGuid().ToString();
        private string _name = string.Empty;
        private LayerType _type = LayerType.Vector;
        private bool _isVisible = true;
        private double _opacity = 1.0;
        private string _colorHex = "#3B82F6";
        private string _details = string.Empty;
        private string _filePath = string.Empty;
        private long _fileSizeBytes = 0;
        private int _featureCount = 0;
        private double[]? _boundingBox;
        private string _loadTimeText = string.Empty;
        private string _canvasRenderTimeText = string.Empty;
        private string _totalDurationText = string.Empty;
        private bool _hasLoadTime = false;
        private string? _shaderMode;
        private string? _palette;
        private bool _isElevation = false;
        private double _minElevation = 0;
        private double _maxElevation = 0;

        public string? ShaderMode
        {
            get => _shaderMode;
            set { _shaderMode = value; OnPropertyChanged(); }
        }

        public string? Palette
        {
            get => _palette;
            set { _palette = value; OnPropertyChanged(); }
        }

        public double MinElevation
        {
            get => _minElevation;
            set { _minElevation = value; OnPropertyChanged(); }
        }

        public double MaxElevation
        {
            get => _maxElevation;
            set { _maxElevation = value; OnPropertyChanged(); }
        }

        public bool IsElevation
        {
            get => _isElevation;
            set { _isElevation = value; OnPropertyChanged(); }
        }

        public double[]? BoundingBox
        {
            get => _boundingBox;
            set { _boundingBox = value; OnPropertyChanged(); }
        }

        public string LoadTimeText
        {
            get => _loadTimeText;
            set { _loadTimeText = value; HasLoadTime = !string.IsNullOrEmpty(value); OnPropertyChanged(); }
        }

        public string CanvasRenderTimeText
        {
            get => _canvasRenderTimeText;
            set { _canvasRenderTimeText = value; OnPropertyChanged(); }
        }

        public string TotalDurationText
        {
            get => _totalDurationText;
            set { _totalDurationText = value; OnPropertyChanged(); }
        }

        public bool HasLoadTime
        {
            get => _hasLoadTime;
            set { _hasLoadTime = value; OnPropertyChanged(); }
        }

        public string Id
        {
            get => _id;
            set { _id = value; OnPropertyChanged(); }
        }

        public string Name
        {
            get => _name;
            set { _name = value; OnPropertyChanged(); }
        }

        public LayerType Type
        {
            get => _type;
            set { _type = value; OnPropertyChanged(); }
        }

        public bool IsVisible
        {
            get => _isVisible;
            set { _isVisible = value; OnPropertyChanged(); }
        }

        public double Opacity
        {
            get => _opacity;
            set { _opacity = value; OnPropertyChanged(); }
        }

        public string ColorHex
        {
            get => _colorHex;
            set { _colorHex = value; OnPropertyChanged(); }
        }

        public string Details
        {
            get => _details;
            set { _details = value; OnPropertyChanged(); }
        }

        public string FilePath
        {
            get => _filePath;
            set { _filePath = value; OnPropertyChanged(); }
        }

        public long FileSizeBytes
        {
            get => _fileSizeBytes;
            set { _fileSizeBytes = value; OnPropertyChanged(); }
        }

        public int FeatureCount
        {
            get => _featureCount;
            set { _featureCount = value; OnPropertyChanged(); }
        }

        public string DisplaySize
        {
            get
            {
                if (_fileSizeBytes <= 0) return string.Empty;
                if (_fileSizeBytes >= 1024L * 1024 * 1024 * 1024)
                    return $"{_fileSizeBytes / (1024.0 * 1024 * 1024 * 1024):F2} TB";
                if (_fileSizeBytes >= 1024L * 1024 * 1024)
                    return $"{_fileSizeBytes / (1024.0 * 1024 * 1024):F2} GB";
                if (_fileSizeBytes >= 1024 * 1024)
                    return $"{_fileSizeBytes / (1024.0 * 1024):F1} MB";
                return $"{_fileSizeBytes / 1024.0:F1} KB";
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;
        protected void OnPropertyChanged([CallerMemberName] string? propName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propName));
        }
    }
}
