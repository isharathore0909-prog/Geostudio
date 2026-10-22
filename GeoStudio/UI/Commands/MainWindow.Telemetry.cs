using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;

namespace GeoStudio
{
    public partial class MainWindow
    {
        private DispatcherTimer? _telemetryTimer;
        private readonly Process _currentProcess = Process.GetCurrentProcess();
        private TimeSpan _lastCpuTime = TimeSpan.Zero;
        private DateTime _lastCpuSampleTime = DateTime.UtcNow;
        private long _peakWorkingSetBytes = 0;
        private bool _isTelemetryExpanded = true;
        private string _activeGpuRenderer = "DirectX/OpenGL WebGL2 Canvas";

        private void InitializeTelemetry()
        {
            try
            {
                _lastCpuTime = _currentProcess.TotalProcessorTime;
                _lastCpuSampleTime = DateTime.UtcNow;
                _peakWorkingSetBytes = _currentProcess.WorkingSet64;

                _telemetryTimer = new DispatcherTimer
                {
                    Interval = TimeSpan.FromMilliseconds(500)
                };
                _telemetryTimer.Tick += (s, e) => UpdateHardwareTelemetry();
                _telemetryTimer.Start();
            }
            catch { }
        }

        private void UpdateHardwareTelemetry()
        {
            try
            {
                var now = DateTime.UtcNow;
                var totalCpu = _currentProcess.TotalProcessorTime;
                var wallDelta = (now - _lastCpuSampleTime).TotalMilliseconds;

                if (wallDelta >= 250)
                {
                    var cpuDelta = (totalCpu - _lastCpuTime).TotalMilliseconds;
                    double cpuPct = (cpuDelta / (wallDelta * Environment.ProcessorCount)) * 100.0;
                    cpuPct = Math.Clamp(cpuPct, 0.0, 100.0);
                    _lastCpuTime = totalCpu;
                    _lastCpuSampleTime = now;

                    if (TxtCpuUsage != null && ProgressCpu != null)
                    {
                        TxtCpuUsage.Text = $"{cpuPct:F1}%";
                        ProgressCpu.Value = Math.Max(3, (int)cpuPct);
                    }
                }

                _currentProcess.Refresh();
                long totalMem = _currentProcess.WorkingSet64;
                try
                {
                    var webviewProcs = Process.GetProcessesByName("msedgewebview2");
                    foreach (var p in webviewProcs)
                    {
                        totalMem += p.WorkingSet64 / 3;
                    }
                }
                catch { }

                if (totalMem > _peakWorkingSetBytes) _peakWorkingSetBytes = totalMem;

                if (TxtMemoryUsage != null && TxtMemoryPeak != null)
                {
                    TxtMemoryUsage.Text = $"{totalMem / (1024.0 * 1024.0):F0} MB";
                    TxtMemoryPeak.Text = $"Peak: {_peakWorkingSetBytes / (1024.0 * 1024.0):F0}M";
                }
            }
            catch { }
        }

        private void BtnToggleTelemetry_Click(object sender, RoutedEventArgs e)
        {
            _isTelemetryExpanded = !_isTelemetryExpanded;
            if (TelemetryContentPanel != null)
                TelemetryContentPanel.Visibility = _isTelemetryExpanded ? Visibility.Visible : Visibility.Collapsed;
            if (BtnToggleTelemetry != null)
                BtnToggleTelemetry.Content = _isTelemetryExpanded ? "▾" : "▴";
        }
    }
}
