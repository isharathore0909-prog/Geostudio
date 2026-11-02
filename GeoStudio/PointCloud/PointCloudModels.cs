using System;
using System.Collections.Generic;

namespace GeoStudio.PointCloud
{
    public class LasHeaderInfo
    {
        public string FileSignature { get; set; } = "LASF";
        public byte VersionMajor { get; set; } = 1;
        public byte VersionMinor { get; set; } = 2;
        public uint HeaderSize { get; set; }
        public uint OffsetToPointData { get; set; }
        public byte PointDataRecordFormat { get; set; }
        public ushort PointDataRecordLength { get; set; }
        public ulong LegacyPointCount { get; set; }
        public ulong TotalPointCount { get; set; }
        public double ScaleX { get; set; } = 0.01;
        public double ScaleY { get; set; } = 0.01;
        public double ScaleZ { get; set; } = 0.01;
        public double OffsetX { get; set; }
        public double OffsetY { get; set; }
        public double OffsetZ { get; set; }
        public double MinX { get; set; }
        public double MaxX { get; set; }
        public double MinY { get; set; }
        public double MaxY { get; set; }
        public double MinZ { get; set; }
        public double MaxZ { get; set; }
        public long FileSizeBytes { get; set; }
        public string? CrsWkt { get; set; }
        public int? EpsgCode { get; set; }
        public bool IsProjected => Math.Abs(MinX) > 180 || Math.Abs(MaxX) > 180 || Math.Abs(MinY) > 90 || Math.Abs(MaxY) > 90;
    }

    public class PointRecord
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public ushort Intensity { get; set; }
        public byte Classification { get; set; }
        public byte ReturnNumber { get; set; }
        public byte R { get; set; }
        public byte G { get; set; }
        public byte B { get; set; }
    }

    public class PointCloudStats
    {
        public long TotalPoints { get; set; }
        public double MinX { get; set; }
        public double MaxX { get; set; }
        public double MinY { get; set; }
        public double MaxY { get; set; }
        public double MinZ { get; set; }
        public double MaxZ { get; set; }
        public double AvgZ { get; set; }
        public Dictionary<byte, long> ClassificationBreakdown { get; set; } = new();
    }

    public class PointCloudBatch
    {
        public int count { get; set; }
        public double[] x { get; set; } = Array.Empty<double>();
        public double[] y { get; set; } = Array.Empty<double>();
        public float[] z { get; set; } = Array.Empty<float>();
        public byte[]? r { get; set; }
        public byte[]? g { get; set; }
        public byte[]? b { get; set; }
        public byte[]? c { get; set; }
        public byte[]? i { get; set; }
        public byte[]? rn { get; set; }
        public byte[]? nr { get; set; }
        public byte[]? sa { get; set; }
        public byte[]? ps { get; set; }
        public byte[]? fl { get; set; }
        public byte[]? nir { get; set; }
        public byte[]? t { get; set; }
        public bool hasRgb { get; set; }
    }

    public class LidarClassItemViewModel : System.ComponentModel.INotifyPropertyChanged
    {
        private bool _isSelected = true;
        private System.Windows.Media.SolidColorBrush? _brush;

        public byte ClassId { get; set; }
        public string Name { get; set; } = "";
        public string ColorHex { get; set; } = "#888888";
        public long PointCount { get; set; }
        public double Percentage { get; set; }

        public System.Windows.Media.SolidColorBrush ColorBrush
        {
            get
            {
                if (_brush == null)
                {
                    try
                    {
                        var color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(ColorHex);
                        _brush = new System.Windows.Media.SolidColorBrush(color);
                        _brush.Freeze();
                    }
                    catch
                    {
                        _brush = System.Windows.Media.Brushes.Gray;
                    }
                }
                return _brush;
            }
        }

        public string Label => $"Class {ClassId}: {Name}";
        public string BadgeText => $"{PointCount:N0} pts ({Percentage:F1}%)";
        public string ShortBadgeText => PointCount >= 1_000_000 
            ? $"{PointCount / 1_000_000.0:F1}M" 
            : (PointCount >= 1_000 ? $"{PointCount / 1000.0:F0}K" : $"{PointCount}");

        public bool IsSelected
        {
            get => _isSelected;
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    PropertyChanged?.Invoke(this, new System.ComponentModel.PropertyChangedEventArgs(nameof(IsSelected)));
                }
            }
        }

        public event System.ComponentModel.PropertyChangedEventHandler? PropertyChanged;
    }
}
