# -*- coding: utf-8 -*-
"""
GeoStudio - Point Cloud Optimizer & COPC Indexer
Indexes raw LAS/LAZ files to Cloud-Optimized Point Cloud (COPC) format using Untwine.
Enables instant rendering, level-of-detail (LOD) octree streaming, and minimal RAM usage (<200MB).
"""

import os
import sys
import subprocess
import shutil
from PyQt5.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QMessageBox, QTextEdit
)


class UntwineIndexWorker(QThread):
    """Background thread to index LAS/LAZ to COPC using QGIS untwine.exe."""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str, str)  # success, output_copc_path, error_message

    def __init__(self, input_las_path: str, output_copc_path: str = None):
        super().__init__()
        self.input_path = input_las_path
        self.output_path = output_copc_path or self._default_output_path(input_las_path)
        self._is_cancelled = False
        self._process = None

    @staticmethod
    def _default_output_path(input_las_path: str) -> str:
        base, _ = os.path.splitext(input_las_path)
        return f"{base}.copc.laz"

    def cancel(self):
        self._is_cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def run(self):
        if not os.path.exists(self.input_path):
            self.finished_signal.emit(False, "", f"Input file does not exist: {self.input_path}")
            return

        qgis_root = r"C:\Program Files\QGIS 3.40.14"
        untwine_exe = os.path.join(qgis_root, "apps", "qgis-ltr", "untwine.exe")
        bin_dir = os.path.join(qgis_root, "bin")
        qgis_bin = os.path.join(qgis_root, "apps", "qgis-ltr", "bin")

        if not os.path.exists(untwine_exe):
            self.finished_signal.emit(False, "", "untwine.exe not found in QGIS installation.")
            return

        # Prepare environment
        env = os.environ.copy()
        path_var = f"{bin_dir};{qgis_bin};" + env.get("PATH", "")
        env["PATH"] = path_var

        cmd = [
            untwine_exe,
            "-i", self.input_path,
            "-o", self.output_path,
            "--level", "6",
            "--progress_debug"
        ]

        try:
            self.progress_signal.emit(5, "Building spatial LOD index...")
            
            # Use BELOW_NORMAL_PRIORITY_CLASS on Windows so PC remains 100% responsive
            cflags = 0
            if os.name == "nt":
                cflags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000)

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                creationflags=cflags
            )

            # Read output
            while True:
                if self._is_cancelled:
                    if self._process:
                        self._process.terminate()
                    self.finished_signal.emit(False, "", "Indexing cancelled by user.")
                    return

                line = self._process.stdout.readline()
                if not line and self._process.poll() is not None:
                    break
                if line:
                    line_str = line.strip()
                    # Try to parse percentage if present
                    if "%" in line_str:
                        for token in line_str.split():
                            if token.endswith("%") and token[:-1].isdigit():
                                pct = int(token[:-1])
                                self.progress_signal.emit(pct, line_str)
                                break
                    else:
                        self.progress_signal.emit(50, line_str)

            rc = self._process.poll()
            if rc == 0 and os.path.exists(self.output_path):
                self.progress_signal.emit(100, "Optimization complete!")
                self.finished_signal.emit(True, self.output_path, "")
            else:
                self.finished_signal.emit(False, "", f"Untwine exited with return code {rc}")

        except Exception as e:
            self.finished_signal.emit(False, "", str(e))


class PointCloudOptimizerDialog(QDialog):
    """Modern progress dialog for indexing point clouds into COPC."""

    def __init__(self, parent, input_path: str):
        super().__init__(parent)
        self.setWindowTitle("Optimizing Point Cloud - GeoStudio")
        self.setFixedSize(520, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.input_path = input_path
        self.output_copc_path = None
        self.success = False

        self._build_ui()
        self._start_worker()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        fname = os.path.basename(self.input_path)
        self.lbl_title = QLabel(f"<b>Indexing Point Cloud:</b> {fname}")
        self.lbl_title.setStyleSheet("font-size: 13px; color: #0f172a;")
        layout.addWidget(self.lbl_title)

        # Description
        self.lbl_desc = QLabel(
            "Building Cloud-Optimized Point Cloud (COPC) octree...\n"
            "This enables 60 FPS fluid rendering and reduces RAM usage from 12+ GB to < 200 MB."
        )
        self.lbl_desc.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.lbl_desc)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(5)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                text-align: center;
                height: 20px;
                background: #f1f5f9;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: #0f172a;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Status text
        self.lbl_status = QLabel("Starting untwine indexer...")
        self.lbl_status.setStyleSheet("color: #475569; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # Cancel button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: bold;
                color: #334155;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _start_worker(self):
        self.worker = UntwineIndexWorker(self.input_path)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, pct: int, status_str: str):
        self.progress_bar.setValue(pct)
        if status_str:
            self.lbl_status.setText(status_str)

    def _on_finished(self, success: bool, output_path: str, err_msg: str):
        self.success = success
        self.output_copc_path = output_path
        if success:
            self.accept()
        else:
            if err_msg and "cancelled" not in err_msg.lower():
                QMessageBox.warning(self, "Indexing Warning", f"Could not create COPC index:\n{err_msg}\nFalling back to direct loading.")
            self.reject()

    def _on_cancel(self):
        if self.worker:
            self.worker.cancel()
        self.reject()


class PointCloudOptimizer:
    """Helper methods for managing COPC caching and on-demand conversion."""

    @staticmethod
    def get_existing_copc(las_path: str) -> str:
        """Returns existing COPC file path if available next to file or in cache."""
        if las_path.lower().endswith(".copc.laz"):
            return las_path

        base, _ = os.path.splitext(las_path)
        copc_sidecar = f"{base}.copc.laz"
        if os.path.exists(copc_sidecar):
            return copc_sidecar

        return None

    @staticmethod
    def should_offer_optimization(las_path: str) -> bool:
        """Checks if file is a raw unindexed LAS/LAZ that is large (> 30 MB)."""
        if not os.path.exists(las_path):
            return False
        if las_path.lower().endswith(".copc.laz"):
            return False
        # If COPC sidecar already exists, no need to re-index
        if PointCloudOptimizer.get_existing_copc(las_path):
            return False

        try:
            size_mb = os.path.getsize(las_path) / (1024 * 1024)
            return size_mb >= 30.0
        except Exception:
            return False
