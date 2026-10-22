# -*- coding: utf-8 -*-
"""
GeoStudio - Raster Auto-Optimizer
Automatically detects large raster layers missing overviews/pyramids and builds
multi-resolution overviews in a background thread for instantaneous zooming and panning.
"""

import os
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class RasterOverviewWorker(QThread):
    """Background worker to generate pyramids without freezing the GUI."""
    progress_changed = pyqtSignal(str, int)  # layer_name, percent
    finished_success = pyqtSignal(str, str)  # layer_name, file_path
    finished_error = pyqtSignal(str, str)    # layer_name, error_msg

    def __init__(self, file_path, layer_name, layer=None, canvas=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.layer_name = layer_name
        self.layer = layer
        self.canvas = canvas

    def run(self):
        try:
            from osgeo import gdal
            gdal.UseExceptions()

            gdal.SetConfigOption("COMPRESS_OVERVIEW", "DEFLATE")
            gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")

            # Try opening in Read-Only mode which generates an external .ovr file
            ds = gdal.Open(self.file_path, gdal.GA_ReadOnly)
            if ds is None:
                return

            band = ds.GetRasterBand(1)
            if band is None:
                return

            # Check if pyramids already exist
            if band.GetOverviewCount() > 0:
                return

            width = ds.RasterXSize
            height = ds.RasterYSize
            max_dim = max(width, height)

            # Compute pyramid levels based on raster dimensions
            levels = []
            f = 2
            while (max_dim // f) >= 128 and f <= 256:
                levels.append(f)
                f *= 2

            if not levels:
                levels = [2, 4, 8, 16, 32]

            def gdal_progress_cb(complete, message, user_data):
                pct = int(complete * 100)
                self.progress_changed.emit(self.layer_name, pct)
                return 1

            # Build overviews using average resampling
            ds.BuildOverviews("AVERAGE", levels, gdal_progress_cb)
            ds.FlushCache()
            ds = None

            self.finished_success.emit(self.layer_name, self.file_path)

        except Exception as e:
            self.finished_error.emit(self.layer_name, str(e))


class AutoRasterOptimizer(QObject):
    """
    Monitors loaded raster layers and automatically builds pyramids in the background.
    """
    status_message = pyqtSignal(str, int)  # message, timeout_ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_workers = {}
        self._processed_paths = set()

    def check_and_optimize(self, layer, canvas=None):
        """Check if layer needs pyramids and triggers background generation."""
        if not layer or not layer.isValid():
            return

        source = layer.source()
        if not source or not os.path.isfile(source):
            return

        # Skip if already processed in this session
        norm_path = os.path.normpath(source)
        if norm_path in self._processed_paths or norm_path in self._active_workers:
            return

        try:
            from osgeo import gdal
            ds = gdal.Open(source, gdal.GA_ReadOnly)
            if ds is None:
                return

            width = ds.RasterXSize
            height = ds.RasterYSize

            # If small raster (< 1500 px), pyramids are unnecessary
            if width <= 1500 and height <= 1500:
                ds = None
                return

            band = ds.GetRasterBand(1)
            if band is None:
                ds = None
                return

            has_overviews = band.GetOverviewCount() > 0
            band = None
            ds = None

            if not has_overviews:
                self._start_worker(norm_path, layer.name(), layer, canvas)

        except Exception as e:
            print(f"[AutoRasterOptimizer] Error checking {source}: {e}")

    def _start_worker(self, path, name, layer, canvas):
        self.status_message.emit(
            f"⚡ Auto-optimizing '{name}' ({layer.width()}x{layer.height()}) for instant zooming...", 0
        )

        worker = RasterOverviewWorker(path, name, layer, canvas, self)
        self._active_workers[path] = worker

        worker.progress_changed.connect(self._on_progress)
        worker.finished_success.connect(self._on_success)
        worker.finished_error.connect(self._on_error)
        worker.start()

    def _on_progress(self, name, pct):
        self.status_message.emit(
            f"⚡ Building fast zoom overviews for '{name}'... {pct}%", 0
        )

    def _on_success(self, name, path):
        self._processed_paths.add(path)
        worker = self._active_workers.pop(path, None)
        if worker:
            try:
                if worker.layer and worker.layer.isValid():
                    worker.layer.reload()
                if worker.canvas:
                    worker.canvas.refresh()
            except Exception:
                pass

        self.status_message.emit(
            f"✓ '{name}' optimized! Zooming and panning is now instant.", 6000
        )

    def _on_error(self, name, error_msg):
        print(f"[AutoRasterOptimizer] Failed for {name}: {error_msg}")
        self.status_message.emit(
            f"⚠ Auto-overview failed for '{name}': {error_msg}", 5000
        )


# Global singleton instance
_optimizer_instance = None

def get_raster_optimizer():
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = AutoRasterOptimizer()
    return _optimizer_instance
