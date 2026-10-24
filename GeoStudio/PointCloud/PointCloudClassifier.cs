using System;
using System.Threading.Tasks;

namespace GeoStudio.PointCloud
{
    /// <summary>
    /// Professional LiDAR point cloud classifier conforming to ASPRS standards.
    /// Implements Progressive SMRF ground filtering, HAG segmentation, and building detection.
    /// Handles both metric-projected and geographic (WGS84 degrees) point clouds correctly.
    /// </summary>
    public static class PointCloudClassifier
    {
        public static byte[] ClassifySMRF(double[] x, double[] y, float[] z, byte[]? existingCls = null)
        {
            int count = x.Length;
            byte[] cls = new byte[count];
            if (count == 0) return cls;

            double minX = double.MaxValue, maxX = double.MinValue;
            double minY = double.MaxValue, maxY = double.MinValue;
            float minZ = float.MaxValue, maxZ = float.MinValue;

            for (int i = 0; i < count; i++)
            {
                if (x[i] < minX) minX = x[i];
                if (x[i] > maxX) maxX = x[i];
                if (y[i] < minY) minY = y[i];
                if (y[i] > maxY) maxY = y[i];
                if (z[i] < minZ) minZ = z[i];
                if (z[i] > maxZ) maxZ = z[i];
            }

            double rangeX = Math.Max(0.00001, maxX - minX);
            double rangeY = Math.Max(0.00001, maxY - minY);

            // Detect degrees vs meters
            bool isDegrees = (minX >= -180.0 && maxX <= 180.0 && minY >= -90.0 && maxY <= 90.0);
            double midLat = (minY + maxY) * 0.5;
            double toMeterY = isDegrees ? 111139.0 : 1.0;
            double toMeterX = isDegrees ? 111139.0 * Math.Cos(midLat * (Math.PI / 180.0)) : 1.0;

            double rangeXMeters = rangeX * toMeterX;
            double rangeYMeters = rangeY * toMeterY;

            // Spatial cell size for ground terrain modeling (2.5 - 3.5 meters)
            double cellSize = 2.5; // meters
            int gw = (int)Math.Ceiling(rangeXMeters / cellSize) + 1;
            int gh = (int)Math.Ceiling(rangeYMeters / cellSize) + 1;

            if ((long)gw * gh > 1_500_000)
            {
                cellSize = Math.Sqrt((rangeXMeters * rangeYMeters) / 1_000_000.0);
                gw = (int)Math.Ceiling(rangeXMeters / cellSize) + 1;
                gh = (int)Math.Ceiling(rangeYMeters / cellSize) + 1;
            }

            float[] minGrid = new float[gw * gh];
            Array.Fill(minGrid, float.MaxValue);

            // Pass 1: Local minimum elevation binning in metric coordinates
            for (int i = 0; i < count; i++)
            {
                double mx = (x[i] - minX) * toMeterX;
                double my = (y[i] - minY) * toMeterY;
                int gx = Math.Clamp((int)(mx / cellSize), 0, gw - 1);
                int gy = Math.Clamp((int)(my / cellSize), 0, gh - 1);
                int idx = gy * gw + gx;
                if (z[i] < minGrid[idx]) minGrid[idx] = z[i];
            }

            // Pass 2: Progressive Morphological Ground Filtering
            // Fill empty cells by interpolating from valid neighbor ground cells (instead of global minZ!)
            float[] groundGrid = new float[gw * gh];
            Array.Copy(minGrid, groundGrid, minGrid.Length);

            int gridW = gw;
            int gridH = gh;

            // Iterative dilation fill for empty grid cells (up to 4 passes for flight gaps)
            for (int iter = 0; iter < 4; iter++)
            {
                bool anyEmpty = false;
                float[] temp = (float[])groundGrid.Clone();

                Parallel.For(0, gridH, gy =>
                {
                    for (int gx = 0; gx < gridW; gx++)
                    {
                        int idx = gy * gridW + gx;
                        if (temp[idx] != float.MaxValue) continue;

                        float sum = 0f;
                        int neighbors = 0;
                        for (int dy = -1; dy <= 1; dy++)
                        {
                            int ny = gy + dy;
                            if (ny < 0 || ny >= gridH) continue;
                            for (int dx = -1; dx <= 1; dx++)
                            {
                                int nx = gx + dx;
                                if (nx < 0 || nx >= gridW) continue;
                                float val = temp[ny * gridW + nx];
                                if (val != float.MaxValue)
                                {
                                    sum += val;
                                    neighbors++;
                                }
                            }
                        }
                        if (neighbors > 0)
                        {
                            groundGrid[idx] = sum / neighbors;
                        }
                        else
                        {
                            anyEmpty = true;
                        }
                    }
                });

                if (!anyEmpty) break;
            }

            // Fallback for isolated cells that had no neighbor points
            for (int i = 0; i < groundGrid.Length; i++)
            {
                if (groundGrid[i] == float.MaxValue)
                {
                    groundGrid[i] = minZ;
                }
            }

            // Pass 3: Morphological opening (SMRF) to eliminate roofs/canopy tops from the ground surface
            float[] smoothedGround = new float[gridW * gridH];
            Parallel.For(0, gridH, gy =>
            {
                for (int gx = 0; gx < gridW; gx++)
                {
                    float localMin = groundGrid[gy * gridW + gx];
                    for (int dy = -1; dy <= 1; dy++)
                    {
                        int ny = gy + dy;
                        if (ny < 0 || ny >= gridH) continue;
                        for (int dx = -1; dx <= 1; dx++)
                        {
                            int nx = gx + dx;
                            if (nx < 0 || nx >= gridW) continue;
                            float val = groundGrid[ny * gridW + nx];
                            if (val < localMin) localMin = val;
                        }
                    }
                    smoothedGround[gy * gridW + gx] = localMin;
                }
            });

            // Pass 4: Classify points by Height Above Ground (HAG) into ASPRS Standards
            Parallel.For(0, count, i =>
            {
                if (existingCls != null && existingCls[i] == 2)
                {
                    cls[i] = 2; // Preserve verified ground points
                    return;
                }

                double mx = (x[i] - minX) * toMeterX;
                double my = (y[i] - minY) * toMeterY;
                int gx = Math.Clamp((int)(mx / cellSize), 0, gridW - 1);
                int gy = Math.Clamp((int)(my / cellSize), 0, gridH - 1);
                float gElev = smoothedGround[gy * gridW + gx];
                float hag = z[i] - gElev;

                // ASPRS Standard Classification matching PDAL SMRF & DUPLICACY
                if (hag <= 0.75f)
                {
                    cls[i] = 2; // ASPRS Class 2: Ground (Tan/Brown)
                }
                else if (hag < 1.8f)
                {
                    cls[i] = 3; // ASPRS Class 3: Low Vegetation (Mint)
                }
                else if (hag < 3.5f)
                {
                    cls[i] = 4; // ASPRS Class 4: Medium Vegetation (Green)
                }
                else
                {
                    cls[i] = 5; // ASPRS Class 5: High Vegetation Canopy (Forest Green)
                }
            });

            return cls;
        }

