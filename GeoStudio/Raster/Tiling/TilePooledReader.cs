using System;
using System.Collections.Generic;
using OSGeo.GDAL;

namespace GeoStudio.Raster
{
    internal sealed class PooledDataset : IDisposable
    {
        public Dataset Ds = null!;
        public Dataset? Src;            // source kept alive underneath a warped VRT
        public int Version;
        public double[] Gt = new double[6];
        public int W, H;
        public int[] Colors = Array.Empty<int>();
        public int Alpha;
        public DataType DType;
        public bool HasNd;
        public double Nd;
        public void Dispose() { Ds?.Dispose(); Src?.Dispose(); }
    }

    internal sealed class TileLease : IDisposable
    {
        private readonly TileLayer _l;
        public readonly PooledDataset Item;
        public TileLease(TileLayer l, PooledDataset item) { _l = l; Item = item; }
        public void Dispose()
        {
            if (Item.Version == _l.Version && _l.Pool.Count < 8) _l.Pool.Add(Item);
            else Item.Dispose();
        }
    }

    internal static class TilePooledReader
    {
        public static TileLease? Rent(TileLayer layer, int ver, string mercatorWkt)
        {
            while (layer.Pool.TryTake(out var pooled))
            {
                if (pooled.Version == ver) return new TileLease(layer, pooled);
                pooled.Dispose();
            }
            var p = OpenPooled(layer, ver, mercatorWkt);
            return p == null ? null : new TileLease(layer, p);
        }

        private static PooledDataset? OpenPooled(TileLayer layer, int ver, string mercatorWkt)
        {
            Dataset? src = null, ds = null;
            try
            {
                string? cog = layer.CogPath;
                if (cog != null)
                {
                    ds = Gdal.Open(cog, Access.GA_ReadOnly);
                }
                else
                {
                    src = Gdal.Open(layer.SourcePath, Access.GA_ReadOnly);
                    string wkt = src.GetProjectionRef();
                    if (string.IsNullOrWhiteSpace(wkt)) { src.Dispose(); return null; }
                    if (CogBuilder.IsWebMercator(wkt)) { ds = src; src = null; }
                    else ds = Gdal.AutoCreateWarpedVRT(src, wkt, mercatorWkt, ResampleAlg.GRA_Bilinear, 0.125);
                }
                if (ds == null) { src?.Dispose(); return null; }

                var p = new PooledDataset { Ds = ds, Src = src, Version = ver, W = ds.RasterXSize, H = ds.RasterYSize };
                ds.GetGeoTransform(p.Gt);
                if (p.Gt[1] == 0 || p.Gt[5] == 0) { p.Dispose(); return null; }

                var colors = new List<int>();
                for (int b = 1; b <= ds.RasterCount; b++)
                {
                    var band = ds.GetRasterBand(b);
                    if (band.GetColorInterpretation() == ColorInterp.GCI_AlphaBand) p.Alpha = b;
                    else if (colors.Count < 3) colors.Add(b);
                }
                if (colors.Count == 2) colors.RemoveAt(1);
                if (colors.Count == 0) { p.Dispose(); return null; }
                p.Colors = colors.ToArray();

                var b1 = ds.GetRasterBand(p.Colors[0]);
                p.DType = b1.DataType;
                b1.GetNoDataValue(out double nd, out int has);
                p.HasNd = has != 0;
                p.Nd = nd;
                return p;
            }
            catch
            {
                ds?.Dispose();
                src?.Dispose();
                return null;
            }
        }
    }
}
