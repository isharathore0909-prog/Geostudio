using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;

namespace GeoStudio.Python
{
    /// <summary>
    /// Self-contained, offline-safe Python processing pipeline service.
    /// Bridges high-throughput C# GIS operations with deep scientific geospatial & LiDAR algorithms.
    /// </summary>
    public static class PythonPipelineService
    {
        private static string? _cachedPythonExe;
        private static string? _bridgeScriptPath;

        public static string ResolvePythonExecutable()
        {
            if (!string.IsNullOrEmpty(_cachedPythonExe) && File.Exists(_cachedPythonExe))
                return _cachedPythonExe;

            // Priority 1: Project's local virtual environment / runtime
            string localVenv = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "PythonEngine", ".venv", "Scripts", "python.exe");
            if (File.Exists(localVenv)) return _cachedPythonExe = localVenv;

            // Priority 2: Duplicacy standalone environment
            string duplicacyVenv = @"D:\DUPLICACY\GeoStudio\.venv\Scripts\python.exe";
            if (File.Exists(duplicacyVenv)) return _cachedPythonExe = duplicacyVenv;

            // Priority 3: Offline QGIS standalone Python runtime if installed
            string qgisBat = @"C:\Program Files\QGIS 3.40.14\bin\python-qgis-ltr.bat";
            if (File.Exists(qgisBat)) return _cachedPythonExe = qgisBat;

            // Priority 4: Standard system Python
            return _cachedPythonExe = "python.exe";
        }

        public static string ResolveBridgeScriptPath()
        {
            if (!string.IsNullOrEmpty(_bridgeScriptPath) && File.Exists(_bridgeScriptPath))
                return _bridgeScriptPath;

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string p0 = Path.Combine(baseDir, "Python", "PythonPipeline", "pipeline_bridge.py");
            if (File.Exists(p0)) return _bridgeScriptPath = p0;

            string p0Dir = Path.Combine(Directory.GetCurrentDirectory(), "Python", "PythonPipeline", "pipeline_bridge.py");
            if (File.Exists(p0Dir)) return _bridgeScriptPath = p0Dir;

            string p1 = Path.Combine(baseDir, "Loading", "PythonPipeline", "pipeline_bridge.py");
            if (File.Exists(p1)) return _bridgeScriptPath = p1;

            string p2 = Path.Combine(Directory.GetCurrentDirectory(), "Loading", "PythonPipeline", "pipeline_bridge.py");
            if (File.Exists(p2)) return _bridgeScriptPath = p2;

            return _bridgeScriptPath = p0;
        }

        /// <summary>
        /// Executes an algorithm task asynchronously with live progress reporting.
        /// </summary>
        public static async Task<PipelineResult> ExecuteTaskAsync(
            string task,
            string? inputFile = null,
            string? outputFile = null,
            string? mode = null,
            string? param1 = null,
            string? param2 = null,
            Action<int, string>? onProgress = null)
        {
            string pythonExe = ResolvePythonExecutable();
            string bridgeScript = ResolveBridgeScriptPath();

            if (!File.Exists(bridgeScript))
            {
                return new PipelineResult { Success = false, ErrorMessage = $"Bridge script not found: {bridgeScript}" };
            }

            var args = $"\"{bridgeScript}\" --task {task}";
            if (!string.IsNullOrEmpty(inputFile)) args += $" --input \"{inputFile}\"";
            if (!string.IsNullOrEmpty(outputFile)) args += $" --output \"{outputFile}\"";
            if (!string.IsNullOrEmpty(mode)) args += $" --mode {mode}";
            if (!string.IsNullOrEmpty(param1)) args += $" --param1 \"{param1}\"";
            if (!string.IsNullOrEmpty(param2)) args += $" --param2 \"{param2}\"";

            var startInfo = new ProcessStartInfo
            {
                FileName = pythonExe.EndsWith(".bat", StringComparison.OrdinalIgnoreCase) ? "cmd.exe" : pythonExe,
                Arguments = pythonExe.EndsWith(".bat", StringComparison.OrdinalIgnoreCase) ? $"/c \"\"{pythonExe}\" {args}\"" : args,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
                WorkingDirectory = Path.GetDirectoryName(bridgeScript) ?? AppDomain.CurrentDomain.BaseDirectory
            };

            // Inject PythonEngine path into PYTHONPATH
            string pythonEnginePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "PythonEngine");
            if (Directory.Exists(pythonEnginePath))
            {
                string existingPath = Environment.GetEnvironmentVariable("PYTHONPATH") ?? "";
                startInfo.EnvironmentVariables["PYTHONPATH"] = $"{pythonEnginePath};{existingPath}";
            }

