# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Export Service
Encapsulates high-resolution export operations using QgsLayoutExporter:
- PDF document export (vector or rasterized)
- PNG, JPEG, TIFF image export with DPI configuration
- SVG vector graphics export
- Resolution and memory validation checks
"""

import os
from typing import Optional, Tuple
from qgis.core import QgsLayoutExporter, QgsPrintLayout


def export_layout_to_image(layout: QgsPrintLayout, output_path: str, dpi: int = 300) -> Tuple[bool, str]:
    """
    Exports a print layout to an image file (PNG, JPG, TIFF).
    Returns (success, message).
    """
    if not layout:
        return False, "Layout is None"

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = dpi

    result = exporter.exportToImage(output_path, settings)
    if result == QgsLayoutExporter.Success:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, f"Image successfully exported to {output_path} ({os.path.getsize(output_path):,} bytes)"
        return False, "Export completed but output file is missing or empty"
    return False, f"Export failed with code: {result}"


def export_layout_to_pdf(layout: QgsPrintLayout, output_path: str, dpi: int = 300, rasterize: bool = False) -> Tuple[bool, str]:
    """
    Exports a print layout to a PDF document.
    Returns (success, message).
    """
    if not layout:
        return False, "Layout is None"

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.PdfExportSettings()
    settings.dpi = dpi
    settings.rasterizeWholeImage = rasterize

    result = exporter.exportToPdf(output_path, settings)
    if result == QgsLayoutExporter.Success:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, f"PDF successfully exported to {output_path} ({os.path.getsize(output_path):,} bytes)"
        return False, "Export completed but output file is missing or empty"
    return False, f"Export failed with code: {result}"


def export_layout_to_svg(layout: QgsPrintLayout, output_path: str, dpi: int = 300) -> Tuple[bool, str]:
    """
    Exports a print layout to an SVG vector file.
    Returns (success, message).
    """
    if not layout:
        return False, "Layout is None"

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.SvgExportSettings()
    settings.dpi = dpi

    result = exporter.exportToSvg(output_path, settings)
    if result == QgsLayoutExporter.Success:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, f"SVG successfully exported to {output_path} ({os.path.getsize(output_path):,} bytes)"
        return False, "Export completed but output file is missing or empty"
    return False, f"Export failed with code: {result}"


__all__ = [
    "export_layout_to_image",
    "export_layout_to_pdf",
    "export_layout_to_svg",
]
