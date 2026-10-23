using System;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;

namespace GeoStudio
{
    public partial class MainWindow
    {
        private void HandleTelemetryMessage(JsonElement root, string action)
        {
            if (action == "viewportTelemetry")
            {
                string activity = root.TryGetProperty("activity", out var act) ? act.GetString() ?? "IDLE" : "IDLE";
                string zoom = root.TryGetProperty("zoom", out var zm) ? zm.GetString() ?? "5.0" : "5.0";
                int redrawMs = root.TryGetProperty("redrawMs", out var rdm) ? rdm.GetInt32() : 0;
                int fps = root.TryGetProperty("fps", out var fp) ? fp.GetInt32() : 60;
                string frameMs = root.TryGetProperty("frameTimeMs", out var ftm) ? ftm.GetString() ?? "16.6" : "16.6";
                string activeElements = root.TryGetProperty("activeElements", out var ae) ? ae.GetString() ?? "" : "";

                if (TxtInteractionType != null && BadgeInteraction != null)
                {
                    TxtInteractionType.Text = activity;
                    if (activity == "PANNING" || activity == "ZOOMING" || activity == "ROTATING")
                    {
                        BadgeInteraction.Background = new SolidColorBrush(Color.FromRgb(37, 99, 235));
                        TxtInteractionType.Foreground = Brushes.White;
                    }
                    else
                    {
                        BadgeInteraction.Background = new SolidColorBrush(Color.FromRgb(219, 234, 254));
                        TxtInteractionType.Foreground = new SolidColorBrush(Color.FromRgb(29, 78, 216));
                    }
                }

                if (TxtInteractionDetails != null) TxtInteractionDetails.Text = $"Zoom: {zoom}x • Redraw: {redrawMs}ms";
                if (!string.IsNullOrEmpty(activeElements) && TxtActiveElements != null) TxtActiveElements.Text = activeElements;
                if (TxtGpuFps != null) TxtGpuFps.Text = $"{fps} FPS";
                if (TxtGpuFrameTime != null) TxtGpuFrameTime.Text = $"~{frameMs} ms";

                if (root.TryGetProperty("centerLon", out var cLon) &&
                    root.TryGetProperty("centerLat", out var cLat) &&
                    root.TryGetProperty("zoomNum", out var zNum))
                {
                    RecordViewportExtent(cLon.GetDouble(), cLat.GetDouble(), zNum.GetDouble());
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

                var layer = FindLayer(id) ?? (!string.IsNullOrEmpty(name) ? Layers.FirstOrDefault(l => l.Name == name) : null);
                if (layer != null)
                {
                    layer.LoadTimeText = fileText;
                    layer.CanvasRenderTimeText = canvasText;
                    layer.TotalDurationText = totalText;
                }
            }
        }
    }
}
