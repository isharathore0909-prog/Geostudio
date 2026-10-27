using System;
using System.Collections.Generic;
using System.Diagnostics;
using GeoStudio.Routing.Models;

namespace GeoStudio.Routing.Services
{
    public class ShortestPathSolver
    {
        private readonly object _stateLock = new();
        private int _searchIdCounter = 1;
        private int[]? _visitedSearchId;
        private double[]? _gScores;
        private int[]? _parent;
        private float[]? _parentDur;
        private int _allocatedNodeCount = 0;

        private void EnsureBuffers(int nodeCount)
        {
            if (_allocatedNodeCount >= nodeCount && _visitedSearchId != null && _gScores != null && _parent != null && _parentDur != null)
                return;

            _visitedSearchId = new int[nodeCount];
            _gScores = new double[nodeCount];
            _parent = new int[nodeCount];
            _parentDur = new float[nodeCount];
            _allocatedNodeCount = nodeCount;
        }

        public ShortestPathResult Solve(
            RoadGraph graph,
            int startNodeId,
            int endNodeId,
            RoutingOptimization optimization = RoutingOptimization.ShortestDistance)
        {
            if (graph == null || graph.NodeCount == 0)
                return new ShortestPathResult { Found = false, Algorithm = "A* Solver (No Graph Loaded)" };

            var sw = Stopwatch.StartNew();

            if (startNodeId == endNodeId)
            {
                sw.Stop();
                return new ShortestPathResult
                {
                    Found = true,
                    TotalDistanceMeters = 0.0,
                    TotalDurationSeconds = 0.0,
                    PathNodes = new List<int> { startNodeId },
                    NodesExplored = 1,
                    SearchTimeMs = sw.Elapsed.TotalMilliseconds
                };
            }

            lock (_stateLock)
            {
                EnsureBuffers(graph.NodeCount);
                int currentSearchId = ++_searchIdCounter;
                if (_searchIdCounter == int.MaxValue)
                {
                    Array.Clear(_visitedSearchId!, 0, _visitedSearchId!.Length);
                    _searchIdCounter = 1;
                    currentSearchId = 1;
                }

                (double targetLng, double targetLat) = graph.GetNodeCoords(endNodeId);

                var pq = new PriorityQueue<int, double>();
                _gScores![startNodeId] = 0.0;
                _parent![startNodeId] = -1;
                _parentDur![startNodeId] = 0.0f;
                _visitedSearchId![startNodeId] = currentSearchId;

                double initialH = Heuristic(graph, startNodeId, targetLng, targetLat, optimization);
                pq.Enqueue(startNodeId, initialH);

                int nodesExplored = 0;
                bool found = false;

                while (pq.Count > 0)
                {
                    var u = pq.Dequeue();
                    nodesExplored++;

                    if (u == endNodeId)
                    {
                        found = true;
                        break;
                    }

                    double currentG = _gScores[u];
                    int edgeStart = graph.Head[u];
                    int edgeEnd = graph.Head[u + 1];

                    for (int e = edgeStart; e < edgeEnd; e++)
                    {
                        int v = graph.To[e];
                        double weight = optimization == RoutingOptimization.FastestTime
                            ? (graph.DurS.Length > e ? graph.DurS[e] : graph.DistM[e] / 13.88) // 50 km/h default
                            : graph.DistM[e];

                        double tentativeG = currentG + weight;

                        if (_visitedSearchId[v] != currentSearchId || tentativeG < _gScores[v])
                        {
                            _visitedSearchId[v] = currentSearchId;
                            _gScores[v] = tentativeG;
                            _parent[v] = u;
                            _parentDur[v] = graph.DurS.Length > e ? graph.DurS[e] : (float)(weight / 13.88);

                            double h = Heuristic(graph, v, targetLng, targetLat, optimization);
                            pq.Enqueue(v, tentativeG + h);
                        }
                    }
                }

                sw.Stop();

                if (!found)
                {
                    return new ShortestPathResult
                    {
                        Found = false,
                        NodesExplored = nodesExplored,
                        SearchTimeMs = sw.Elapsed.TotalMilliseconds
                    };
                }

                // Reconstruct path
                var path = new List<int>();
                int curr = endNodeId;
                double totalDist = 0.0;
                double totalDur = 0.0;

                while (curr != -1)
                {
                    path.Add(curr);
                    int p = _parent[curr];
                    if (p != -1)
                    {
                        (double pLng, double pLat) = graph.GetNodeCoords(p);
                        (double cLng, double cLat) = graph.GetNodeCoords(curr);
                        totalDist += HaversineMeters(pLat, pLng, cLat, cLng);
                        totalDur += _parentDur[curr];
                    }
                    curr = p;
                }

                path.Reverse();

                return new ShortestPathResult
                {
                    Found = true,
                    TotalDistanceMeters = totalDist,
                    TotalDurationSeconds = totalDur,
                    PathNodes = path,
                    NodesExplored = nodesExplored,
                    SearchTimeMs = sw.Elapsed.TotalMilliseconds
                };
            }
        }

        private static double Heuristic(RoadGraph g, int u, double targetLng, double targetLat, RoutingOptimization opt)
        {
            (double uLng, double uLat) = g.GetNodeCoords(u);
            double distM = HaversineMeters(uLat, uLng, targetLat, targetLng);
            if (opt == RoutingOptimization.FastestTime)
            {
                // Divide by max highway speed (e.g. 120 km/h = 33.33 m/s) to maintain admissibility
                return distM / 33.33;
            }
            return distM;
        }

        public static double HaversineMeters(double lat1, double lon1, double lat2, double lon2)
        {
            const double R = 6371000.0;
            double dLat = (lat2 - lat1) * Math.PI / 180.0;
            double dLon = (lon2 - lon1) * Math.PI / 180.0;
            double a = Math.Sin(dLat / 2) * Math.Sin(dLat / 2) +
                       Math.Cos(lat1 * Math.PI / 180.0) * Math.Cos(lat2 * Math.PI / 180.0) *
                       Math.Sin(dLon / 2) * Math.Sin(dLon / 2);
            double c = 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1 - a));
            return R * c;
        }
    }
}
