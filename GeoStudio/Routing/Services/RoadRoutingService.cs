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

        private static readonly System.Net.Http.HttpClient _httpClient = CreateHttpClient();

        private static System.Net.Http.HttpClient CreateHttpClient()
        {
            var client = new System.Net.Http.HttpClient { Timeout = TimeSpan.FromSeconds(8) };
            client.DefaultRequestHeaders.Add("User-Agent", "GeoStudio/3.0 (RoadRoutingEngine)");
            return client;
        }

        public RouteGeometryResponse RouteAerial(double startLng, double startLat, double endLng, double endLat)
        {
            double directDist = ShortestPathSolver.HaversineMeters(startLat, startLng, endLat, endLng);
            var directCoords = new List<double[]>
            {
                new double[] { startLng, startLat },
                new double[] { endLng, endLat }
            };
            double distKm = directDist / 1000.0;
            return new RouteGeometryResponse
            {
                Success = true,
                DistanceKm = distKm,
                DurationMin = (distKm / 120.0) * 60.0,
                Coordinates = directCoords,
                GeoJson = ToGeoJson(directCoords, distKm, "Direct Aerial Air Line")
            };
        }

        public RouteGeometryResponse Route(
            double startLng, double startLat,
            double endLng, double endLat,
            RoutingOptimization opt = RoutingOptimization.ShortestDistance)
        {
            // 1. If an offline CSR Road Graph is loaded, solve with A*
            if (_activeGraph != null && _activeGraph.NodeCount > 0)
            {
                var graphRoute = RouteWithGraph(startLng, startLat, endLng, endLat, opt);
                if (graphRoute.Success) return graphRoute;
            }

            // 2. Query real-world road network driving engine (OSRM)
            var roadRoute = RouteWithOsrm(startLng, startLat, endLng, endLat);
            if (roadRoute.Success)
            {
                return roadRoute;
            }

            // 3. Fallback direct geodesic line if network unavailable
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
                DurationMin = (directDist / 1000.0) / 50.0 * 60.0, // 50 km/h
                Coordinates = directCoords,
                GeoJson = ToGeoJson(directCoords, directDist / 1000.0)
            };
        }

        private RouteGeometryResponse RouteWithOsrm(double sLng, double sLat, double eLng, double eLat)
        {
            try
            {
                string url = FormattableString.Invariant(
                    $"https://router.project-osrm.org/route/v1/driving/{sLng:F6},{sLat:F6};{eLng:F6},{eLat:F6}?overview=full&geometries=geojson");

                string json = _httpClient.GetStringAsync(url).GetAwaiter().GetResult();
                using var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;

                if (root.TryGetProperty("code", out var code) && code.GetString() == "Ok" &&
                    root.TryGetProperty("routes", out var routes) && routes.GetArrayLength() > 0)
                {
                    var primary = routes[0];
                    double distanceMeters = primary.GetProperty("distance").GetDouble();
                    double durationSeconds = primary.GetProperty("duration").GetDouble();

                    var coordinates = new List<double[]>();
                    if (primary.TryGetProperty("geometry", out var geom) &&
                        geom.TryGetProperty("coordinates", out var coordsArray))
                    {
                        foreach (var pt in coordsArray.EnumerateArray())
                        {
                            if (pt.GetArrayLength() >= 2)
                            {
                                coordinates.Add(new double[] { pt[0].GetDouble(), pt[1].GetDouble() });
                            }
                        }
                    }

                    if (coordinates.Count == 0)
                    {
                        coordinates.Add(new double[] { sLng, sLat });
                        coordinates.Add(new double[] { eLng, eLat });
                    }

                    double distKm = distanceMeters / 1000.0;
                    double durMin = durationSeconds / 60.0;

                    return new RouteGeometryResponse
                    {
                        Success = true,
                        DistanceKm = distKm,
                        DurationMin = durMin,
                        Coordinates = coordinates,
                        GeoJson = ToGeoJson(coordinates, distKm)
                    };
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[OSRM Road Routing Warning]: {ex.Message}");
            }

            return new RouteGeometryResponse { Success = false };
        }

        private RouteGeometryResponse RouteWithGraph(
            double startLng, double startLat,
            double endLng, double endLat,
            RoutingOptimization opt)
        {
            if (_activeGraph == null) return new RouteGeometryResponse { Success = false };

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

        private static string ToGeoJson(List<double[]> coords, double distKm, string mode = "Car / Highway")
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
                            name = mode == "Direct Aerial Air Line" ? "Aerial Direct Line" : "Optimized Road Route",
                            distance_km = Math.Round(distKm, 2),
                            mode = mode
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
