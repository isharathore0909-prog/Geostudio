using System;
using System.Collections.Generic;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Threading.Tasks;
using GeoStudio.Raster;

namespace GeoStudio.PointCloud
{
    public static class LasSampleReader
    {
        public static unsafe LasSampleResult Read(string path, LasCrsInfo crs, int targetPoints = 800_000)
        {
            GdalRasterService.Initialize();

            if (string.Equals(Path.GetExtension(path), ".laz", StringComparison.OrdinalIgnoreCase))
                throw new NotSupportedException("LAZ (compressed) files are not supported by the instant LAS preview yet.");

            using var mmf = MemoryMappedFile.CreateFromFile(path, FileMode.Open, null, 0, MemoryMappedFileAccess.Read);
            using var accessor = mmf.CreateViewAccessor(0, 0, MemoryMappedFileAccess.Read);
            byte* ptr = null;
            accessor.SafeMemoryMappedViewHandle.AcquirePointer(ref ptr);
            try
            {
                long fileLen = accessor.Capacity;
                if (fileLen < 227 || ptr[0] != (byte)'L' || ptr[1] != (byte)'A' || ptr[2] != (byte)'S' || ptr[3] != (byte)'F')
                    throw new InvalidDataException("Not a valid standard LAS file.");

                byte vMinor = ptr[25];
                uint dataOffset = *(uint*)(ptr + 96);
                byte fmtRaw = ptr[104];
                if ((fmtRaw & 0xC0) != 0)
                    throw new NotSupportedException("LAZ (compressed) files must be decompressed to LAS first.");

                int fmt = fmtRaw & 0x3F;
                int recLen = *(ushort*)(ptr + 105);
                ulong total = *(uint*)(ptr + 107);
                if (vMinor >= 4 && fileLen >= 255)
                {
                    ulong t14 = *(ulong*)(ptr + 247);
                    if (t14 > 0) total = t14;
                }
                if (recLen < 20) throw new InvalidDataException("Unsupported point record length.");
                ulong avail = (ulong)Math.Max(0, (fileLen - dataOffset) / recLen);
                if (total == 0 || total > avail) total = avail;
                if (total == 0) throw new InvalidDataException("LAS file contains no points.");

                double sx = *(double*)(ptr + 131), sy = *(double*)(ptr + 139), sz = *(double*)(ptr + 147);
                double ox = *(double*)(ptr + 155), oy = *(double*)(ptr + 163), oz = *(double*)(ptr + 171);
                double maxX = *(double*)(ptr + 179), minX = *(double*)(ptr + 187);
                double maxY = *(double*)(ptr + 195), minY = *(double*)(ptr + 203);
                double maxZ = *(double*)(ptr + 211), minZ = *(double*)(ptr + 219);

                int clsOff = fmt >= 6 ? 16 : 15;
                byte clsMask = fmt >= 6 ? (byte)0xFF : (byte)0x1F;
                int rgbOff = fmt switch { 2 => 20, 3 => 28, 5 => 28, 7 => 30, 8 => 30, 10 => 30, _ => -1 };
                bool hasRgbFmt = rgbOff > 0 && recLen >= rgbOff + 6;

                ulong step = Math.Max(1, total / (ulong)targetPoints);
                int count = (int)(total / step);

                double realMinX = Math.Min(minX, maxX);
                double realMaxX = Math.Max(minX, maxX);
                double realMinY = Math.Min(minY, maxY);
                double realMaxY = Math.Max(minY, maxY);
                double[] bounds = { realMinX, realMinY, realMaxX, realMaxY };
                bool reproj = false, assumed = false;
                using (var mainT = CrsTransform.Create(crs, realMinX, realMaxX, realMinY, realMaxY))
                {
                    if (mainT != null)
                    {
                        reproj = true;
                        assumed = mainT.Assumed;
                        double bx0 = double.MaxValue, by0 = double.MaxValue, bx1 = double.MinValue, by1 = double.MinValue;
                        foreach (var (cx, cy) in new[] { (realMinX, realMinY), (realMaxX, realMinY), (realMinX, realMaxY), (realMaxX, realMaxY) })
                        {
                            var p = new[] { cx, cy, minZ };
                            mainT.Ct.TransformPoint(p);
                            bx0 = Math.Min(bx0, p[0]); bx1 = Math.Max(bx1, p[0]);
                            by0 = Math.Min(by0, p[1]); by1 = Math.Max(by1, p[1]);
                        }
                        bounds = new[] { Math.Min(bx0, bx1), Math.Min(by0, by1), Math.Max(bx0, bx1), Math.Max(by0, by1) };
                    }
                }
                int digits = (reproj || (Math.Abs(bounds[0]) <= 180 && Math.Abs(bounds[2]) <= 180)) ? 7 : 3;

                var xs = new double[count];
                var ys = new double[count];
                var zs = new float[count];
                var inten = new byte[count];
                var cls = new byte[count];
                var retNum = new byte[count];
                var numRet = new byte[count];
                var scanAng = new byte[count];
                var ptSrc = new byte[count * 2];
                var flags = new byte[count];
                var r16 = new ushort[hasRgbFmt ? count : 0];
                var g16 = new ushort[hasRgbFmt ? count : 0];
                var b16 = new ushort[hasRgbFmt ? count : 0];
                var nirBytes = (fmt == 8 && recLen >= 38) ? new byte[count] : null;

                byte* basePtr = ptr + dataOffset;

                var opts = new ParallelOptions { MaxDegreeOfParallelism = Math.Clamp(Environment.ProcessorCount, 1, 8) };
                Parallel.For(0, count, opts, () => new Worker(reproj ? crs : (LasCrsInfo?)null, realMinX, realMaxX, realMinY, realMaxY), (i, _, w) =>
                {
                    byte* p = basePtr + ((long)i * (long)step * (long)recLen);
                    int rx = *(int*)p;
                    int ry = *(int*)(p + 4);
                    int rz = *(int*)(p + 8);
                    ushort rawInten = *(ushort*)(p + 12);
                    byte retByte = *(p + 14);

                    byte rn, nr, clsVal, wth, kp, ovl;
                    int saDeg;
                    ushort psVal;

                    if (fmt >= 6)
                    {
                        rn = (byte)(retByte & 0x0F);
                        nr = (byte)((retByte >> 4) & 0x0F);
                        byte flgByte = *(p + 15);
                        wth = (byte)((flgByte >> 2) & 1);
                        kp = (byte)((flgByte >> 1) & 1);
                        ovl = (byte)((flgByte >> 3) & 1);
                        clsVal = *(p + 16);
                        short saRaw = *(short*)(p + 18);
                        saDeg = (int)Math.Round(saRaw * 0.006);
                        psVal = *(ushort*)(p + 20);
                        if (nirBytes != null)
                        {
                            ushort rawNir = *(ushort*)(p + 36);
                            nirBytes[i] = (byte)(rawNir > 255 ? (rawNir >> 8) : rawNir);
                        }
                    }
                    else
                    {
                        rn = (byte)(retByte & 0x07);
                        nr = (byte)((retByte >> 3) & 0x07);
                        byte clsByte = *(p + 15);
                        clsVal = (byte)(clsByte & 0x1F);
                        wth = (byte)((clsByte >> 7) & 1);
                        kp = (byte)((clsByte >> 6) & 1);
                        ovl = (byte)(clsVal == 12 ? 1 : 0);
                        sbyte saRank = *(sbyte*)(p + 16);
                        saDeg = saRank;
                        psVal = *(ushort*)(p + 18);
                    }

                    retNum[i] = rn > 0 ? rn : (byte)1;
                    numRet[i] = nr > 0 ? nr : (byte)1;
                    flags[i] = (byte)(wth | (kp << 1) | (ovl << 2));
                    scanAng[i] = (byte)Math.Clamp(saDeg + 128, 0, 255);
                    ptSrc[i * 2] = (byte)(psVal & 0xFF);
                    ptSrc[i * 2 + 1] = (byte)((psVal >> 8) & 0xFF);

                    double curX = rx * sx + ox;
                    double curY = ry * sy + oy;
                    double curZ = rz * sz + oz;

                    if (w.T != null)
                    {
                        w.Pt[0] = curX; w.Pt[1] = curY; w.Pt[2] = curZ;
                        w.T.Ct.TransformPoint(w.Pt);
                        curX = w.Pt[0]; curY = w.Pt[1];
                    }

                    xs[i] = Math.Round(curX, digits);
                    ys[i] = Math.Round(curY, digits);
                    zs[i] = (float)Math.Round(curZ, 2);
                    inten[i] = (byte)(rawInten > 255 ? (rawInten >> 8) : rawInten);
                    cls[i] = clsVal;

                    if (hasRgbFmt)
                    {
                        r16[i] = *(ushort*)(p + rgbOff);
                        g16[i] = *(ushort*)(p + rgbOff + 2);
                        b16[i] = *(ushort*)(p + rgbOff + 4);
                    }
                    return w;
                }, w => w.Dispose());

                byte[]? r = null;
                byte[]? g = null;
                byte[]? b = null;
                bool hasRgb = false;
                if (hasRgbFmt)
                {
                    var vals = new List<ushort>(3200);
                    int sampleStep = Math.Max(1, count / 1000);
                    for (int i = 0; i < count; i += sampleStep)
                        if (r16[i] > 0 || g16[i] > 0 || b16[i] > 0) { vals.Add(r16[i]); vals.Add(g16[i]); vals.Add(b16[i]); }

                    hasRgb = vals.Count > 0;
                    if (hasRgb)
                    {
                        r = new byte[count];
                        g = new byte[count];
                        b = new byte[count];

                        float cMin = 0f, cMax = 255f;
                        if (vals.Count > 60)
                        {
                            vals.Sort();
                            if (vals[^1] > 255)
                            {
                                ushort p1 = vals[Math.Clamp((int)(vals.Count * 0.01), 0, vals.Count - 1)];
                                ushort p99 = vals[Math.Clamp((int)(vals.Count * 0.99), 0, vals.Count - 1)];
                                if (p99 - p1 > 100) { cMin = p1; cMax = p99; } else { cMin = 0; cMax = 65535; }
                            }
                        }
                        float range = Math.Max(1f, cMax - cMin);
                        for (int i = 0; i < count; i++)
                        {
                            if (cMax > 255f)
                            {
                                r[i] = (byte)Math.Clamp((int)((r16[i] - cMin) / range * 255f), 0, 255);
                                g[i] = (byte)Math.Clamp((int)((g16[i] - cMin) / range * 255f), 0, 255);
                                b[i] = (byte)Math.Clamp((int)((b16[i] - cMin) / range * 255f), 0, 255);
                            }
                            else
                            {
                                r[i] = (byte)Math.Min(r16[i], (ushort)255);
                                g[i] = (byte)Math.Min(g16[i], (ushort)255);
                                b[i] = (byte)Math.Min(b16[i], (ushort)255);
                            }
                        }
                    }
                }
                int unassigned = 0;
                int checkMax = Math.Min(count, 2000);
                for (int i = 0; i < checkMax; i++) if (cls[i] <= 1) unassigned++;
                if (unassigned > (checkMax * 0.5))
                {
                    cls = PointCloudClassifier.ClassifySMRF(xs, ys, zs);
                }

                return new LasSampleResult
                {
                    Batch = new PointCloudBatch
                    {
                        count = count,
                        x = xs,
                        y = ys,
                        z = zs,
                        i = inten,
                        c = cls,
                        r = r,
                        g = g,
                        b = b,
                        rn = retNum,
                        nr = numRet,
                        sa = scanAng,
                        ps = ptSrc,
                        fl = flags,
                        nir = nirBytes,
                        hasRgb = hasRgb
                    },
                    TotalPoints = (long)total,
                    Bounds = bounds,
                    MinZ = minZ,
                    MaxZ = maxZ,
                    HasRgb = hasRgb,
                    Reprojected = reproj,
                    AssumedCrs = assumed
                };
            }
            finally
            {
                accessor.SafeMemoryMappedViewHandle.ReleasePointer();
            }
        }
    }
}
