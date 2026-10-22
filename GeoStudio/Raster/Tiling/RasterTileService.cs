using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Web.WebView2.Core;
using OSGeo.GDAL;
using OSGeo.OSR;
using GeoStudio.Models;

namespace GeoStudio.Raster
{
    /// <summary>
    /// Phase 4: XYZ (EPSG:3857) PNG tiles served in-process via WebView2 WebResourceRequested.
    /// URL: http://tiles.geostudio.local/t/{layerId}/{z}/{x}/{y}.png?v={version}
    /// </summary>
    public static class RasterTileService
    {
        public const string Host = "tiles.geostudio.local";
        private const double R = 20037508.342789244;
        private const int T = 256;

        private static readonly ConcurrentDictionary<string, TileLayer> _layers = new();
        private static readonly TileCache _cache = new(256L * 1024 * 1024);
        private static readonly SemaphoreSlim _gate = new(Math.Clamp(Environment.ProcessorCount, 2, 6));
        private static readonly Lazy<byte[]> _emptyPng = new(() => EncodePng(new byte[4], 1, 1));
        private static readonly Lazy<string> _mercatorWkt = new(() =>
        {
            using var s = new SpatialReference("");
            s.ImportFromEPSG(3857);
            s.ExportToWkt(out string wkt, null);
            return wkt;
        });

        #region Layer lifetime
        public static void Register(string layerId, string path)
        {
            GdalRasterService.Initialize();
            var layer = new TileLayer { Id = layerId, SourcePath = path };
            using (var ds = Gdal.Open(path, Access.GA_ReadOnly))
            {
                layer.HasOverviews = ds.GetRasterBand(1).GetOverviewCount() > 0;
            }
            _layers[layerId] = layer;
        }

        public static void Unregister(string layerId)
        {
            if (_layers.TryRemove(layerId, out var l)) l.DrainPool();
            _cache.RemoveLayer(layerId);
        }

        public static int SetOptimized(string layerId, string cogPath)
        {
            if (!_layers.TryGetValue(layerId, out var l)) return 0;
            l.CogPath = cogPath;
            int v = Interlocked.Increment(ref l.Version);
            l.DrainPool();
            _cache.RemoveLayer(layerId);
            return v;
        }

        public static LayerTier GetTier(string layerId) =>
            _layers.TryGetValue(layerId, out var l) ? (l.CogPath != null ? LayerTier.Optimized : LayerTier.Direct) : LayerTier.Preview;
        #endregion

        #region WebView2 hook
        public static void Attach(CoreWebView2 wv)
        {
            wv.AddWebResourceRequestedFilter($"http://{Host}/*", CoreWebView2WebResourceContext.All);
            wv.WebResourceRequested += (s, e) =>
            {
                Uri uri;
                try { uri = new Uri(e.Request.Uri); } catch { return; }
                if (!uri.Host.Equals(Host, StringComparison.OrdinalIgnoreCase)) return;

                var parts = uri.AbsolutePath.Trim('/').Split('/');
                if (parts.Length != 5 || parts[0] != "t" || !_layers.ContainsKey(parts[1])
                    || !int.TryParse(parts[2], out int z) || !int.TryParse(parts[3], out int x)
                    || !int.TryParse(Path.GetFileNameWithoutExtension(parts[4]), out int y))
                {
                    e.Response = wv.Environment.CreateWebResourceResponse(null, 404, "Not Found", "Access-Control-Allow-Origin: *");
                    return;
                }

                string layerId = parts[1];
                var deferral = e.GetDeferral();
                var dispatcher = Application.Current.Dispatcher;

                _ = Task.Run(async () =>
                {
                    byte[] png;
                    await _gate.WaitAsync();
                    try { png = GetTile(layerId, z, x, y); }
                    catch (Exception ex) { System.Diagnostics.Debug.WriteLine($"Tile error: {ex.Message}"); png = _emptyPng.Value; }
                    finally { _gate.Release(); }

                    await dispatcher.InvokeAsync(() =>
                    {
                        e.Response = wv.Environment.CreateWebResourceResponse(
                            new MemoryStream(png), 200, "OK",
                            "Content-Type: image/png\r\nAccess-Control-Allow-Origin: *\r\nCache-Control: max-age=3600");
                        deferral.Complete();
                    });
                });
            };
        }
        #endregion

        #region Tile rendering
        public static byte[] GetTile(string layerId, int z, int x, int y)
        {
            if (!_layers.TryGetValue(layerId, out var L)) return _emptyPng.Value;
            if (z < 0 || z > 26 || x < 0 || y < 0 || x >= (1L << z) || y >= (1L << z)) return _emptyPng.Value;

            int ver = L.Version;
            string key = $"{layerId}|{ver}|{z}|{x}|{y}";
            if (_cache.TryGet(key, out var hit)) return hit;

            byte[] png = Render(L, ver, z, x, y) ?? _emptyPng.Value;
            if (ver == L.Version) _cache.Add(key, png);
            return png;
        }

