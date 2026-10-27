using System;
using GeoStudio.Routing.Models;

namespace GeoStudio.Routing.Services
{
    public class RoadSnappingService
    {
        /// <summary>
        /// Snaps a query coordinate (lng, lat) to the closest node in the road graph.
        /// </summary>
        public static int SnapToNearestNode(RoadGraph graph, double lng, double lat, double maxDistanceMeters = 50000)
        {
            if (graph == null || graph.NodeCount == 0) return -1;

            int bestNode = -1;
            double minDistance = double.MaxValue;

            // Fast Euclidean bounding box filter before haversine
            double latTolerance = maxDistanceMeters / 111000.0;
            double lngTolerance = maxDistanceMeters / (111000.0 * Math.Cos(lat * Math.PI / 180.0));

            for (int i = 0; i < graph.NodeCount; i++)
            {
                (double nodeLng, double nodeLat) = graph.GetNodeCoords(i);

                if (Math.Abs(nodeLat - lat) > latTolerance || Math.Abs(nodeLng - lng) > lngTolerance)
                    continue;

                double d = ShortestPathSolver.HaversineMeters(lat, lng, nodeLat, nodeLng);
                if (d < minDistance)
                {
                    minDistance = d;
                    bestNode = i;
                }
            }

            // Fallback: If no node within tolerance, scan with coarse step to find absolute nearest
            if (bestNode == -1)
            {
                for (int i = 0; i < graph.NodeCount; i += 10)
                {
                    (double nodeLng, double nodeLat) = graph.GetNodeCoords(i);
                    double d = ShortestPathSolver.HaversineMeters(lat, lng, nodeLat, nodeLng);
                    if (d < minDistance)
                    {
                        minDistance = d;
                        bestNode = i;
                    }
                }
            }

            return bestNode;
        }
    }
}
