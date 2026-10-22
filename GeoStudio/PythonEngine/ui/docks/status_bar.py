# -*- coding: utf-8 -*-
"""GeoStudio - Status Bar with coordinates, elevation, CRS, scale, file loading metrics, and progress."""

import time
from PyQt5.QtWidgets import (
    QStatusBar, QLabel, QProgressBar, QWidget, QHBoxLayout, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class GeoStatusBar(QStatusBar):
    """
    Custom workstation status bar showing:
    - Current map coordinates (mouse position)
    - Real-time elevation value at cursor (Z/Elevation)
    - Map scale
    - Project CRS
    - Active layer name
    - File loading metrics (Progress %, loaded file size, stage, elapsed load duration)
    - Progress bar indicator
    - Status badge
    """

    def __init__(self, map_canvas, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self._load_start_time = None
        self._active_loading_file = None
        self._active_file_size = ""
        self._hide_progress_timer = QTimer(self)
        self._hide_progress_timer.setSingleShot(True)
        self._hide_progress_timer.timeout.connect(self._hide_progress)

        self.setStyleSheet("""
            QStatusBar {
                background: #ffffff;
                color: #475569;
                border-top: 1px solid #e2e8f0;
                padding: 2px 6px;
            }
            QLabel {
                color: #334155;
                font-size: 11px;
                padding: 2px 8px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QProgressBar {
                min-width: 130px;
                max-width: 170px;
                max-height: 16px;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background: #f1f5f9;
                text-align: center;
                font-size: 10px;
                font-weight: 600;
                color: #0f172a;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #334155);
                border-radius: 3px;
            }
        """)
        self._build_widgets()
        self._connect_canvas()

    def _build_widgets(self):
        self.setSizeGripEnabled(False)

        # Coordinate display
        self.coord_label = QLabel("🌐 X: ─────  Y: ─────")
        self.coord_label.setMinimumWidth(220)

        # Elevation display (Real-time cursor elevation)
        self.elev_label = QLabel("🏔 Elev: ─────")
        self.elev_label.setMinimumWidth(110)
        self.elev_label.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 2px 8px; color: #94a3b8;")

        # Scale
        self.scale_label = QLabel("📐 Scale: 1:──────")
        self.scale_label.setMinimumWidth(125)

        # CRS
        self.crs_label = QLabel("🌐 CRS: ──────")
        self.crs_label.setMinimumWidth(115)

        # Active layer
        self.layer_label = QLabel("🗂 Layer: None")
        self.layer_label.setMinimumWidth(140)

        # File loading / metrics info widget
        self.file_load_label = QLabel("📁 Ready")
        self.file_load_label.setMinimumWidth(180)
        self.file_load_label.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 2px 8px; color: #64748b; font-weight: 500;")

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setVisible(False)

        # Status message badge
        self.msg_label = QLabel("● Ready")
        self.msg_label.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 4px; padding: 2px 10px; color: #16a34a; font-weight: 600;")

        self.addWidget(self.coord_label)
        self.addWidget(self.elev_label)
        self.addWidget(self.scale_label)
        self.addWidget(self.crs_label)
        self.addWidget(self.layer_label)
        self.addWidget(self.file_load_label)
        self.addWidget(self.progress)
        self.addPermanentWidget(self.msg_label)

    def _connect_canvas(self):
        if self.map_canvas and self.map_canvas.canvas:
            self.map_canvas.coordinate_changed.connect(self._update_coords)
            if hasattr(self.map_canvas, 'elevation_changed'):
                self.map_canvas.elevation_changed.connect(self._update_elevation)
            self.map_canvas.canvas.scaleChanged.connect(self._update_scale)
            self.map_canvas.canvas.destinationCrsChanged.connect(self._update_crs)
            try:
                from qgis.core import QgsProject
                QgsProject.instance().crsChanged.connect(self._update_crs)
            except Exception:
                pass
            self._update_scale(self.map_canvas.get_scale())
            self._update_crs()

    def _update_coords(self, x, y):
        self.coord_label.setText(f"X: {x:>12.4f}  Y: {y:>12.4f}")

    def _update_elevation(self, elev_val):
        if elev_val is not None:
            self.elev_label.setText(f"🏔 {elev_val:,.1f} m")
            self.elev_label.setStyleSheet("color: #b45309; font-weight: bold; background: #fffbeb; border: 1px solid #fde68a;")
        else:
            self.elev_label.setText("Elev: ─────")
            self.elev_label.setStyleSheet("color: #94a3b8; background: #f8fafc; border: 1px solid #e2e8f0;")

    def _update_scale(self, scale=None):
        if scale is None:
            scale = self.map_canvas.get_scale()
        self.scale_label.setText(f"Scale: 1:{int(scale):,}")

    def _update_crs(self):
        crs = self.map_canvas.get_crs()
        self.crs_label.setText(f"CRS: {crs}")

    def set_layer(self, name: str):
        self.layer_label.setText(f"Layer: {name}")

    def set_message(self, msg: str, timeout_ms: int = 4000):
        self.msg_label.setText(msg)
        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda: self.msg_label.setText("● Ready"))

    def showMessage(self, msg: str, timeout: int = 0):
        self.set_message(msg, timeout)

    def set_progress(self, value: int, text: str = None):
        if value <= 0:
            self.progress.setVisible(False)
            self.progress.setValue(0)
        elif value >= 100:
            self.progress.setValue(100)
            self._hide_progress_timer.start(700)
        else:
            self._hide_progress_timer.stop()
            self.progress.setVisible(True)
            self.progress.setValue(value)
        if text:
            self.progress.setFormat(f"{text} ({value}%)")
        else:
            self.progress.setFormat("%p%")

    def _hide_progress(self):
        self.progress.setVisible(False)

    # ── File Loading & Load Duration Telemetry ──────────────────────────────
    def start_file_loading(self, file_name: str, file_size_str: str = "", stage: str = "Loading..."):
        """Called when a file begins loading to initialize progress and timer."""
        self._hide_progress_timer.stop()
        self._load_start_time = time.perf_counter()
        self._active_loading_file = file_name
        self._active_file_size = file_size_str

        self.progress.setVisible(True)
        self.progress.setValue(10)
        self.progress.setFormat("%p%")

        size_part = f" ({file_size_str})" if file_size_str else ""
        stage_part = f" • {stage}" if stage else ""
        self.file_load_label.setText(f"⏳ Loading {file_name}{size_part}{stage_part}")
        self.file_load_label.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 4px; padding: 2px 8px; color: #1d4ed8; font-weight: 600;")
        
        self.msg_label.setText("⏳ Loading...")
        self.msg_label.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 4px; padding: 2px 10px; color: #1d4ed8; font-weight: 600;")
        QApplication.processEvents()

    def update_file_loading(self, percent: int, stage: str = ""):
        """Updates live progress percentage, stage description, and elapsed timer."""
        self._hide_progress_timer.stop()
        self.progress.setVisible(True)
        self.progress.setValue(max(0, min(100, percent)))
        self.progress.setFormat("%p%")

        start_t = self._load_start_time or time.perf_counter()
        elapsed = time.perf_counter() - start_t
        file_name = self._active_loading_file or "dataset"
        size_part = f" ({self._active_file_size})" if self._active_file_size else ""
        stage_part = f" — {stage}" if stage else ""
        
        self.file_load_label.setText(f"⏳ {file_name}{size_part} • {percent}%{stage_part} ({elapsed:.1f}s)")
        QApplication.processEvents()

    def finish_file_loading(self, file_name: str, elapsed_seconds: float = None, file_size_str: str = "", layer_type: str = ""):
        """Called when a file completes loading, displaying the total duration and size."""
        if elapsed_seconds is None:
            start_t = self._load_start_time or time.perf_counter()
            elapsed_seconds = max(0.001, time.perf_counter() - start_t)

        self.progress.setValue(100)
        self.progress.setFormat("100%")
        self._hide_progress_timer.start(800)

        # Format load duration nicely
        if elapsed_seconds < 0.05:
            duration_str = f"{elapsed_seconds * 1000:.0f} ms"
        elif elapsed_seconds < 60.0:
            duration_str = f"{elapsed_seconds:.2f} s"
        else:
            mins = int(elapsed_seconds // 60)
            secs = elapsed_seconds % 60
            duration_str = f"{mins}m {secs:.1f}s"

        size_display = f" ({file_size_str})" if file_size_str else ""
        status_text = f"⏱ Loaded {file_name}{size_display} in {duration_str}"
        
        self.file_load_label.setText(status_text)
        self.file_load_label.setToolTip(
            f"Dataset: {file_name}\n"
            f"Type: {layer_type or 'GIS Layer'}\n"
            f"Size: {file_size_str or 'N/A'}\n"
            f"Load Time: {duration_str}"
        )
        self.file_load_label.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 4px; padding: 2px 8px; color: #15803d; font-weight: 600;")

        self.msg_label.setText(f"✓ Ready ({duration_str})")
        self.msg_label.setStyleSheet("background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 4px; padding: 2px 10px; color: #16a34a; font-weight: 600;")
        
        # Clear loading tracker
        self._load_start_time = None
        self._active_loading_file = None
        self._active_file_size = ""
        QApplication.processEvents()

    def fail_file_loading(self, file_name: str, elapsed_seconds: float = None, error_msg: str = ""):
        """Called when file loading encounters an error, displaying elapsed time before failure."""
        if elapsed_seconds is None:
            start_t = self._load_start_time or time.perf_counter()
            elapsed_seconds = max(0.001, time.perf_counter() - start_t)

        self.progress.setVisible(False)
        duration_str = f"{elapsed_seconds:.2f} s" if elapsed_seconds >= 0.05 else f"{elapsed_seconds * 1000:.0f} ms"
        
        self.file_load_label.setText(f"✕ Failed: {file_name} after {duration_str}")
        self.file_load_label.setToolTip(f"Failed to load {file_name}\nDuration: {duration_str}\nError: {error_msg}")
        self.file_load_label.setStyleSheet("background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px; padding: 2px 8px; color: #b91c1c; font-weight: 600;")

        self.msg_label.setText("✕ Load Error")
        self.msg_label.setStyleSheet("background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px; padding: 2px 10px; color: #b91c1c; font-weight: 600;")

        self._load_start_time = None
        self._active_loading_file = None
        self._active_file_size = ""
        QApplication.processEvents()

