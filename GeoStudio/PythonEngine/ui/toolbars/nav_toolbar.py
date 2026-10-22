# -*- coding: utf-8 -*-
"""
GeoStudio - Navigation Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import (
    QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QToolButton, QMenu, QAction
)
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class NavToolBar(QToolBar):
    """Map navigation toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Navigation", parent or main_window)
        self.setObjectName("tb_nav")
        self.mw = main_window
        self._build_ui()

    def _build_ui(self):
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 1)
        layout.setSpacing(1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(2)

        nav_items = [
            ("pan",       "Pan Map",      self.mw.set_pan_tool,    "Pan Map (P)",                    "P"),
            ("zoom_in",   "Zoom In",      self.mw.set_zoom_in,     "Zoom In (+)",                    "+"),
            ("zoom_out",  "Zoom Out",     self.mw.set_zoom_out,    "Zoom Out (-)",                   "-"),
            ("zoom_full", "Zoom Full",    self.mw.zoom_full,       "Zoom to Full Extent (Ctrl+Shift+F)", "Ctrl+Shift+F"),
            ("refresh",   "Refresh",      self.mw.refresh_canvas,  "Refresh Map Canvas (F5)",        "F5"),
        ]
        for icon_key, text, slot, tip, shortcut in nav_items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            if shortcut:
                btn.setShortcut(shortcut)
            btn_row.addWidget(btn)

        # ── Swipe Compare button ──────────────────────────────────
        btn_swipe = QToolButton(container)
        btn_swipe.setIcon(get_icon("swipe"))
        btn_swipe.setIconSize(QSize(20, 20))
        btn_swipe.setToolTip("Layer Swipe Compare (Ctrl+Shift+W)\nCompare two layers interactively side-by-side or with a spyglass")
        btn_swipe.setStatusTip("Layer Swipe Compare — drag a divider bar or spyglass to compare layers")
        btn_swipe.clicked.connect(self.mw.open_swipe_compare)
        btn_row.addWidget(btn_swipe)

        # ── Blend Mode quick-access dropdown ──────────────────────
        btn_blend = QToolButton(container)
        btn_blend.setIcon(get_icon("blend_mode"))
        btn_blend.setIconSize(QSize(20, 20))
        btn_blend.setToolTip("Layer Blend Mode\nApply a compositing blend mode (Multiply, Screen, Overlay...) to the active raster layer")
        btn_blend.setStatusTip("Layer Blend Mode — compositing and blending for raster layers")
        btn_blend.setPopupMode(QToolButton.InstantPopup)
        btn_blend.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        blend_menu = QMenu(container)
        blend_menu.setStyleSheet(
            "QMenu { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; "
            "font-size: 11px; padding: 4px; }"
            "QMenu::item { padding: 4px 18px; border-radius: 3px; }"
            "QMenu::item:selected { background: #dbeafe; color: #1e40af; }"
            "QMenu::item:disabled { color: #94a3b8; }"
            "QMenu::separator { height: 1px; background: #e2e8f0; margin: 3px 6px; }"
        )
        QUICK_MODES = [
            ("─ Darken ─",    None),
            ("Normal",        "Normal"),
            ("Multiply  ★",   "Multiply"),
            ("Darken",        "Darken"),
            ("Color Burn",    "Color Burn"),
            ("─ Lighten ─",   None),
            ("Screen  ★",     "Screen"),
            ("Lighten",       "Lighten"),
            ("Color Dodge",   "Color Dodge"),
            ("─ Contrast ─",  None),
            ("Overlay",       "Overlay"),
            ("Hard Light",    "Hard Light"),
            ("Soft Light",    "Soft Light"),
            ("─ Compare ─",   None),
            ("Difference",    "Difference"),
            ("Exclusion",     "Exclusion"),
        ]
        for label, mode in QUICK_MODES:
            if mode is None:
                act = blend_menu.addAction(label)
                act.setEnabled(False)
            else:
                act = blend_menu.addAction(label)
                act.triggered.connect(
                    lambda checked=False, m=mode: self.mw.apply_layer_blend_mode(m)
                )
        btn_blend.setMenu(blend_menu)
        btn_row.addWidget(btn_blend)

        layout.addLayout(btn_row)

        lbl = QLabel("NAVIGATION", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color: #64748b; font-size: 9px; font-weight: 700; "
            "letter-spacing: 0.5px; padding-top: 1px;"
        )
        layout.addWidget(lbl)

        self.addWidget(container)