        private static byte[]? Render(TileLayer L, int ver, int z, int x, int y)
        {
            using var lease = TilePooledReader.Rent(L, ver, _mercatorWkt.Value);
            if (lease == null) return null;
            var p = lease.Item;

            double size = 2 * R / (1L << z);
            double minX = -R + x * size, maxX = minX + size;
            double maxY = R - y * size, minY = maxY - size;

            double px0 = (minX - p.Gt[0]) / p.Gt[1], px1 = (maxX - p.Gt[0]) / p.Gt[1];
            double py0 = (maxY - p.Gt[3]) / p.Gt[5], py1 = (minY - p.Gt[3]) / p.Gt[5];
            if (px1 <= 0 || py1 <= 0 || px0 >= p.W || py0 >= p.H) return null;

            double ix0 = Math.Max(0, px0), ix1 = Math.Min(p.W, px1);
            double iy0 = Math.Max(0, py0), iy1 = Math.Min(p.H, py1);
            double sx = T / (px1 - px0), sy = T / (py1 - py0);

            int ox0 = Math.Clamp((int)Math.Floor((ix0 - px0) * sx), 0, T - 1);
            int oy0 = Math.Clamp((int)Math.Floor((iy0 - py0) * sy), 0, T - 1);
            int ox1 = Math.Clamp((int)Math.Ceiling((ix1 - px0) * sx), ox0 + 1, T);
            int oy1 = Math.Clamp((int)Math.Ceiling((iy1 - py0) * sy), oy0 + 1, T);
            int ow = ox1 - ox0, oh = oy1 - oy0;

            int rx = (int)Math.Floor(ix0), ry = (int)Math.Floor(iy0);
            int rw = Math.Max(1, Math.Min(p.W - rx, (int)Math.Ceiling(ix1) - rx));
            int rh = Math.Max(1, Math.Min(p.H - ry, (int)Math.Ceiling(iy1) - ry));

            if (L.CogPath == null && !L.HasOverviews && (long)rw * rh > 64_000_000L) return null;

            Gdal.SetThreadLocalConfigOption("GDAL_RASTERIO_RESAMPLING", "AVERAGE");

            int n = ow * oh;
            int nc = p.Colors.Length;
            bool isByte = p.DType == DataType.GDT_Byte;
            var chans = new byte[nc][];
            bool[]? ndMask = null;
            (double lo, double hi)[]? stretch = isByte ? null : EnsureStretch(L, p);

            for (int i = 0; i < nc; i++)
            {
                var band = p.Ds.GetRasterBand(p.Colors[i]);
                if (isByte)
                {
                    var buf = new byte[n];
                    if (band.ReadRaster(rx, ry, rw, rh, buf, ow, oh, 0, 0) != CPLErr.CE_None) return null;
                    chans[i] = buf;
                }
                else
                {
                    var f = new float[n];
                    if (band.ReadRaster(rx, ry, rw, rh, f, ow, oh, 0, 0) != CPLErr.CE_None) return null;
                    var bytes = new byte[n];
                    var (lo, hi) = stretch![i];
                    ndMask ??= new bool[n];
                    for (int k = 0; k < n; k++)
                    {
                        float v = f[k];
                        if (float.IsNaN(v) || float.IsInfinity(v) || (p.HasNd && v == (float)p.Nd)) { ndMask[k] = true; continue; }
                        bytes[k] = (byte)Math.Clamp((v - lo) / (hi - lo) * 255.0, 0, 255);
                    }
                    chans[i] = bytes;
                }
            }

            byte[]? alpha = null;
            if (p.Alpha > 0)
            {
                alpha = new byte[n];
                if (p.Ds.GetRasterBand(p.Alpha).ReadRaster(rx, ry, rw, rh, alpha, ow, oh, 0, 0) != CPLErr.CE_None) alpha = null;
            }

            bool zeroIsNoData = isByte && alpha == null && !p.HasNd;
            var bgra = new byte[T * T * 4];

            for (int r = 0; r < oh; r++)
            {
                for (int c = 0; c < ow; c++)
                {
                    int s = r * ow + c;
                    byte a = alpha != null ? alpha[s] : (byte)255;
                    byte cr = chans[0][s];
                    byte cg = nc == 3 ? chans[1][s] : cr;
                    byte cb = nc == 3 ? chans[2][s] : cr;

                    if (ndMask != null && ndMask[s]) a = 0;
                    else if (isByte && p.HasNd && cr == (byte)p.Nd && (nc == 1 || (cg == (byte)p.Nd && cb == (byte)p.Nd))) a = 0;
                    else if (zeroIsNoData && cr == 0 && cg == 0 && cb == 0) a = 0;

                    int d = ((oy0 + r) * T + (ox0 + c)) * 4;
                    bgra[d] = cb; bgra[d + 1] = cg; bgra[d + 2] = cr; bgra[d + 3] = a;
                }
            }
            return EncodePng(bgra, T, T);
        }

        private static (double lo, double hi)[] EnsureStretch(TileLayer L, PooledDataset p)
        {
            lock (L.StretchLock)
            {
                if (L.Stretch != null) return L.Stretch;
                var st = new (double lo, double hi)[p.Colors.Length];
                var statsDs = p.Src ?? p.Ds;
                for (int i = 0; i < st.Length; i++)
                {
                    try
                    {
                        statsDs.GetRasterBand(p.Colors[i]).ComputeStatistics(true, out double mn, out double mx, out double mean, out double sd, null, null);
                        double lo = Math.Max(mn, mean - 2 * sd), hi = Math.Min(mx, mean + 2 * sd);
                        if (hi <= lo) { lo = mn; hi = mx; }
                        if (hi <= lo) hi = lo + 1;
                        st[i] = (lo, hi);
                    }
                    catch { st[i] = (0, 1); }
                }
                L.Stretch = st;
                return st;
            }
        }

        private static byte[] EncodePng(byte[] bgra, int w, int h)
        {
            var bmp = BitmapSource.Create(w, h, 96, 96, PixelFormats.Bgra32, null, bgra, w * 4);
            bmp.Freeze();
            using var ms = new MemoryStream();
            var enc = new PngBitmapEncoder();
            enc.Frames.Add(BitmapFrame.Create(bmp));
            enc.Save(ms);
            return ms.ToArray();
        }
        #endregion
    }
}
