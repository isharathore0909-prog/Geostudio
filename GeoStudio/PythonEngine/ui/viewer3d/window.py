# -*- coding: utf-8 -*-
"""
GeoStudio - 3D Point Cloud Workstation Window
Provides the full workstation UI dialog, side controls, symbology picker, and snapshot exporter.
"""

import os
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFileDialog, QMessageBox, QApplication
)

from .reader import PointCloudReader
from .canvas import GLPointCloudCanvas
from .controls import build_3d_side_panel, COLOR_MODE_KEYS


class GeoStudio3DViewerWindow(QDialog):
    """Modern standalone 3D workstation visualizer dialog with real-time controls."""

    def __init__(self, parent=None, layer=None, file_path: str = None):
        super().__init__(parent)
        self.layer = layer
        raw_dem = (layer.customProperty("raw_dem_source") or getattr(layer, "_raw_dem_source", None)) if layer else None
        if not file_path:
            file_path = raw_dem if (raw_dem and os.path.exists(raw_dem)) else (layer.source() if layer else None)
        self.file_path = file_path
        self.max_points = 6000000
        self.pts_xyz = None

        self._init_window()
        self._build_ui()
        if self.file_path:
            QTimer.singleShot(100, self._load_data)

    def load_point_cloud(self, file_path: str):
        """Loads and visualizes a new point cloud file path."""
        self.file_path = file_path
        fname = os.path.basename(file_path) if file_path else "Point Cloud"
        self.setWindowTitle(f"GeoStudio 3D Visualizer — {fname}")
        if hasattr(self, 'lbl_dataset'):
            self.lbl_dataset.setText(f"Dataset: <b>{fname}</b>")
        self._load_data()

    def _init_window(self):
        fname = os.path.basename(self.file_path) if self.file_path else "Point Cloud"
        self.setWindowTitle(f"GeoStudio 3D Visualizer — {fname}")
        self.resize(1180, 780)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        self.setStyleSheet("""
            QDialog { background: #f8fafc; color: #0f172a; font-family: 'Segoe UI Variable Display', 'Segoe UI', 'Inter', sans-serif; }
            QLabel { color: #334155; font-size: 11px; }
            QGroupBox { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; color: #0f172a; font-size: 11px; font-weight: bold; margin-top: 12px; padding: 10px 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #0284c7; }
            QPushButton { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 5px; padding: 6px 12px; font-weight: 600; font-size: 11px; }
            QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }
            QPushButton:pressed { background: #e2e8f0; }
            QComboBox { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 8px; font-size: 11px; min-height: 24px; }
            QComboBox QAbstractItemView { background: #ffffff; color: #0f172a; selection-background-color: #38bdf8; selection-color: #ffffff; }
            QCheckBox { color: #334155; font-size: 11px; spacing: 6px; }
            QSlider::groove:horizontal { height: 4px; background: #e2e8f0; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #0284c7; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ffffff; border: 2px solid #0284c7; width: 14px; margin-top: -5px; margin-bottom: -5px; border-radius: 7px; }
        """)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Top Control Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        lbl_logo = QLabel("🌌 <b>3D WORKSTATION</b>")
        lbl_logo.setStyleSheet("color: #0284c7; font-size: 13px; font-weight: bold;")
        top_bar.addWidget(lbl_logo)

        fname = os.path.basename(self.file_path) if self.file_path else "No Dataset"
        self.lbl_dataset = QLabel(f"Dataset: <b>{fname}</b>")
        self.lbl_dataset.setStyleSheet("color: #64748b; font-size: 11px;")
        top_bar.addWidget(self.lbl_dataset)
        top_bar.addStretch()

        btn_top = QPushButton("Top View (2D)")
        btn_top.clicked.connect(lambda: self.canvas.set_top_view())
        top_bar.addWidget(btn_top)

        btn_iso = QPushButton("Isometric 3D")
        btn_iso.clicked.connect(lambda: self.canvas.set_isometric_view())
        top_bar.addWidget(btn_iso)

        btn_reset = QPushButton("Reset Camera")
        btn_reset.clicked.connect(lambda: self.canvas.reset_view())
        top_bar.addWidget(btn_reset)

        btn_screenshot = QPushButton("📸 Snapshot")
        btn_screenshot.clicked.connect(self._export_screenshot)
        top_bar.addWidget(btn_screenshot)

        main_layout.addLayout(top_bar)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)
        self.canvas = GLPointCloudCanvas(self)
        splitter.addWidget(self.canvas)

        side_panel = build_3d_side_panel(self)
        splitter.addWidget(side_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        main_layout.addWidget(splitter, 1)

    def _load_data(self):
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.warning(self, "3D Viewer", "No valid point cloud file selected.")
            return

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            res = PointCloudReader.load_las_points(self.file_path, max_points=self.max_points)
            if len(res) >= 10:
                pts_xyz, rgb, z_col, class_col, int_col, center, z_min, z_max, total_pts, color_dict = res
            else:
                pts_xyz, rgb, z_col, class_col, int_col, center, z_min, z_max, total_pts = res
                color_dict = {}

            self.pts_xyz = pts_xyz
            self.canvas.set_point_data(pts_xyz, rgb, z_col, class_col, int_col, mode="auto", color_dict=color_dict)

            rendered_count = len(pts_xyz)
            self.lbl_points.setText(f"Points in 3D: <b>{rendered_count:,}</b> (of {total_pts:,})")
            self.lbl_zrange.setText(f"Z Range: <b>{z_min:.1f} m – {z_max:.1f} m</b> (Δ {z_max - z_min:.1f} m)")

            if rgb is not None and not np.all(rgb == 0):
                self.combo_color.setCurrentIndex(0)
            else:
                self.combo_color.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(self, "3D Point Cloud Error", f"Could not load 3D points:\n{e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_color_mode_changed(self, idx: int):
        if 0 <= idx < len(COLOR_MODE_KEYS):
            self.canvas.set_color_mode(COLOR_MODE_KEYS[idx])

    def _on_budget_changed(self, idx: int):
        budgets = [6000000, 10000000, 0, 4000000, 2000000]
        if 0 <= idx < len(budgets):
            new_budget = budgets[idx]
            if new_budget != self.max_points:
                self.max_points = new_budget
                self._load_data()

    def _export_screenshot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save 3D Snapshot", "3d_point_cloud_view.png", "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if path:
            img = self.canvas.grabFramebuffer()
            img.save(path)
            QMessageBox.information(self, "Snapshot", f"Saved 3D screenshot to:\n{path}")


# Backwards compatibility alias
Viewer3DWindow = GeoStudio3DViewerWindow

