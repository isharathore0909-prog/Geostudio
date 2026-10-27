using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using GeoStudio.Routing.Models;

namespace GeoStudio.Routing.Services
{
    public class RoadRoutingService
    {
        private static readonly Lazy<RoadRoutingService> _instance = new(() => new RoadRoutingService());
        public static RoadRoutingService Instance => _instance.Value;

        private RoadGraph? _activeGraph;
        private readonly ShortestPathSolver _solver = new();

        public bool IsGraphLoaded => _activeGraph != null && _activeGraph.NodeCount > 0;
        public int LoadedNodeCount => _activeGraph?.NodeCount ?? 0;
        public int LoadedEdgeCount => _activeGraph?.EdgeCount ?? 0;

        public void SetGraph(RoadGraph graph)
        {
            _activeGraph = graph;
        }

        public RouteGeometryResponse Route(
            double startLng, double startLat,
            double endLng, double endLat,
            RoutingOptimization opt = RoutingOptimization.ShortestDistance)
        {
            if (_activeGraph == null || _activeGraph.NodeCount == 0)
            {
                // Fallback direct geodesic line if no road network graph is loaded
                double directDist = ShortestPathSolver.HaversineMeters(startLat, startLng, endLat, endLng);
                var directCoords = new List<double[]>
                {
                    new double[] { startLng, startLat },
                    new double[] { endLng, endLat }
                };
                return new RouteGeometryResponse
                {
                    Success = true,
                    DistanceKm = directDist / 1000.0,
                    DurationMin = (directDist / 1000.0) / 60.0 * 60.0, // 60 km/h
                    Coordinates = directCoords,
                    GeoJson = ToGeoJson(directCoords, directDist / 1000.0)
                };
            }

            int startNode = RoadSnappingService.SnapToNearestNode(_activeGraph, startLng, startLat);
            int endNode = RoadSnappingService.SnapToNearestNode(_activeGraph, endLng, endLat);

            if (startNode < 0 || endNode < 0)
            {
                return new RouteGeometryResponse
                {
                    Success = false,
                    ErrorMessage = "Unable to snap origin or destination to road network."
                };
            }

            var result = _solver.Solve(_activeGraph, startNode, endNode, opt);

            if (!result.Found)
            {
                return new RouteGeometryResponse
                {
                    Success = false,
                    SearchTimeMs = result.SearchTimeMs,
                    ErrorMessage = "No road path found between the selected points."
                };
            }

            var coordinates = new List<double[]>();
            // Add user start point
            coordinates.Add(new double[] { startLng, startLat });

            foreach (var node in result.PathNodes)
            {
                (double lng, double lat) = _activeGraph.GetNodeCoords(node);
                coordinates.Add(new double[] { lng, lat });
            }

            // Add user end point
            coordinates.Add(new double[] { endLng, endLat });

            string geoJson = ToGeoJson(coordinates, result.TotalDistanceKm);

            return new RouteGeometryResponse
            {
                Success = true,
                DistanceKm = result.TotalDistanceKm,
                DurationMin = result.TotalDurationMinutes,
                SearchTimeMs = result.SearchTimeMs,
                Coordinates = coordinates,
                GeoJson = geoJson
            };
        }

        private static string ToGeoJson(List<double[]> coords, double distKm)
        {
            var feature = new
            {
                type = "FeatureCollection",
                features = new[]
                {
                    new
                    {
                        type = "Feature",
                        properties = new
                        {
                            name = "Optimized Road Route",
                            distance_km = Math.Round(distKm, 2),
                            mode = "Car / Highway"
                        },
                        geometry = new
                        {
                            type = "LineString",
                            coordinates = coords
                        }
                    }
                }
            };

            return JsonSerializer.Serialize(feature);
        }
    }
}