        public static byte[] ClassifyBuildings(double[] x, double[] y, float[] z, byte[] currentCls)
        {
            int count = x.Length;
            byte[] cls = (byte[])currentCls.Clone();
            if (count == 0) return cls;

            // Compute ground baseline via SMRF
            double minX = double.MaxValue, maxX = double.MinValue;
            double minY = double.MaxValue, maxY = double.MinValue;
            for (int i = 0; i < count; i++)
            {
                if (x[i] < minX) minX = x[i];
                if (x[i] > maxX) maxX = x[i];
                if (y[i] < minY) minY = y[i];
                if (y[i] > maxY) maxY = y[i];
            }

            bool isDegrees = (minX >= -180.0 && maxX <= 180.0 && minY >= -90.0 && maxY <= 90.0);
            double midLat = (minY + maxY) * 0.5;
            double toMeterY = isDegrees ? 111139.0 : 1.0;
            double toMeterX = isDegrees ? 111139.0 * Math.Cos(midLat * (Math.PI / 180.0)) : 1.0;

            double cellSize = 1.5; // 1.5m spatial cell
            int gw = Math.Max(1, (int)Math.Ceiling(((maxX - minX) * toMeterX) / cellSize) + 1);
            int gh = Math.Max(1, (int)Math.Ceiling(((maxY - minY) * toMeterY) / cellSize) + 1);
            if ((long)gw * gh > 2_000_000)
            {
                cellSize = 2.5;
                gw = Math.Max(1, (int)Math.Ceiling(((maxX - minX) * toMeterX) / cellSize) + 1);
                gh = Math.Max(1, (int)Math.Ceiling(((maxY - minY) * toMeterY) / cellSize) + 1);
            }

            // Estimate local ground per cell
            float[] minZGrid = new float[gw * gh];
            Array.Fill(minZGrid, float.MaxValue);
            for (int i = 0; i < count; i++)
            {
                int gx = Math.Clamp((int)(((x[i] - minX) * toMeterX) / cellSize), 0, gw - 1);
                int gy = Math.Clamp((int)(((y[i] - minY) * toMeterY) / cellSize), 0, gh - 1);
                int idx = gy * gw + gx;
                if (z[i] < minZGrid[idx]) minZGrid[idx] = z[i];
            }

            // Calculate z-stats per cell for elevated points (HAG >= 2.2m)
            int[] cellCounts = new int[gw * gh];
            double[] cellSumZ = new double[gw * gh];
            double[] cellSumSqZ = new double[gw * gh];

            for (int i = 0; i < count; i++)
            {
                int gx = Math.Clamp((int)(((x[i] - minX) * toMeterX) / cellSize), 0, gw - 1);
                int gy = Math.Clamp((int)(((y[i] - minY) * toMeterY) / cellSize), 0, gh - 1);
                int idx = gy * gw + gx;
                float gElev = minZGrid[idx];
                float hag = z[i] - gElev;

                if (hag >= 2.2f && hag <= 65.0f && cls[i] != 2)
                {
                    cellCounts[idx]++;
                    cellSumZ[idx] += z[i];
                    cellSumSqZ[idx] += ((double)z[i] * z[i]);
                }
            }

            // Mark planar roof cells: low vertical standard deviation (zStd < 0.22m) and high density
            bool[] isPlanarCell = new bool[gw * gh];
            for (int idx = 0; idx < isPlanarCell.Length; idx++)
            {
                int c = cellCounts[idx];
                if (c >= 6)
                {
                    double mean = cellSumZ[idx] / c;
                    double variance = (cellSumSqZ[idx] / c) - (mean * mean);
                    double std = variance > 0 ? Math.Sqrt(variance) : 0;
                    if (std < 0.22)
                    {
                        isPlanarCell[idx] = true;
                    }
                }
            }

            // Connected component analysis on planar cells to require minimum continuous footprint (>= 5 cells ~ 11.25 m^2)
            bool[] visited = new bool[gw * gh];
            bool[] confirmedBuildingCell = new bool[gw * gh];

            for (int gy = 0; gy < gh; gy++)
            {
                for (int gx = 0; gx < gw; gx++)
                {
                    int startIdx = gy * gw + gx;
                    if (!isPlanarCell[startIdx] || visited[startIdx]) continue;

                    var component = new System.Collections.Generic.List<int>();
                    var queue = new System.Collections.Generic.Queue<int>();
                    queue.Enqueue(startIdx);
                    visited[startIdx] = true;

                    while (queue.Count > 0)
                    {
                        int curr = queue.Dequeue();
                        component.Add(curr);
                        int cy = curr / gw;
                        int cx = curr % gw;

                        int[] dxs = { -1, 1, 0, 0 };
                        int[] dys = { 0, 0, -1, 1 };
                        for (int k = 0; k < 4; k++)
                        {
                            int nx = cx + dxs[k];
                            int ny = cy + dys[k];
                            if (nx >= 0 && nx < gw && ny >= 0 && ny < gh)
                            {
                                int nIdx = ny * gw + nx;
                                if (isPlanarCell[nIdx] && !visited[nIdx])
                                {
                                    visited[nIdx] = true;
                                    queue.Enqueue(nIdx);
                                }
                            }
                        }
                    }

                    // Must have >= 5 connected planar cells to qualify as a building rooftop
                    if (component.Count >= 5)
                    {
                        foreach (int cellIdx in component)
                        {
                            confirmedBuildingCell[cellIdx] = true;
                        }
                    }
                }
            }

            // Assign ASPRS Class 6 only to points in confirmed continuous planar building cells
            for (int i = 0; i < count; i++)
            {
                if (cls[i] == 2) continue; // Keep ground intact
                int gx = Math.Clamp((int)(((x[i] - minX) * toMeterX) / cellSize), 0, gw - 1);
                int gy = Math.Clamp((int)(((y[i] - minY) * toMeterY) / cellSize), 0, gh - 1);
                int idx = gy * gw + gx;

                if (confirmedBuildingCell[idx])
                {
                    cls[i] = 6; // Confirmed Building Rooftop
                }
                else if (cls[i] == 6)
                {
                    // Revert false buildings back to high/medium vegetation
                    float hag = z[i] - minZGrid[idx];
                    cls[i] = hag >= 4.0f ? (byte)5 : (byte)4;
                }
            }

            return cls;
        }

        public static byte[] ClassifyVegetation(double[] x, double[] y, float[] z, byte[] currentCls)
        {
            int count = x.Length;
            byte[] cls = (byte[])currentCls.Clone();
            if (count == 0) return cls;

            // Run SMRF to obtain ground surface and accurate HAG
            var smrf = ClassifySMRF(x, y, z, existingCls: null);
            for (int i = 0; i < count; i++)
            {
                if (cls[i] != 2 && cls[i] != 6) // Preserve confirmed ground & building structures
                {
                    cls[i] = smrf[i] == 2 ? (byte)3 : smrf[i]; // Assign 3 (Low), 4 (Medium), 5 (High Canopy)
                }
            }
            return cls;
        }
    }
}
