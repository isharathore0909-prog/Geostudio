using System.Collections.Generic;

namespace GeoStudio.Routing.Models
{
    public class RoutingPoint
    {
        public double Longitude { get; set; }
        public double Latitude { get; set; }
        public string? Name { get; set; }
    }

    public class ShortestPathResult
    {
        public bool Found { get; set; }
        public double TotalDistanceMeters { get; set; }
        public double TotalDurationSeconds { get; set; }
        public List<int> PathNodes { get; set; } = new List<int>();
        public int NodesExplored { get; set; }
        public double SearchTimeMs { get; set; }
        public string Algorithm { get; set; } = "CSR Geodesic A*";

        public double TotalDistanceKm => TotalDistanceMeters / 1000.0;
        public double TotalDurationMinutes => TotalDurationSeconds / 60.0;
    }

    public class RouteGeometryResponse
    {
        public bool Success { get; set; }
        public double DistanceKm { get; set; }
        public double DurationMin { get; set; }
        public double SearchTimeMs { get; set; }
        public List<double[]> Coordinates { get; set; } = new List<double[]>(); // [lng, lat]
        public string? GeoJson { get; set; }
        public string? ErrorMessage { get; set; }
    }

    public enum RoutingOptimization
    {
        ShortestDistance,
        FastestTime
    }
}
