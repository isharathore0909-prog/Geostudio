using System;
using System.Collections.Concurrent;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

namespace GeoStudio.Raster
{
    public enum LayerTier { Preview, Direct, Optimized }
    public static class CacheKeys
    {
        public static string For(string path)
        {
            var fi = new FileInfo(path);
            string s = $"{Path.GetFullPath(path).ToLowerInvariant()}|{fi.Length}|{fi.LastWriteTimeUtc.Ticks}";
            return Convert.ToHexString(SHA1.HashData(Encoding.UTF8.GetBytes(s)))[..16];
        }
    }

    public static class OptimizationQueue
    {
        private sealed class Job
        {
            public string LayerId = "";
            public string FinalPath = "";
            public Func<string, Action<int>, CancellationToken, bool> Work = null!;
            public readonly CancellationTokenSource Cts = new();
        }

        public static event Action<string, int>? Progress;
        public static event Action<string, string>? Completed;
        public static event Action<string, string>? Failed;

        private static readonly BlockingCollection<Job> _queue = new();
        private static readonly ConcurrentDictionary<string, Job> _jobs = new();
        private static Thread? _worker;
        private static readonly object _startLock = new();
        private static long _lastActivityTicks;

        public static void NotifyViewportActivity() => Interlocked.Exchange(ref _lastActivityTicks, DateTime.UtcNow.Ticks);

        private static bool ViewportBusy =>
            DateTime.UtcNow.Ticks - Interlocked.Read(ref _lastActivityTicks) < TimeSpan.FromMilliseconds(500).Ticks;

        internal static void ReportFailed(string layerId, string message) => Failed?.Invoke(layerId, message);

        public static void Enqueue(string layerId, string finalPath, Func<string, Action<int>, CancellationToken, bool> work)
        {
            if (File.Exists(finalPath) && new FileInfo(finalPath).Length > 0)
            {
                Completed?.Invoke(layerId, finalPath);
                return;
            }

            Directory.CreateDirectory(Path.GetDirectoryName(finalPath)!);
            var job = new Job { LayerId = layerId, FinalPath = finalPath, Work = work };
            if (_jobs.TryRemove(layerId, out var old)) old.Cts.Cancel();
            _jobs[layerId] = job;
            EnsureWorker();
            _queue.Add(job);
            Progress?.Invoke(layerId, 0);
        }

        public static void Cancel(string layerId)
        {
            if (_jobs.TryGetValue(layerId, out var job)) job.Cts.Cancel();
        }

        public static void CleanupStaleTemps(string rootDir)
        {
            try
            {
                if (!Directory.Exists(rootDir)) return;
                foreach (var f in Directory.EnumerateFiles(rootDir, "*.tmp", SearchOption.AllDirectories))
                    TryDelete(f);
            }
            catch { }
        }

        private static void EnsureWorker()
        {
            lock (_startLock)
            {
                if (_worker != null) return;
                _worker = new Thread(Run) { IsBackground = true, Name = "GeoStudio.Optimizer", Priority = ThreadPriority.BelowNormal };
                _worker.Start();
            }
        }

        private static void Run()
        {
            foreach (var job in _queue.GetConsumingEnumerable())
            {
                var ct = job.Cts.Token;
                if (ct.IsCancellationRequested) { _jobs.TryRemove(job.LayerId, out _); continue; }

                string tmp = job.FinalPath + ".tmp";
                try
                {
                    TryDelete(tmp);
                    int last = -1;
                    bool ok = job.Work(tmp, pct =>
                    {
                        while (ViewportBusy && !ct.IsCancellationRequested) Thread.Sleep(100);
                        if (pct == last) return;
                        last = pct;
                        Progress?.Invoke(job.LayerId, pct);
                    }, ct);

                    if (ct.IsCancellationRequested) { TryDelete(tmp); continue; }

                    if (ok && File.Exists(tmp) && new FileInfo(tmp).Length > 0)
                    {
                        File.Move(tmp, job.FinalPath, overwrite: true);
                        Completed?.Invoke(job.LayerId, job.FinalPath);
                    }
                    else
                    {
                        TryDelete(tmp);
                        Failed?.Invoke(job.LayerId, "Optimization did not produce a file.");
                    }
                }
                catch (Exception ex)
                {
                    TryDelete(tmp);
                    Failed?.Invoke(job.LayerId, ex.Message);
                }
                finally
                {
                    _jobs.TryRemove(job.LayerId, out _);
                }
            }
        }

        private static void TryDelete(string path)
        {
            try { if (File.Exists(path)) File.Delete(path); } catch { }
        }
    }
}
