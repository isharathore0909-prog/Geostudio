# -*- coding: utf-8 -*-
"""
GeoStudio - Layer Swipe Compare Dialog
Allows users to compare two layers side-by-side (Vertical/Horizontal) or via a Spyglass,
matching ArcGIS Web AppBuilder and ArcGIS Pro Swipe Tool capabilities.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLabel, QPushButton, QButtonGroup, QRadioButton,
    QGroupBox, QWidget, QSlider
)
from PyQt5.QtCore import Qt

from resources.icons.icon_provider import get_icon

DIALOG_STYLE = """
QDialog {
    background: #ffffff;
    color: #0f172a;
    font-family: "Segoe UI Variable Display", "Segoe UI", "Inter", sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 8px;
    font-weight: 600;
    padding: 10px 8px 8px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    color: #334155;
}
QComboBox {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 4px 8px;
    min-width: 220px;
}
QPushButton {
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover { background: #1d4ed8; }
QPushButton:pressed { background: #1e40af; }
QPushButton#secondaryBtn {
    background: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
}
QPushButton#secondaryBtn:hover { background: #e2e8f0; }
QPushButton#swapBtn {
    background: #f1f5f9;
    color: #2563eb;
    border: 1px solid #cbd5e1;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#swapBtn:hover { background: #dbeafe; border-color: #3b82f6; }
QRadioButton { spacing: 6px; }
QRadioButton::indicator { width: 16px; height: 16px; }
"""


class SwipeCompareDialog(QDialog):
    """Dialog to configure and launch the Swipe Compare overlay."""

    def __init__(self, map_canvas, parent=None):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self._swipe_overlay = None

        if hasattr(map_canvas, "canvas") and map_canvas.canvas:
            self._canvas = map_canvas.canvas
        else:
            self._canvas = map_canvas

        self.setWindowTitle("Layer Swipe Compare")
        self.setWindowIcon(get_icon("swipe"))
        self.setMinimumWidth(440)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()
        self.swipe_layer_combo = self.layer_a_combo
        self._populate_layers()

        # Connect signals for real-time reactivity
        self.layer_a_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.layer_b_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.rb_vertical.toggled.connect(self._on_setting_changed)
        self.rb_horizontal.toggled.connect(self._on_setting_changed)
        self.rb_spyglass.toggled.connect(self._on_setting_changed)

        # Auto-activate immediately when dialog is opened
        self._on_activate()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # --- Instructions ---
        info = QLabel(
            "Interactively compare two layers by dragging the divider bar or moving the circular spyglass. "
            "Layer A is revealed on the left / inside lens; Layer B is displayed on the right / base."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; font-size: 11px; padding: 2px 0;")
        layout.addWidget(info)

        # --- Layer selection ---
        layer_group = QGroupBox("Layer Selection")
        layer_layout = QVBoxLayout(layer_group)
        layer_layout.setSpacing(6)

        form = QFormLayout()
        form.setSpacing(6)

        self.layer_a_combo = QComboBox()
        self.layer_a_combo.setToolTip("Primary layer (peeled back on the left / top / inside spyglass)")
        form.addRow("Layer A (Swipe / Lens):", self.layer_a_combo)

        self.layer_b_combo = QComboBox()
        self.layer_b_combo.setToolTip("Base comparison layer (revealed on the right / bottom / base)")
        form.addRow("Layer B (Compare With):", self.layer_b_combo)

        layer_layout.addLayout(form)

        swap_row = QHBoxLayout()
        swap_row.addStretch()
        self.btn_swap = QPushButton("⇄ Swap Layers (A ↔ B)")
        self.btn_swap.setObjectName("swapBtn")
        self.btn_swap.setToolTip("Swap Layer A and Layer B")
        self.btn_swap.clicked.connect(self._on_swap_layers)
        swap_row.addWidget(self.btn_swap)
        layer_layout.addLayout(swap_row)

        layout.addWidget(layer_group)

        # --- Mode selection ---
        mode_group = QGroupBox("Swipe Mode")
        mode_layout = QHBoxLayout(mode_group)

        self._mode_group = QButtonGroup(self)
        self.rb_vertical   = QRadioButton("⇔  Vertical Bar")
        self.rb_horizontal = QRadioButton("⇕  Horizontal Bar")
        self.rb_spyglass   = QRadioButton("🔍 Spyglass")
        self.rb_vertical.setChecked(True)

        for rb in (self.rb_vertical, self.rb_horizontal, self.rb_spyglass):
            self._mode_group.addButton(rb)
            mode_layout.addWidget(rb)

        layout.addWidget(mode_group)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        self.btn_activate = QPushButton("⚡ Refresh Swipe")
        self.btn_activate.clicked.connect(self._on_activate)

        btn_close = QPushButton("✕ Close & Deactivate")
        btn_close.setObjectName("secondaryBtn")
        btn_close.clicked.connect(self._on_close)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_activate)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Data & Populate
    # ------------------------------------------------------------------

    def _populate_layers(self):
        self.layer_a_combo.blockSignals(True)
        self.layer_b_combo.blockSignals(True)
        self.layer_a_combo.clear()
        self.layer_b_combo.clear()

        try:
            from qgis.core import QgsProject
            layers = list(QgsProject.instance().mapLayers().values())

            # Add all layers to Layer A combo
            for layer in reversed(layers):
                if layer.isValid():
                    self.layer_a_combo.addItem(layer.name(), layer.id())

            # Add all layers to Layer B combo + "All Other Visible Layers"
            self.layer_b_combo.addItem("(All Other Visible Layers)", None)
            for layer in reversed(layers):
                if layer.isValid():
                    self.layer_b_combo.addItem(layer.name(), layer.id())

            # By default, if at least 2 layers exist, select layer 0 for A and layer 1 for B
            if len(layers) >= 2:
                self.layer_a_combo.setCurrentIndex(0)
                # In layer_b_combo, index 0 is "(All Other Visible Layers)", index 2 is the 2nd layer
                self.layer_b_combo.setCurrentIndex(2)
            elif len(layers) == 1:
                self.layer_a_combo.setCurrentIndex(0)
                self.layer_b_combo.setCurrentIndex(0)

        except Exception as e:
            self.layer_a_combo.addItem("(No layers available)", None)
            self.layer_b_combo.addItem("(No layers available)", None)

        self.layer_a_combo.blockSignals(False)
        self.layer_b_combo.blockSignals(False)

    def _get_layer_a(self):
        try:
            from qgis.core import QgsProject
            lid = self.layer_a_combo.currentData()
            if lid:
                return QgsProject.instance().mapLayer(lid)
        except Exception:
            pass
        return None

    def _get_layer_b(self):
        try:
            from qgis.core import QgsProject
            lid = self.layer_b_combo.currentData()
            if lid:
                return QgsProject.instance().mapLayer(lid)
        except Exception:
            pass
        return None

    def _current_mode(self) -> str:
        if self.rb_horizontal.isChecked():
            return "horizontal"
        if self.rb_spyglass.isChecked():
            return "spyglass"
        return "vertical"

    # ------------------------------------------------------------------
    # Actions & Reactivity
    # ------------------------------------------------------------------

    def _on_swap_layers(self):
        """Swap selected Layer A and Layer B."""
        idx_a = self.layer_a_combo.currentIndex()
        text_a = self.layer_a_combo.currentText()
        text_b = self.layer_b_combo.currentText()

        # Find text_a in layer_b_combo
        idx_b_for_a = self.layer_b_combo.findText(text_a)
        # Find text_b in layer_a_combo
        idx_a_for_b = self.layer_a_combo.findText(text_b)

        self.layer_a_combo.blockSignals(True)
        self.layer_b_combo.blockSignals(True)

        if idx_a_for_b >= 0:
            self.layer_a_combo.setCurrentIndex(idx_a_for_b)
        if idx_b_for_a >= 0:
            self.layer_b_combo.setCurrentIndex(idx_b_for_a)

        self.layer_a_combo.blockSignals(False)
        self.layer_b_combo.blockSignals(False)

        self._on_setting_changed()

    def _on_setting_changed(self):
        """Immediately update the active swipe overlay when settings change."""
        if not self._swipe_overlay:
            self._on_activate()
            return

        layer_a = self._get_layer_a()
        layer_b = self._get_layer_b()
        mode    = self._current_mode()

        self._swipe_overlay.set_mode(mode)
        self._swipe_overlay.set_layers(layer_a, layer_b)

    def _on_activate(self):
        """Create or update the swipe overlay on the map canvas."""
        canvas = self._canvas
        if not canvas:
            return

        layer_a = self._get_layer_a()
        layer_b = self._get_layer_b()
        mode    = self._current_mode()

        if self._swipe_overlay:
            self._swipe_overlay.set_mode(mode)
            self._swipe_overlay.set_layers(layer_a, layer_b)
            self._swipe_overlay.show()
            self._swipe_overlay.raise_()
            return

        from tools.swipe_tool import SwipeOverlay
        self._swipe_overlay = SwipeOverlay(
            canvas, layer_a=layer_a, layer_b=layer_b, mode=mode, parent=canvas
        )
        self._swipe_overlay.setGeometry(0, 0, canvas.width(), canvas.height())
        self._swipe_overlay.show()
        self._swipe_overlay.raise_()

        if self.map_canvas:
            self.map_canvas._swipe_overlay = self._swipe_overlay

    def _on_close(self):
        """Deactivate swipe and close."""
        if self._swipe_overlay:
            self._swipe_overlay.deactivate()
            self._swipe_overlay.deleteLater()
            self._swipe_overlay = None
        if self.map_canvas:
            self.map_canvas._swipe_overlay = None
        self.reject()

    def closeEvent(self, event):
        # Keep the overlay alive when dialog is minimized/closed if user is comparing
        event.accept()
