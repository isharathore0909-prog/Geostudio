using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;
using GeoStudio.Models;
using GeoStudio.Raster;
using OSGeo.GDAL;
using OSGeo.OGR;
using OSGeo.OSR;

namespace GeoStudio
{
    public partial class MainWindow
    {
        internal void BtnAddVector_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Title = "Open Vector Dataset",
                Filter = "Vector Files (*.geojson;*.json;*.shp;*.gpkg;*.kml)|*.geojson;*.json;*.shp;*.gpkg;*.kml|All Files (*.*)|*.*"
            };

            if (dlg.ShowDialog() == true)
            {
                LoadVectorFile(dlg.FileName);
            }
        }

        public async void LoadVectorFile(string filePath, string? customColor = null, bool isContour = false, bool zoomTo = true, double? contourInterval = null)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath)) return;
            var sw = Stopwatch.StartNew();
            if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Visible;
            if (TxtBenchmarkFileName != null) TxtBenchmarkFileName.Text = Path.GetFileName(filePath);
            if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = "Loading...";
            if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Visible;
            if (TxtBenchmarkStatusIcon != null)
            {
                TxtBenchmarkStatusIcon.Text = "⏳";
                TxtBenchmarkStatusIcon.Foreground = new SolidColorBrush(Color.FromRgb(245, 158, 11));
            }

            var fileInfo = new FileInfo(filePath);
            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            bool isGeoJson = ext == ".geojson" || ext == ".json";
            bool isContourDetected = isContour || filePath.Contains("contour", StringComparison.OrdinalIgnoreCase);

            string layerId = Guid.NewGuid().ToString("N");
            string layerName = Path.GetFileNameWithoutExtension(filePath);
            string colorHex = customColor ?? (isContourDetected ? "#D97706" : "#10B981");

            if (TxtBenchmarkStatus != null)
                TxtBenchmarkStatus.Text = isGeoJson ? "Parsing GeoJSON geometries..." : "Converting vector geometries for GPU canvas...";
            if (TxtBenchmarkBreakdown != null)
                TxtBenchmarkBreakdown.Text = isGeoJson ? "Reading vector features..." : $"Translating {ext.ToUpperInvariant().TrimStart('.')} dataset to WGS84 GeoJSON...";

            string cacheDir = GdalRasterService.GetCacheDirectory();
            string safeName = Path.GetFileNameWithoutExtension(filePath);
            long mtime = fileInfo.LastWriteTimeUtc.Ticks;
            long fLen = fileInfo.Length;
            string cacheKey = $"{filePath}_{mtime}_{fLen}";
            string hash = Convert.ToHexString(System.Security.Cryptography.MD5.HashData(System.Text.Encoding.UTF8.GetBytes(cacheKey)))[..8].ToLowerInvariant();
            string cacheFileName = $"vector_{safeName}_{hash}.geojson";
            string cacheFilePath = Path.Combine(cacheDir, cacheFileName);

            int featureCount = 0;
            double[]? bounds = null;
            var attributeFields = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);

            try
            {
                await Task.Run(() =>
                {
                    if (isGeoJson)
                    {
                        if (!File.Exists(cacheFilePath) || new FileInfo(cacheFilePath).Length != fileInfo.Length)
                        {
                            File.Copy(filePath, cacheFilePath, true);
                        }

                        using var fs = File.OpenRead(cacheFilePath);
                        using var doc = JsonDocument.Parse(fs);
                        var root = doc.RootElement;
                        if (root.TryGetProperty("features", out var feats) && feats.ValueKind == JsonValueKind.Array)
                        {
                            featureCount = feats.GetArrayLength();
                            double minX = double.PositiveInfinity, minY = double.PositiveInfinity;
                            double maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;
                            int idx = 0;
                            foreach (var feat in feats.EnumerateArray())
                            {
                                if (idx < 50 && feat.TryGetProperty("properties", out var props) && props.ValueKind == JsonValueKind.Object)
                                {
                                    foreach (var p in props.EnumerateObject())
                                    {
                                        attributeFields.Add(p.Name);
                                    }
                                }

                                if (idx++ > 3000) break;
                                if (feat.TryGetProperty("geometry", out var geom) && geom.TryGetProperty("coordinates", out var coords))
                                {
                                    ExtractBounds(coords, ref minX, ref minY, ref maxX, ref maxY);
                                }
                            }
                            if (!double.IsInfinity(minX) && !double.IsInfinity(minY))
                            {
                                bounds = new double[] { minX, minY, maxX, maxY };
                            }
                        }
                    }
                    else
                    {
                        // OGR / GDAL Vector Translation for Shapefiles (.shp), GeoPackage (.gpkg), KML, etc.
                        GdalRasterService.Initialize();

                        using var srcDs = Gdal.OpenEx(filePath, 4, null, null, null); // 4 = GDAL_OF_VECTOR
                        if (srcDs != null && srcDs.GetLayerCount() > 0)
                        {
                            // 1. Fast metadata extraction directly from vector driver
                            try
                            {
                                using var ogrLayer = srcDs.GetLayer(0);
                                featureCount = (int)ogrLayer.GetFeatureCount(1);

                                Envelope env = new Envelope();
                                ogrLayer.GetExtent(env, 1);

                                SpatialReference srs = ogrLayer.GetSpatialRef();
                                using var wgs84 = new SpatialReference("");
                                wgs84.ImportFromEPSG(4326);

                                double minX = env.MinX, minY = env.MinY, maxX = env.MaxX, maxY = env.MaxY;
                                if (srs != null && srs.IsSame(wgs84, null) == 0)
                                {
                                    using var ct = new CoordinateTransformation(srs, wgs84);
                                    double[] p1 = new double[] { env.MinX, env.MinY, 0 };
                                    double[] p2 = new double[] { env.MaxX, env.MaxY, 0 };
                                    ct.TransformPoint(p1);
                                    ct.TransformPoint(p2);

                                    double c1 = p1[0], c2 = p1[1];
                                    double c3 = p2[0], c4 = p2[1];
                                    if (Math.Abs(c1) <= 90 && Math.Abs(c2) <= 180 && (Math.Abs(c2) > 90 || Math.Abs(c1) < Math.Abs(c2)))
                                    {
                                        minX = Math.Min(c2, c4);
                                        maxX = Math.Max(c2, c4);
                                        minY = Math.Min(c1, c3);
                                        maxY = Math.Max(c1, c3);
                                    }
                                    else
                                    {
                                        minX = Math.Min(c1, c3);
                                        maxX = Math.Max(c1, c3);
                                        minY = Math.Min(c2, c4);
                                        maxY = Math.Max(c2, c4);
                                    }
                                }
                                else
                                {
                                    minX = Math.Min(env.MinX, env.MaxX);
                                    maxX = Math.Max(env.MinX, env.MaxX);
                                    minY = Math.Min(env.MinY, env.MaxY);
                                    maxY = Math.Max(env.MinY, env.MaxY);
                                }

                                if (!double.IsInfinity(minX) && !double.IsInfinity(minY) && Math.Abs(minX) <= 180 && Math.Abs(minY) <= 90)
                                {
                                    bounds = new double[] { minX, minY, maxX, maxY };
                                }

                                var defn = ogrLayer.GetLayerDefn();
                                int fCount = defn.GetFieldCount();
                                for (int i = 0; i < Math.Min(fCount, 50); i++)
                                {
                                    attributeFields.Add(defn.GetFieldDefn(i).GetName());
                                }
                            }
                            catch (Exception ex)
                            {
                                Debug.WriteLine($"OGR metadata read error: {ex.Message}");
                            }

                            // 2. Convert to optimized WGS84 GeoJSON if not cached
                            bool needsConversion = !File.Exists(cacheFilePath) || new FileInfo(cacheFilePath).Length == 0;
                            if (needsConversion)
                            {
                                string tempPath = cacheFilePath + ".tmp";
                                if (File.Exists(tempPath)) File.Delete(tempPath);

                                var options = new GDALVectorTranslateOptions(new[] {
                                    "-f", "GeoJSON",
                                    "-t_srs", "EPSG:4326",
                                    "-lco", "COORDINATE_PRECISION=6",
                                    "-skipfailures"
                                });

                                // Explicit using block ensures outDs is disposed and the file handle released before File.Move
                                using (var outDs = Gdal.wrapper_GDALVectorTranslateDestName(tempPath, srcDs, options, null, null))
                                {
                                }

                                if (File.Exists(tempPath) && new FileInfo(tempPath).Length > 0)
                                {
                                    if (File.Exists(cacheFilePath)) File.Delete(cacheFilePath);
                                    File.Move(tempPath, cacheFilePath, true);
                                }
                            }
                        }
                    }
                });
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Vector loading failed: {ex.Message}");
                if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = $"Load Error: {ex.Message}";
                return;
            }

            long readMs = sw.ElapsedMilliseconds;
            string readText = readMs >= 1000 ? $"{readMs / 1000.0:F2}s" : $"{readMs}ms";

            var layer = new LayerItem
            {
                Id = layerId,
                Name = layerName,
                Type = LayerType.Vector,
                FilePath = filePath,
                FileSizeBytes = fileInfo.Length,
                Details = isContourDetected
                    ? $"CONTOURS | {(featureCount > 0 ? $"{featureCount:N0} segments • " : "")}{fileInfo.Length / 1024.0:F1} KB"
                    : $"{ext.ToUpperInvariant().TrimStart('.')} | {(featureCount > 0 ? $"{featureCount:N0} features • " : "")}{fileInfo.Length / 1024.0:F1} KB",
                ColorHex = colorHex,
                FillColorHex = colorHex,
                StrokeWidth = 1.6,
                FillOpacity = 0.28,
                FeatureCount = featureCount,
                BoundingBox = bounds,
                AttributeFields = System.Linq.Enumerable.ToList(attributeFields),
                GeoJsonCachePath = cacheFilePath,
                LoadTimeText = readText,
                CanvasRenderTimeText = "Rendering...",
                TotalDurationText = readText,
                UseGpuAcceleration = true
            };
            Layers.Add(layer);
            UpdateLayerCount();

            bool isHeavy = fileInfo.Length > 1024 * 1024 || featureCount > 300;

            bool isDrainageStream = !isContourDetected && (
                layerName.Contains("stream", StringComparison.OrdinalIgnoreCase) ||
                layerName.Contains("drainage", StringComparison.OrdinalIgnoreCase) ||
                filePath.Contains("stream", StringComparison.OrdinalIgnoreCase) ||
                filePath.Contains("drainage", StringComparison.OrdinalIgnoreCase));

            bool isPointOrCentroid = layerName.Contains("centroid", StringComparison.OrdinalIgnoreCase) ||
                layerName.Contains("point", StringComparison.OrdinalIgnoreCase) ||
                filePath.Contains("centroid", StringComparison.OrdinalIgnoreCase) ||
                filePath.Contains("point", StringComparison.OrdinalIgnoreCase);

            int vectorZIndex = isPointOrCentroid ? 30 : (isDrainageStream ? 25 : 12);

            if (File.Exists(cacheFilePath))
            {
                if (TxtBenchmarkStatus != null) TxtBenchmarkStatus.Text = "Rendering vector onto GPU map canvas...";
                if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = $"File Ingest: {readText} • Awaiting GPU Canvas Paint...";

                PostMessageToMap(new
                {
                    action = "addVectorLayer",
                    id = layer.Id,
                    name = layer.Name,
                    url = $"http://cache.geostudio.local/{cacheFileName}",
                    bounds = bounds,
                    isContour = isContourDetected,
                    isStream = isDrainageStream,
                    isPoint = isPointOrCentroid,
                    zIndex = vectorZIndex,
                    interval = contourInterval ?? 10.0,
                    color = colorHex,
                    fileSizeBytes = fileInfo.Length,
                    featureCount = featureCount,
                    fileLoadMs = readMs,
                    useGpu = true,
                    isHeavy = isHeavy
                });
            }

            TxtStatus.Text = $"Loading vector dataset onto canvas: {layer.Name} ({(featureCount > 0 ? $"{featureCount:N0} features, " : "")}{readText})...";
        }

        private static void ExtractBounds(JsonElement elem, ref double minX, ref double minY, ref double maxX, ref double maxY)
        {
            if (elem.ValueKind == JsonValueKind.Array)
            {
                int count = elem.GetArrayLength();
                if (count >= 2 && elem[0].ValueKind == JsonValueKind.Number && elem[1].ValueKind == JsonValueKind.Number)
                {
                    double x = elem[0].GetDouble();
                    double y = elem[1].GetDouble();
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                    if (y < minY) minY = y;
                    if (y > maxY) maxY = y;
                }
                else
                {
                    foreach (var child in elem.EnumerateArray())
                    {
                        ExtractBounds(child, ref minX, ref minY, ref maxX, ref maxY);
                    }
                }
            }
        }
    }
}
