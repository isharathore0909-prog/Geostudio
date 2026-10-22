using System;

namespace GeoStudio.Raster
{
    public class GdalRasterMetadata
    {
        public int Width { get; set; }
        public int Height { get; set; }
        public int BandCount { get; set; }
        public double[] BoundingBox { get; set; } = new double[4]; // minLon, minLat, maxLon, maxLat (EPSG:4326)
        public string Projection { get; set; } = "EPSG:4326";
        public string PreviewImagePath { get; set; } = string.Empty;
        public string PreviewUrl { get; set; } = string.Empty;
        public string PreviewDataUri => PreviewUrl;
        public bool IsElevation { get; set; }
        public double MinElevation { get; set; }
        public double MaxElevation { get; set; }
    }

    public class WindowRenderResult
    {
        public bool Success { get; set; }
        public string ImageUrl { get; set; } = string.Empty;
        public double[] Extent { get; set; } = new double[4]; // minLon, minLat, maxLon, maxLat
    }
}