            // Ensure stable PROJ & GDAL data paths overriding any conflicting system software (e.g. PostGIS)
            string qgisShareProj = @"C:\Program Files\QGIS 3.40.14\share\proj";
            if (Directory.Exists(qgisShareProj))
            {
                startInfo.EnvironmentVariables["PROJ_LIB"] = qgisShareProj;
                startInfo.EnvironmentVariables["PROJ_DATA"] = qgisShareProj;
            }
            string qgisShareGdal = @"C:\Program Files\QGIS 3.40.14\share\gdal";
            if (Directory.Exists(qgisShareGdal))
            {
                startInfo.EnvironmentVariables["GDAL_DATA"] = qgisShareGdal;
            }

            var result = new PipelineResult();

            return await Task.Run(() =>
            {
                try
                {
                    using var proc = new Process { StartInfo = startInfo };
                    proc.OutputDataReceived += (s, e) =>
                    {
                        if (string.IsNullOrWhiteSpace(e.Data)) return;

                        if (e.Data.StartsWith("PROGRESS:"))
                        {
                            var parts = e.Data.Split(':', 3);
                            if (parts.Length >= 2 && int.TryParse(parts[1], out int pct))
                            {
                                string msg = parts.Length > 2 ? parts[2] : "";
                                onProgress?.Invoke(pct, msg);
                            }
                        }
                        else if (e.Data.StartsWith("RESULT:"))
                        {
                            string json = e.Data.Substring(7);
                            try
                            {
                                using var doc = JsonDocument.Parse(json);
                                var root = doc.RootElement;
                                result.Success = root.GetProperty("status").GetString() == "ok";
                                if (root.TryGetProperty("error", out var err))
                                    result.ErrorMessage = err.GetString();
                                if (root.TryGetProperty("data", out var data))
                                {
                                    result.OutputData = data.ToString();
                                    if (data.ValueKind == JsonValueKind.Object && data.TryGetProperty("output_file", out var ofProp))
                                    {
                                        result.OutputFilePath = ofProp.GetString();
                                    }
                                }
                            }
                            catch
                            {
                                result.OutputData = json;
                            }
                        }
                    };

                    proc.ErrorDataReceived += (s, e) =>
                    {
                        if (!string.IsNullOrWhiteSpace(e.Data))
                        {
                            result.StandardError += e.Data + "\n";
                        }
                    };

                    proc.Start();
                    proc.BeginOutputReadLine();
                    proc.BeginErrorReadLine();
                    proc.WaitForExit();

                    if (proc.ExitCode != 0 && string.IsNullOrEmpty(result.ErrorMessage))
                    {
                        result.Success = false;
                        result.ErrorMessage = string.IsNullOrEmpty(result.StandardError)
                            ? $"Process exited with code {proc.ExitCode}"
                            : result.StandardError;
                    }

                    return result;
                }
                catch (Exception ex)
                {
                    return new PipelineResult { Success = false, ErrorMessage = ex.Message };
                }
            });
        }

        /// <summary>
        /// Generates full-resolution 3D Shaded Relief GeoTIFF using Python GDAL engine.
        /// </summary>
        public static async Task<PipelineResult> GenerateElevationReliefAsync(
            string demPath,
            string presetKey = "GLOBAL_MAPPER_ATLAS",
            Action<int, string>? onProgress = null)
        {
            return await ExecuteTaskAsync(
                task: "elevation_relief",
                inputFile: demPath,
                param1: presetKey,
                onProgress: onProgress);
        }

        /// <summary>
        /// Spawns the standalone OpenGL 3D viewer workstation.
        /// </summary>
        public static void Launch3DViewer(string? filePath = null)
        {
            string pythonExe = ResolvePythonExecutable();
            string bridgeScript = ResolveBridgeScriptPath();
            string args = $"\"{bridgeScript}\" --task launch_3d";
            if (!string.IsNullOrEmpty(filePath)) args += $" --input \"{filePath}\"";

            var startInfo = new ProcessStartInfo
            {
                FileName = pythonExe.EndsWith(".bat", StringComparison.OrdinalIgnoreCase) ? "cmd.exe" : pythonExe,
                Arguments = pythonExe.EndsWith(".bat", StringComparison.OrdinalIgnoreCase) ? $"/c \"\"{pythonExe}\" {args}\"" : args,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            Process.Start(startInfo);
        }
    }

    public class PipelineResult
    {
        public bool Success { get; set; } = true;
        public string? OutputData { get; set; }
        public string? OutputFilePath { get; set; }
        public string? ErrorMessage { get; set; }
        public string StandardError { get; set; } = "";
    }
}
