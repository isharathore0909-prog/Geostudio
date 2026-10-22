# -*- coding: utf-8 -*-
"""
GeoStudio - DEM Elevation Dialog UI Components & Previews
Preview widgets and stylesheet definitions for DEM symbology.
"""

from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QColor, QPainter, QBrush, QLinearGradient
from core.elevation_styler import ELEVATION_PRESETS

DIALOG_STYLE = """
    QDialog { background: #f8fafc; color: #1e293b; font-size: 12px; }
    QGroupBox { font-weight: bold; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 6px; margin-top: 16px; padding-top: 6px; background: #ffffff; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 8px; padding: 0 4px; background: #ffffff; color: #0f172a; }
    QTabWidget::pane { border: 1px solid #cbd5e1; background: #ffffff; border-radius: 6px; top: -1px; }
    QTabWidget::tab-bar { left: 6px; }
    QTabBar::tab { background: #f1f5f9; color: #64748b; padding: 7px 18px; border: 1px solid #cbd5e1; border-top-left-radius: 5px; border-top-right-radius: 5px; margin-right: 4px; margin-top: 2px; min-width: 68px; }
    QTabBar::tab:selected { background: #ffffff; color: #0f172a; font-weight: bold; border-bottom: 1px solid #ffffff; margin-top: 0px; }
    QTabBar::tab:hover:!selected { background: #e2e8f0; color: #1e293b; }
    QPushButton { background: #0f172a; color: white; border: none; border-radius: 4px; padding: 7px 16px; font-weight: bold; }
    QPushButton:hover { background: #1e293b; }
    QPushButton:pressed { background: #334155; }
    QPushButton#secondaryBtn { background: #e2e8f0; color: #334155; font-weight: normal; border: 1px solid #cbd5e1; }
    QPushButton#secondaryBtn:hover { background: #cbd5e1; }
    QComboBox, QDoubleSpinBox { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 6px; }
    QLabel { color: #334155; }
    QCheckBox { color: #334155; spacing: 5px; }
    QSlider::groove:horizontal { border: 1px solid #cbd5e1; height: 6px; background: #f1f5f9; border-radius: 3px; }
    QSlider::sub-page:horizontal { background: #0f172a; border-radius: 3px; }
    QSlider::handle:horizontal { background: #0f172a; border: 1px solid #000000; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
    QSlider::handle:horizontal:hover { background: #334155; }
"""


class ColorRampPreviewWidget(QFrame):
    """Draws a smooth graphical preview of the selected elevation color ramp."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.preset_key = "GLOBAL_MAPPER_ATLAS"
        self.invert = False
        self.setFixedHeight(24)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 4px;")

    def set_preset(self, preset_key: str, invert: bool = False):
        self.preset_key = preset_key
        self.invert = invert
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        preset = ELEVATION_PRESETS.get(self.preset_key, ELEVATION_PRESETS["GLOBAL_MAPPER_ATLAS"])
        stops = preset["stops"]
        if self.invert:
            stops = list(reversed(stops))

        gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        for stop_frac, hex_color, _ in stops:
            gradient.setColorAt(stop_frac, QColor(hex_color))

        painter.fillRect(rect, QBrush(gradient))
        painter.end()
