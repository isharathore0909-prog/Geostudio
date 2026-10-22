using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using GeoStudio.Models;
using GeoStudio.Raster;
using GeoStudio.PointCloud;

namespace GeoStudio
{
    public partial class MainWindow
    {
        private void CoreWebView2_WebMessageReceived(object? sender, Microsoft.Web.WebView2.Core.CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                using var doc = JsonDocument.Parse(e.WebMessageAsJson);
                var root = doc.RootElement;
                if (!root.TryGetProperty("action", out var actionProp)) return;

                string action = actionProp.GetString() ?? "";

                if (action == "ready")
                {
                    _isMapReady = true;
                    MapWebView.Visibility = Visibility.Visible;
                    MapLoadingOverlay.Visibility = Visibility.Collapsed;
                    TxtStatus.Text = "Map Engine Ready (GPU WebGL Accelerated)";
                }
                else if (action == "pointerMove")
                {
                    string lon = root.GetProperty("lon").GetString() ?? "0.0";
                    string lat = root.GetProperty("lat").GetString() ?? "0.0";
                    int elev = root.GetProperty("elev").GetInt32();
                    string scale = root.GetProperty("scale").GetString() ?? "1:1";

                    TxtCoords.Text = $"X: {lon}   Y: {lat}";
                    TxtElevation.Text = $"Elev: {elev} m";
                    TxtScale.Text = $"Scale: 1:{scale}";
                }
                else if (action == "digitizedFeature")
                {
                    string featType = root.GetProperty("type").GetString() ?? "Feature";
                    int count = root.GetProperty("count").GetInt32();

                    TxtStatus.Text = $"Digitized {featType} (Total features: {count})";

                    var activeVector = FindLayer("vector_active");
                    if (activeVector == null)
                    {
                        activeVector = new LayerItem
                        {
                            Id = "vector_active",
                            Name = "Digitized Vectors",
                            Type = LayerType.Vector,
                            IsVisible = true,
                            Opacity = 1.0,
                            FeatureCount = count,
                            Details = $"Digitized Layer | {count} features",
                            ColorHex = "#2563EB"
                        };
                        Layers.Add(activeVector);
                        UpdateLayerCount();
                    }
                    else
                    {
                        activeVector.FeatureCount = count;
                        activeVector.Details = $"Digitized Layer | {count} features";
                    }
                }
                else if (action == "profileLineDrawn")
                {
                    try
                    {
                        var p1 = root.GetProperty("p1");
                        var p2 = root.GetProperty("p2");
                        double lon1 = p1.GetProperty("lon").GetDouble();
                        double lat1 = p1.GetProperty("lat").GetDouble();
                        double lon2 = p2.GetProperty("lon").GetDouble();
                        double lat2 = p2.GetProperty("lat").GetDouble();

                        var activeRaster = Layers.LastOrDefault(l => l.Type == LayerType.Raster);
                        if (activeRaster != null && !string.IsNullOrEmpty(activeRaster.FilePath) && File.Exists(activeRaster.FilePath))
                        {
                            var (distances, elevations) = GdalRasterService.SampleProfileLine(activeRaster.FilePath, lon1, lat1, lon2, lat2);
                            if (distances.Length > 0 && elevations.Length > 0)
                            {
                                if (_activeProfileWindow != null && _activeProfileWindow.IsLoaded)
                                {
                                    _activeProfileWindow.UpdateData(activeRaster.Name, distances, elevations);
                                    if (_activeProfileWindow.WindowState == WindowState.Minimized)
                                        _activeProfileWindow.WindowState = WindowState.Normal;
                                    _activeProfileWindow.Activate();
                                    TxtStatus.Text = $"Updated elevation profile: {elevations.Length} points along {activeRaster.Name}.";
                                }
                                else
                                {
                                    _activeProfileWindow = new UI.ElevationProfileWindow(activeRaster.Name, distances, elevations);
                                    _activeProfileWindow.Owner = this;
                                    _activeProfileWindow.Closed += (s, ev) =>
                                    {
                                        _activeProfileWindow = null;
                                        PostMessageToMap(new { action = "clearProfileLine" });
                                    };
                                    _activeProfileWindow.Show();
                                    TxtStatus.Text = $"Extracted {elevations.Length} profile points along {activeRaster.Name}.";
                                }
                            }
                            else
                            {
                                TxtStatus.Text = "No valid elevation data found along the drawn profile transect.";
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        TxtStatus.Text = $"Profile extraction error: {ex.Message}";
                    }
                }
                else if (action == "requestRasterWindow")
                {
                    string filePath = root.TryGetProperty("filePath", out var fp) ? fp.GetString() ?? "" : "";
                    if (string.IsNullOrEmpty(filePath)) filePath = _activeRasterFilePath ?? "";
                    if (!string.IsNullOrEmpty(filePath) && File.Exists(filePath))
                    {
                        var bounds = root.GetProperty("bounds");
                        double minLon = bounds[0].GetDouble();
                        double minLat = bounds[1].GetDouble();
                        double maxLon = bounds[2].GetDouble();
                        double maxLat = bounds[3].GetDouble();

                        int screenW = root.TryGetProperty("screenW", out var sw) ? sw.GetInt32() : 1920;
                        int screenH = root.TryGetProperty("screenH", out var sh) ? sh.GetInt32() : 1080;
                        string layerId = root.TryGetProperty("layerId", out var lid) ? lid.GetString() ?? "" : (_activeRasterLayerId ?? "");
                        string reqShader = root.TryGetProperty("shaderMode", out var sm) ? sm.GetString() ?? "" : "";
                        string reqPalette = root.TryGetProperty("palette", out var pal) ? pal.GetString() ?? "" : "";

                        var layer = Layers.FirstOrDefault(l => l.Id == layerId || l.FilePath == filePath);
                        string effectiveShader = !string.IsNullOrEmpty(reqShader) 
                            ? reqShader 
                            : (layer?.ShaderMode ?? _activeRasterShaderMode ?? "");
                        string effectivePalette = !string.IsNullOrEmpty(reqPalette) 
                            ? reqPalette 
                            : (layer?.Palette ?? _activeRasterPalette ?? "GLOBAL_MAPPER_ATLAS");

                        _rasterCts?.Cancel();
                        _rasterCts = new System.Threading.CancellationTokenSource();
                        var token = _rasterCts.Token;

                        _ = System.Threading.Tasks.Task.Run(() =>
                        {
                            if (token.IsCancellationRequested) return;
                            var win = GdalRasterService.RenderWindow(filePath, minLon, minLat, maxLon, maxLat, screenW, screenH, effectiveShader, effectivePalette);
                            if (!win.Success || token.IsCancellationRequested) return;

                            Dispatcher.InvokeAsync(() =>
                            {
                                if (token.IsCancellationRequested) return;
                                PostMessageToMap(new
                                {
                                    action = "updateRasterWindow",
                                    layerId = layerId,
                                    imageUrl = win.ImageUrl,
                                    bounds = win.Extent
                                });
                            });
                        }, token);
                    }
                }
                else if (action == "queryPointCloudViewport")
                {
                    if (DuckDbPointCloudService.HasData)
                    {
                        var bounds = root.GetProperty("bounds");
                        double minLon = bounds[0].GetDouble();
                        double minLat = bounds[1].GetDouble();
                        double maxLon = bounds[2].GetDouble();
                        double maxLat = bounds[3].GetDouble();

                        byte? clsFilter = null;
                        if (root.TryGetProperty("classification", out var cp) && cp.GetInt32() >= 0)
                            clsFilter = (byte)cp.GetInt32();

                        _ = System.Threading.Tasks.Task.Run(() =>
                        {
                            var batch = DuckDbPointCloudService.QueryViewportBatch(minLon, maxLon, minLat, maxLat, 500000, clsFilter);
                            if (batch != null && batch.count > 0)
                            {
                                Dispatcher.InvokeAsync(() =>
                                {
                                    PostMessageToMap(new
                                    {
                                        action = "updatePointCloud",
                                        batch = batch
                                    });
                                });
                            }
                        });
                    }
                }
                else if (action == "gpuInfo")
                {
                    string renderer = root.TryGetProperty("gpuRenderer", out var gr) ? gr.GetString() ?? "" : "";
                    if (!string.IsNullOrEmpty(renderer))
                    {
                        _activeGpuRenderer = renderer;
                        if (TxtGpuFps != null)
                        {
                            TxtGpuFps.ToolTip = $"GPU: {_activeGpuRenderer}";
                        }
                    }
                }
                else if (action == "viewportTelemetry")
                {
                    string activity = root.TryGetProperty("activity", out var act) ? act.GetString() ?? "IDLE" : "IDLE";
                    string zoom = root.TryGetProperty("zoom", out var zm) ? zm.GetString() ?? "5.0" : "5.0";
                    int redrawMs = root.TryGetProperty("redrawMs", out var rm) ? rm.GetInt32() : 0;
                    int fps = root.TryGetProperty("fps", out var fp) ? fp.GetInt32() : 60;
                    string frameMs = root.TryGetProperty("frameTimeMs", out var ftm) ? ftm.GetString() ?? "1.6" : "1.6";
                    string activeElements = root.TryGetProperty("activeElements", out var ae) ? ae.GetString() ?? "" : "";

                    if (TxtInteractionType != null && BadgeInteraction != null)
                    {
                        TxtInteractionType.Text = activity;
                        if (activity == "ZOOM IN")
                        {
                            BadgeInteraction.Background = new SolidColorBrush(Color.FromRgb(37, 99, 235));
                            TxtInteractionType.Foreground = Brushes.White;
                        }
                        else if (activity == "ZOOM OUT")
                        {
                            BadgeInteraction.Background = new SolidColorBrush(Color.FromRgb(124, 58, 237));
                            TxtInteractionType.Foreground = Brushes.White;
                        }
                        else if (activity == "PAN")
                        {
                            BadgeInteraction.Background = new SolidColorBrush(Color.FromRgb(16, 185, 129));
                            TxtInteractionType.Foreground = Brushes.White;
                        }
                        else
                        {
                            BadgeInteraction.Background = new SolidColorBrush(Color.FromRgb(219, 234, 254));
                            TxtInteractionType.Foreground = new SolidColorBrush(Color.FromRgb(29, 78, 216));
                        }
                    }

                    if (TxtInteractionDetails != null)
                    {
                        TxtInteractionDetails.Text = $"Zoom: {zoom}x • Redraw: {redrawMs}ms";
                    }
                    if (!string.IsNullOrEmpty(activeElements) && TxtActiveElements != null)
                    {
                        TxtActiveElements.Text = activeElements;
                    }
                    if (TxtGpuFps != null)
                    {
                        TxtGpuFps.Text = $"{fps} FPS";
                    }
                    if (TxtGpuFrameTime != null)
                    {
                        TxtGpuFrameTime.Text = $"~{frameMs} ms";
                    }
                }
                else if (action == "layerBenchmark")
                {
                    string id = root.TryGetProperty("id", out var idProp) ? idProp.GetString() ?? "" : "";
                    string name = root.TryGetProperty("name", out var nProp) ? nProp.GetString() ?? "" : "";
                    long fileLoadMs = root.TryGetProperty("fileLoadMs", out var flm) ? flm.GetInt64() : 0;
                    long canvasRenderMs = root.TryGetProperty("canvasRenderMs", out var crm) ? crm.GetInt64() : 0;
                    long totalMs = root.TryGetProperty("totalMs", out var tm) ? tm.GetInt64() : (fileLoadMs + canvasRenderMs);

                    double totalSec = totalMs / 1000.0;
                    string totalText = totalSec >= 1.0 ? $"{totalSec:F2}s" : $"{totalMs}ms";
                    string fileText = fileLoadMs >= 1000 ? $"{fileLoadMs / 1000.0:F2}s" : $"{fileLoadMs}ms";
                    string canvasText = canvasRenderMs >= 1000 ? $"{canvasRenderMs / 1000.0:F2}s" : $"{canvasRenderMs}ms";

                    if (CardBenchmark != null) CardBenchmark.Visibility = Visibility.Visible;
                    if (TxtBenchmarkFileName != null) TxtBenchmarkFileName.Text = name;
                    if (TxtBenchmarkTotalTime != null) TxtBenchmarkTotalTime.Text = totalText;
                    if (TxtBenchmarkBreakdown != null) TxtBenchmarkBreakdown.Text = $"Ingest/Read: {fileText} • Canvas Paint: {canvasText}";
                    if (ProgressBarFileLoad != null) ProgressBarFileLoad.Visibility = Visibility.Collapsed;
                    if (TxtBenchmarkStatusIcon != null)
                    {
                        TxtBenchmarkStatusIcon.Text = "✓";
                        TxtBenchmarkStatusIcon.Foreground = new SolidColorBrush(Color.FromRgb(16, 185, 129));
                    }
                    if (TxtBenchmarkStatus != null)
                    {
                        TxtBenchmarkStatus.Text = "Fully Loaded & Shown on Canvas";
                        TxtBenchmarkStatus.Foreground = new SolidColorBrush(Color.FromRgb(5, 150, 105));
                    }

                    var layer = FindLayer(id);
                    if (layer == null && !string.IsNullOrEmpty(name))
                    {
                        layer = Layers.FirstOrDefault(l => l.Name == name);
                    }
                    if (layer != null)
                    {
                        layer.LoadTimeText = fileText;
                        layer.CanvasRenderTimeText = canvasText;
                        layer.TotalDurationText = totalText;
                    }
                }
            }
            catch { }
        }
    }
}
