# -*- coding: utf-8 -*-
"""
GeoStudio - Print & Export Map Layout Dialog
Provides high-resolution map image and PDF export with custom DPI,
title, scale bar, and north arrow overlays.
"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QProgressBar, QApplication
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPainter, QColor, QPen

from qgis.core import (
    QgsProject, QgsMapSettings, QgsMapRendererCustomPainterJob
)
from app.ui.canvas.print_export_overlays import (
    draw_title_overlay,
    draw_north_arrow_overlay,
    draw_scalebar_overlay
)


class PrintExportDialog(QDialog):
    """High-resolution map export and print dialog."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.mw = main_window
        self.setWindowTitle("Print & Export Map Layout")
        self.resize(560, 480)
        self.setMinimumWidth(480)

        self._init_ui()
        self._update_dimensions_info()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Output Settings
        grp_output = QGroupBox("Output Settings")
        form_output = QFormLayout(grp_output)
        form_output.setSpacing(8)

        self.combo_format = QComboBox()
        self.combo_format.addItems(["PNG High-Res Image (*.png)", "JPEG Image (*.jpg)", "PDF Document (*.pdf)"])
        form_output.addRow("Format:", self.combo_format)

        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "Current Map View (Exact Aspect)",
            "A4 Landscape (297 × 210 mm)",
            "A4 Portrait (210 × 297 mm)",
            "A3 Landscape (420 × 297 mm)",
            "Full HD (1920 × 1080 px)",
            "4K Ultra HD (3840 × 2160 px)",
        ])
        self.combo_preset.currentIndexChanged.connect(self._update_dimensions_info)
        form_output.addRow("Page Preset:", self.combo_preset)

        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["96 DPI (Screen / Fast)", "150 DPI (Draft Print)", "300 DPI (High-Res Production)", "600 DPI (Ultra-Fine)"])
        self.combo_dpi.setCurrentIndex(2)
        self.combo_dpi.currentIndexChanged.connect(self._update_dimensions_info)
        form_output.addRow("Resolution (DPI):", self.combo_dpi)

        self.lbl_dims = QLabel("Output Dimensions: --")
        self.lbl_dims.setStyleSheet("color: #0284c7; font-weight: bold; font-size: 11px;")
        form_output.addRow("Calculated Size:", self.lbl_dims)

        layout.addWidget(grp_output)

        # Map Elements & Overlays
        grp_decor = QGroupBox("Map Elements & Overlays")
        form_decor = QFormLayout(grp_decor)
        form_decor.setSpacing(8)

        self.chk_title = QCheckBox("Include Map Title")
        self.chk_title.setChecked(True)
        self.txt_title = QLineEdit(f"{self.mw.APP_NAME} Map Layout")
        self.chk_title.toggled.connect(self.txt_title.setEnabled)
        form_decor.addRow(self.chk_title, self.txt_title)

        self.chk_scalebar = QCheckBox("Include Scale Bar")
        self.chk_scalebar.setChecked(True)
        form_decor.addRow(self.chk_scalebar)

        self.chk_north_arrow = QCheckBox("Include North Arrow")
        self.chk_north_arrow.setChecked(True)
        form_decor.addRow(self.chk_north_arrow)

        self.chk_border = QCheckBox("Draw Map Border & Coordinate Frame")
        self.chk_border.setChecked(True)
        form_decor.addRow(self.chk_border)

        layout.addWidget(grp_decor)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        btn_box.addStretch()

        btn_export = QPushButton("🚀 Export & Save Map")
        btn_export.setStyleSheet("background: #0284c7; color: white; font-weight: bold; padding: 7px 16px; border-radius: 4px;")
        btn_export.clicked.connect(self._do_export)
        btn_box.addWidget(btn_export)

        layout.addLayout(btn_box)

    def _get_dpi(self):
        idx = self.combo_dpi.currentIndex()
        return [96, 150, 300, 600][idx]

    def _get_target_pixel_size(self):
        dpi = self._get_dpi()
        preset = self.combo_preset.currentText()

        if "A4 Landscape" in preset:
            w_in, h_in = 297 / 25.4, 210 / 25.4
            return int(w_in * dpi), int(h_in * dpi)
        elif "A4 Portrait" in preset:
            w_in, h_in = 210 / 25.4, 297 / 25.4
            return int(w_in * dpi), int(h_in * dpi)
        elif "A3 Landscape" in preset:
            w_in, h_in = 420 / 25.4, 297 / 25.4
            return int(w_in * dpi), int(h_in * dpi)
        elif "Full HD" in preset:
            return 1920, 1080
        elif "4K Ultra HD" in preset:
            return 3840, 2160
        else:
            canvas = self.mw.map_canvas.canvas
            base_w = canvas.width() if canvas else 1200
            base_h = canvas.height() if canvas else 800
            scale = dpi / 96.0
            return int(base_w * scale), int(base_h * scale)

    def _update_dimensions_info(self):
        w, h = self._get_target_pixel_size()
        dpi = self._get_dpi()
        mp = (w * h) / 1_000_000
        self.lbl_dims.setText(f"{w} × {h} px  (~{mp:.1f} Megapixels @ {dpi} DPI)")

    def _do_export(self):
        fmt_idx = self.combo_format.currentIndex()
        if fmt_idx == 0:
            filt, ext = "PNG Image (*.png)", ".png"
        elif fmt_idx == 1:
            filt, ext = "JPEG Image (*.jpg)", ".jpg"
        else:
            filt, ext = "PDF Document (*.pdf)", ".pdf"

        path, _ = QFileDialog.getSaveFileName(self, "Export Map Layout", f"GeoStudio_Map{ext}", filt)
        if not path:
            return

        self.progress.show()
        self.progress.setRange(0, 0)
        QApplication.processEvents()

        try:
            w, h = self._get_target_pixel_size()
            dpi = self._get_dpi()

            canvas = self.mw.map_canvas.canvas
            dest_crs = canvas.mapSettings().destinationCrs()
            extent = canvas.extent()
            layers = [l for l in QgsProject.instance().mapLayers().values() if l.isValid()]

            settings = QgsMapSettings()
            settings.setLayers(layers)
            settings.setDestinationCrs(dest_crs)
            settings.setExtent(extent)
            settings.setOutputSize(QSize(w, h))
            settings.setOutputDpi(dpi)
            settings.setBackgroundColor(QColor("#ffffff"))

            image = QImage(QSize(w, h), QImage.Format_ARGB32_Premultiplied)
            image.fill(QColor("#ffffff"))

            p = QPainter(image)
            p.setRenderHint(QPainter.Antialiasing)

            job = QgsMapRendererCustomPainterJob(settings, p)
            job.start()
            job.waitForFinished()

            if self.chk_title.isChecked() and self.txt_title.text().strip():
                draw_title_overlay(p, w, h, self.txt_title.text().strip())

            if self.chk_north_arrow.isChecked():
                draw_north_arrow_overlay(p, w, h)

            if self.chk_scalebar.isChecked():
                draw_scalebar_overlay(p, w, h, extent, dest_crs)

            if self.chk_border.isChecked():
                p.setPen(QPen(QColor("#0f172a"), max(2, int(w / 1000))))
                p.setBrush(Qt.NoBrush)
                p.drawRect(0, 0, w - 1, h - 1)

            p.end()

            if ext == ".pdf":
                from PyQt5.QtGui import QPdfWriter
                from PyQt5.QtCore import QSizeF
                writer = QPdfWriter(path)
                writer.setResolution(dpi)
                writer.setPageSizeMM(QSizeF(w * 25.4 / dpi, h * 25.4 / dpi))
                pdf_p = QPainter(writer)
                pdf_p.drawImage(0, 0, image)
                pdf_p.end()
            else:
                image.save(path)

            self.progress.hide()
            self.mw.geo_status.showMessage(f"Map successfully exported to {os.path.basename(path)}", 5000)

            reply = QMessageBox.information(
                self, "Export Complete",
                f"Map layout successfully exported to:\n{path}\n\nWould you like to open the exported file?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                os.startfile(path)
            self.accept()

        except Exception as e:
            self.progress.hide()
            QMessageBox.critical(self, "Export Failed", f"An error occurred while exporting map:\n{e}")
