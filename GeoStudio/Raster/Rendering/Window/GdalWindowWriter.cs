using System;
using System.IO;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using OSGeo.OSR;

namespace GeoStudio.Raster
{
    internal static class GdalWindowWriter
    {
        public static WindowRenderResult SavePngAndComputeResult(
            byte[] bgra, int targetW, int targetH,
            double[] gt, int xOff, int xEnd, int yOff, int yEnd,
            CoordinateTransformation? ctTo4326)
        {
            string cacheDir = GdalCacheManager.GetCacheDirectory();
            string cacheFile = $"win_{Guid.NewGuid():N}.png";
            string outPath = Path.Combine(cacheDir, cacheFile);

            GdalCacheManager.PruneCache();

            var bmp = BitmapSource.Create(targetW, targetH, 96, 96, PixelFormats.Bgra32, null, bgra, targetW * 4);
            bmp.Freeze();

            using (var fs = new FileStream(outPath, FileMode.Create, FileAccess.Write, FileShare.None, 65536))
            {
                var enc = new PngBitmapEncoder();
                enc.Frames.Add(BitmapFrame.Create(bmp));
                enc.Save(fs);
                fs.Flush(true);
            }

            double exactMinX = gt[0] + (xOff * gt[1]);
            double exactMaxX = gt[0] + (xEnd * gt[1]);
            double exactMaxY = gt[3] + (yOff * gt[5]);
            double exactMinY = gt[3] + (yEnd * gt[5]);

            if (ctTo4326 != null)
            {
                double[] p1 = new double[] { exactMinX, exactMinY, 0 };
                double[] p2 = new double[] { exactMaxX, exactMaxY, 0 };
                ctTo4326.TransformPoint(p1);
                ctTo4326.TransformPoint(p2);
                exactMinX = Math.Min(p1[0], p2[0]);
                exactMinY = Math.Min(p1[1], p2[1]);
                exactMaxX = Math.Max(p1[0], p2[0]);
                exactMaxY = Math.Max(p1[1], p2[1]);
                ctTo4326.Dispose();
            }

            return new WindowRenderResult
            {
                Success = true,
                ImageUrl = $"http://cache.geostudio.local/{cacheFile}",
                Extent = new double[]
                {
                    Math.Min(exactMinX, exactMaxX),
                    Math.Min(exactMinY, exactMaxY),
                    Math.Max(exactMinX, exactMaxX),
                    Math.Max(exactMinY, exactMaxY)
                }
            };
        }
    }
}
