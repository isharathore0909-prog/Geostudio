using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using OSGeo.GDAL;

namespace GeoStudio.Raster
{
    internal static class SparseRasterPreview
    {
        private const int Sub = 16;

        public static byte[] Build(string filePath, int width, int height, int bands, int outW, int outH, int gridCells = 48)
        {
            double cellSrc = Math.Max(width, height) / (double)Math.Max(2, gridCells);
            int gx = Math.Max(1, (int)Math.Ceiling(width / cellSrc));
            int gy = Math.Max(1, (int)Math.Ceiling(height / cellSrc));
            int nCells = gx * gy;

            int colorBands = bands >= 3 ? 3 : 1;
            bool hasAlpha = bands >= 4;

            DataType dtype;
            int bw, bh;
            var noData = new double[colorBands];
            var hasNoData = new bool[colorBands];
            using (var probe = Gdal.Open(filePath, Access.GA_ReadOnly))
            {
                var b1 = probe.GetRasterBand(1);
                dtype = b1.DataType;
                b1.GetBlockSize(out bw, out bh);
                for (int b = 0; b < colorBands; b++)
                {
                    probe.GetRasterBand(b + 1).GetNoDataValue(out double v, out int has);
                    noData[b] = v;
                    hasNoData[b] = has != 0;
                }
            }
            bw = Math.Max(1, bw);
            bh = Math.Max(1, bh);

            bool anyNoData = Array.Exists(hasNoData, h => h);
            bool zeroIsNoData = !hasAlpha && !anyNoData && dtype == DataType.GDT_Byte;

            var mean = new float[colorBands][];
            for (int b = 0; b < colorBands; b++) mean[b] = new float[nCells];
            var valid = new bool[nCells];

            var opts = new ParallelOptions { MaxDegreeOfParallelism = Math.Clamp(Environment.ProcessorCount, 1, 8) };
            Parallel.For(0, gy, opts, () => Gdal.Open(filePath, Access.GA_ReadOnly), (j, _, ds) =>
            {
                var buf = new float[colorBands + (hasAlpha ? 1 : 0)][];
                for (int k = 0; k < buf.Length; k++) buf[k] = new float[Sub * Sub];
                var sum = new double[colorBands];

                int cy = (int)Math.Min(height - 1, (j + 0.5) * cellSrc);
                for (int i = 0; i < gx; i++)
                {
                    int cx = (int)Math.Min(width - 1, (i + 0.5) * cellSrc);
                    int ww = Math.Min(width, bw < width ? Math.Min(bw, 512) : 128);
                    int wh = Math.Min(height, bh < height ? Math.Max(Math.Min(bh, 512), 16) : 128);
                    int x0 = Math.Clamp(bw < width ? cx / bw * bw : cx - ww / 2, 0, width - ww);
                    int y0 = Math.Clamp(bh < height ? cy / bh * bh : cy - wh / 2, 0, height - wh);

                    bool ok = true;
                    for (int b = 0; b < buf.Length && ok; b++)
                    {
                        int bandNo = b < colorBands ? b + 1 : 4;
                        ok = ds.GetRasterBand(bandNo).ReadRaster(x0, y0, ww, wh, buf[b], Sub, Sub, 0, 0) == CPLErr.CE_None;
                    }
                    if (!ok) continue;

                    Array.Clear(sum);
                    int n = 0;
                    for (int p = 0; p < Sub * Sub; p++)
                    {
                        if (hasAlpha && buf[colorBands][p] <= 0f) continue;
                        bool skip = false, allZero = true;
                        for (int b = 0; b < colorBands; b++)
                        {
                            float v = buf[b][p];
                            if (float.IsNaN(v) || float.IsInfinity(v) || (hasNoData[b] && v == (float)noData[b])) { skip = true; break; }
                            if (v != 0f) allZero = false;
                        }
                        if (skip || (zeroIsNoData && allZero)) continue;
                        for (int b = 0; b < colorBands; b++) sum[b] += buf[b][p];
                        n++;
                    }
                    if (n < Sub * Sub / 16) continue;

                    int idx = j * gx + i;
                    for (int b = 0; b < colorBands; b++) mean[b][idx] = (float)(sum[b] / n);
                    valid[idx] = true;
                }
                return ds;
            }, ds => ds.Dispose());

            if (dtype != DataType.GDT_Byte)
            {
                for (int b = 0; b < colorBands; b++)
                {
                    var vals = new List<float>(nCells);
                    for (int c = 0; c < nCells; c++) if (valid[c]) vals.Add(mean[b][c]);
                    if (vals.Count == 0) continue;
                    vals.Sort();
                    float lo = vals[(int)(0.02 * (vals.Count - 1))];
                    float hi = vals[(int)(0.98 * (vals.Count - 1))];
                    if (hi <= lo) hi = lo + 1f;
                    for (int c = 0; c < nCells; c++)
                        if (valid[c]) mean[b][c] = Math.Clamp((mean[b][c] - lo) / (hi - lo) * 255f, 0f, 255f);
                }
            }

            var bgra = new byte[outW * outH * 4];
            Parallel.For(0, outH, py =>
            {
                double v = (py + 0.5) / outH * gy - 0.5;
                int j0 = (int)Math.Floor(v);
                double fv = v - j0;
                for (int px = 0; px < outW; px++)
                {
                    double u = (px + 0.5) / outW * gx - 0.5;
                    int i0 = (int)Math.Floor(u);
                    double fu = u - i0;

                    double wSum = 0, c0 = 0, c1 = 0, c2 = 0;
                    for (int dj = 0; dj < 2; dj++)
                    {
                        int cj = Math.Clamp(j0 + dj, 0, gy - 1);
                        double wy = dj == 0 ? 1 - fv : fv;
                        for (int di = 0; di < 2; di++)
                        {
                            int ci = Math.Clamp(i0 + di, 0, gx - 1);
                            int idx = cj * gx + ci;
                            if (!valid[idx]) continue;
                            double w = wy * (di == 0 ? 1 - fu : fu);
                            wSum += w;
                            c0 += w * mean[0][idx];
                            if (colorBands == 3) { c1 += w * mean[1][idx]; c2 += w * mean[2][idx]; }
                        }
                    }

                    int o = (py * outW + px) * 4;
                    if (wSum < 0.5) continue;
                    byte r = (byte)Math.Clamp(c0 / wSum, 0, 255);
                    byte g = colorBands == 3 ? (byte)Math.Clamp(c1 / wSum, 0, 255) : r;
                    byte b2 = colorBands == 3 ? (byte)Math.Clamp(c2 / wSum, 0, 255) : r;
                    bgra[o] = b2; bgra[o + 1] = g; bgra[o + 2] = r; bgra[o + 3] = 255;
                }
            });

            return bgra;
        }
    }
}
