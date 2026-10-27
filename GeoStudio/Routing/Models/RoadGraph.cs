using System;

namespace GeoStudio.Routing.Models
{
    /// <summary>
    /// Compressed Sparse Row (CSR) road graph representation for high-speed offline routing.
    /// Memory footprint: ~55MB for 1M nodes and 2.8M edges.
    /// </summary>
    public class RoadGraph
    {
        public int NodeCount { get; }
        public int EdgeCount { get; }
        public double[] NodesWgs { get; } // Flat array: [lng0, lat0, lng1, lat1, ...]
        public int[] Head { get; }        // CSR head pointers of size NodeCount + 1
        public int[] To { get; }          // CSR destination node indices of size EdgeCount
        public float[] DistM { get; }     // Edge distance in meters
        public float[] DurS { get; }      // Edge travel duration in seconds

        public RoadGraph(
            int nodeCount,
            int edgeCount,
            double[] nodesWgs,
            int[] head,
            int[] to,
            float[] distM,
            float[] durS)
        {
            NodeCount = nodeCount;
            EdgeCount = edgeCount;
            NodesWgs = nodesWgs ?? Array.Empty<double>();
            Head = head ?? Array.Empty<int>();
            To = to ?? Array.Empty<int>();
            DistM = distM ?? Array.Empty<float>();
            DurS = durS ?? Array.Empty<float>();
        }

        public (double Lng, double Lat) GetNodeCoords(int nodeId)
        {
            if (nodeId < 0 || nodeId >= NodeCount) return (0, 0);
            int offset = nodeId * 2;
            return (NodesWgs[offset], NodesWgs[offset + 1]);
        }
    }
}
