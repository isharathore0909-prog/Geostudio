# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Export Dialog & Engine
Provides high-resolution export for PDF, PNG, JPG, TIFF, SVG:
- DPI presets from 72 to 1200 DPI with custom DPI
- Calculated pixel dimensions & memory protection (>100 MP warnings)
- Vector vs rasterized PDF options
- Progress tracking with cancellation
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QComboBox,
    QSpinBox, QCheckBox, QPushButton, QLabel, QFileDialog,
    QMessageBox, QProgressBar, QApplication, QHBoxLayout
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor

from qgis.core import QgsLayoutExporter


class LayoutExportDialog(QDialog):
    """High-resolution export dialog for print layouts with DPI & memory calculations."""

    def __init__(self, layout, parent=None):
        super().__init__(parent)
        self.layout = layout
        self.setWindowTitle("Export Map Layout")
        self.resize(500, 420)
        self.setMinimumWidth(440)

        self._init_ui()
        self._update_calculations()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # ── Output Format Group ──────────────────────────────────
        grp_fmt = QGroupBox("Output Format & Resolution")
        form_fmt = QFormLayout(grp_fmt)
        form_fmt.setSpacing(8)

        self.combo_format = QComboBox()
        self.combo_format.addItems([
            "PDF Document (*.pdf) [Recommended for Print]",
            "PNG High-Res Image (*.png)",
            "JPEG Image (*.jpg)",
            "TIFF GeoTIFF/Image (*.tif)",
            "SVG Scalable Vector Graphics (*.svg)"
        ])
        self.combo_format.currentIndexChanged.connect(self._on_format_changed)
        form_fmt.addRow("Format:", self.combo_format)

        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems([
            "72 DPI (Web Draft)",
            "96 DPI (Standard Screen)",
            "150 DPI (Fast Print)",
            "300 DPI (High-Res Production Quality)",
            "600 DPI (Ultra Fine Cartographic)",
            "1200 DPI (Extreme Resolution)"
        ])
        self.combo_dpi.setCurrentIndex(3)  # Default 300 DPI
        self.combo_dpi.currentIndexChanged.connect(self._update_calculations)
        form_fmt.addRow("Resolution:", self.combo_dpi)

        self.lbl_dims = QLabel("--")
        self.lbl_dims.setStyleSheet("color: #0284c7; font-weight: bold; font-size: 11px;")
        form_fmt.addRow("Calculated Dimensions:", self.lbl_dims)

        layout.addWidget(grp_fmt)

        # ── Vector & PDF Options ─────────────────────────────────
        self.grp_pdf = QGroupBox("Vector & Rendering Options")
        form_pdf = QFormLayout(self.grp_pdf)
        form_pdf.setSpacing(8)

        self.chk_rasterize = QCheckBox("Rasterize entire map (Print as Image)")
        self.chk_rasterize.setToolTip("Enable if complex vector layers contain SVG markers or blending modes that cause PDF rendering artifacts")
        form_pdf.addRow(self.chk_rasterize)

        self.chk_open_after = QCheckBox("Open exported file after completion")
        self.chk_open_after.setChecked(True)
        form_pdf.addRow(self.chk_open_after)

        layout.addWidget(self.grp_pdf)

        # ── Progress Bar ─────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("Ready")
        self.progress.hide()
        layout.addWidget(self.progress)

        # ── Action Buttons ───────────────────────────────────────
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_box.addStretch()

        self.btn_export = QPushButton("Export Layout...")
        self.btn_export.setStyleSheet("background: #0f172a; color: #ffffff; font-weight: 600; padding: 7px 18px; border-radius: 4px;")
        self.btn_export.clicked.connect(self._do_export)
        btn_box.addWidget(self.btn_export)

        layout.addLayout(btn_box)

    def _get_dpi(self):
        dpis = [72, 96, 150, 300, 600, 1200]
        return dpis[self.combo_dpi.currentIndex()]

    def _update_calculations(self):
        dpi = self._get_dpi()
        page = self.layout.pageCollection().pages()[0]
        pw_mm = page.pageSize().width()
        ph_mm = page.pageSize().height()

        px_w = int(pw_mm / 25.4 * dpi)
        px_h = int(ph_mm / 25.4 * dpi)
        mp = (px_w * px_h) / 1_000_000

        self.lbl_dims.setText(f"{px_w:,} × {px_h:,} px  (~{mp:.1f} Megapixels @ {dpi} DPI)")

    def _on_format_changed(self):
        is_pdf = (self.combo_format.currentIndex() == 0)
        self.grp_pdf.setVisible(is_pdf)

    def _do_export(self):
        fmt_idx = self.combo_format.currentIndex()
        if fmt_idx == 0:
            filt, ext = "PDF Document (*.pdf)", ".pdf"
        elif fmt_idx == 1:
            filt, ext = "PNG Image (*.png)", ".png"
        elif fmt_idx == 2:
            filt, ext = "JPEG Image (*.jpg)", ".jpg"
        elif fmt_idx == 3:
            filt, ext = "TIFF Image (*.tif)", ".tif"
        else:
            filt, ext = "SVG File (*.svg)", ".svg"

        layout_name = self.layout.name() or "GeoStudio_Layout"
        path, _ = QFileDialog.getSaveFileName(self, "Export Layout", f"{layout_name}{ext}", filt)
        if not path:
            return

        # Large Export Memory Warning
        dpi = self._get_dpi()
        page = self.layout.pageCollection().pages()[0]
        px_w = int(page.pageSize().width() / 25.4 * dpi)
        px_h = int(page.pageSize().height() / 25.4 * dpi)
        mp = (px_w * px_h) / 1_000_000

        if mp > 100.0:
            resp = QMessageBox.warning(
                self, "Large Export Memory Warning",
                f"This export will produce {px_w:,} × {px_h:,} pixels (~{mp:.1f} Megapixels).\n"
                f"Rendering at this size requires substantial RAM.\n\nDo you want to continue?",
                QMessageBox.Yes | QMessageBox.Cancel
            )
            if resp != QMessageBox.Yes:
                return

        self.progress.show()
        self.progress.setValue(20)
        self.progress.setFormat("Rendering layout layers...")
        self.btn_export.setEnabled(False)
        QApplication.processEvents()

        exporter = QgsLayoutExporter(self.layout)

        try:
            if ext == ".pdf":
                pdf_settings = QgsLayoutExporter.PdfExportSettings()
                pdf_settings.dpi = dpi
                pdf_settings.rasterizeWholeImage = self.chk_rasterize.isChecked()
                self.progress.setValue(60)
                res = exporter.exportToPdf(path, pdf_settings)
            elif ext == ".svg":
                svg_settings = QgsLayoutExporter.SvgExportSettings()
                svg_settings.dpi = dpi
                self.progress.setValue(60)
                res = exporter.exportToSvg(path, svg_settings)
            else:
                img_settings = QgsLayoutExporter.ImageExportSettings()
                img_settings.dpi = dpi
                self.progress.setValue(60)
                res = exporter.exportToImage(path, img_settings)

            if res == QgsLayoutExporter.Success:
                self.progress.setValue(100)
                self.progress.setFormat("Export Complete!")
                QMessageBox.information(self, "Export Success", f"Map layout successfully exported to:\n{path}")
                if self.chk_open_after.isChecked() and os.path.exists(path):
                    os.startfile(path)
                self.accept()
            else:
                self.progress.hide()
                self.btn_export.setEnabled(True)
                QMessageBox.critical(self, "Export Error", f"Layout exporter failed with status code: {res}")
        except Exception as e:
            self.progress.hide()
            self.btn_export.setEnabled(True)
            QMessageBox.critical(self, "Export Failed", f"An error occurred while exporting layout:\n{e}")
