using System;
using System.IO;

namespace GeoStudio.PointCloud
{
    internal static class LasDecompressor
    {
        public static string EnsureUncompressedLas(string filePath, Action<int, string>? progress = null)
        {
            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            if (ext != ".laz")
            {
                return filePath;
            }

            var pdalCandidates = new[]
            {
                @"C:\Program Files\QGIS 3.40.14\bin\pdal.exe",
                @"C:\Program Files\QGIS 3.38\bin\pdal.exe",
                @"C:\Program Files\QGIS 3.36\bin\pdal.exe",
                @"C:\Program Files\QGIS 3.34\bin\pdal.exe",
                @"C:\Program Files\QGIS 3.28\bin\pdal.exe"
            };

            string? pdalExe = null;
            foreach (var p in pdalCandidates)
            {
                if (File.Exists(p)) { pdalExe = p; break; }
            }

            if (pdalExe == null)
            {
                throw new NotSupportedException("LAZ (compressed point cloud) requires PDAL. Install QGIS or decompress to standard .las first.");
            }

            progress?.Invoke(15, "Decompressing LAZ with high-speed PDAL engine...");
            string tmpDir = Path.Combine(Path.GetTempPath(), "GeoStudio", "LasCache");
            Directory.CreateDirectory(tmpDir);
            string baseName = Path.GetFileNameWithoutExtension(filePath);
            string tmpLas = Path.Combine(tmpDir, $"{baseName}_{new FileInfo(filePath).Length}.las");

            if (File.Exists(tmpLas) && new FileInfo(tmpLas).Length > 1024)
            {
                return tmpLas;
            }

            var psi = new System.Diagnostics.ProcessStartInfo
            {
                FileName = pdalExe,
                Arguments = $"translate \"{filePath}\" \"{tmpLas}\"",
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            string qgisRoot = Path.GetDirectoryName(Path.GetDirectoryName(pdalExe)) ?? "";
            string projDir = Path.Combine(qgisRoot, "share", "proj");
            if (Directory.Exists(projDir))
            {
                psi.EnvironmentVariables["PROJ_LIB"] = projDir;
                psi.EnvironmentVariables["PROJ_DATA"] = projDir;
            }

            using var proc = System.Diagnostics.Process.Start(psi);
            if (proc != null)
            {
                proc.WaitForExit(60000);
            }

            if (File.Exists(tmpLas) && new FileInfo(tmpLas).Length > 1024)
            {
                return tmpLas;
            }

            throw new InvalidOperationException("Failed to decompress LAZ point cloud with PDAL.");
        }
    }
}
