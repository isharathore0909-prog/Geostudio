# -*- coding: utf-8 -*-
"""
GeoStudio - Terrain & Elevation Toolbar (Grouped with Title)
"""

from PyQt5.QtWidgets import QToolBar, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QMenu
from PyQt5.QtCore import Qt, QSize

from resources.icons.icon_provider import get_icon


class TerrainToolBar(QToolBar):
    """Terrain & Elevation Toolbar with group label."""

    def __init__(self, main_window, parent=None):
        super().__init__("Terrain", parent or main_window)
        self.setObjectName("tb_terrain")
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

        # ── 1. Shader Dropdown Button ──────────────────────
        btn_shader = QToolButton(container)
        btn_shader.setIcon(get_icon("shader"))
        btn_shader.setText(" Shader ▾")
        btn_shader.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn_shader.setPopupMode(QToolButton.InstantPopup)
        btn_shader.setToolTip("Instant Terrain Visualization Shaders")

        shader_menu = QMenu(btn_shader)
        shader_menu.addAction(get_icon("elevation"), "Atlas (Global Mapper Pro)", lambda: self.mw.apply_shader_preset("GLOBAL_MAPPER_ATLAS"))
        shader_menu.addAction(get_icon("elevation"), "Elevation Terrain (Earth Tones)", lambda: self.mw.apply_shader_preset("GLOBAL_MAPPER_TERRAIN"))
        shader_menu.addAction(get_icon("slope"), "Slope Map Preview", self.mw.open_slope_dialog)
        shader_menu.addAction(get_icon("aspect"), "Aspect Map Preview", self.mw.open_aspect_dialog)
        shader_menu.addAction(get_icon("hillshade"), "Hillshade Preview", self.mw.open_hillshade_dialog)
        shader_menu.addSeparator()
        shader_menu.addAction(get_icon("elevation"), "TRI (Ruggedness Index)", self.mw.open_tri_dialog)
        shader_menu.addAction(get_icon("elevation"), "TPI (Position Index)", self.mw.open_tpi_dialog)
        shader_menu.addAction(get_icon("watershed"), "TWI (Wetness Index)", self.mw.open_twi_dialog)
        shader_menu.addAction(get_icon("profile"), "Curvature Analysis", self.mw.open_curvature_dialog)
        shader_menu.addSeparator()
        shader_menu.addAction(get_icon("elevation"), "Open Full Terrain Styler...", self.mw.open_dem_elevation_dialog)
        btn_shader.setMenu(shader_menu)
        btn_row.addWidget(btn_shader)

        # ── 2. Atlas Preset Dropdown Button ────────────────
        btn_atlas = QToolButton(container)
        btn_atlas.setIcon(get_icon("elevation"))
        btn_atlas.setText(" Atlas ▾")
        btn_atlas.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn_atlas.setPopupMode(QToolButton.InstantPopup)
        btn_atlas.setToolTip("Quick Color Ramp Atlas Presets")

        atlas_menu = QMenu(btn_atlas)
        atlas_menu.addAction("Atlas (Blue-Cyan-Green-Yellow-Red)", lambda: self.mw.apply_shader_preset("GLOBAL_MAPPER_ATLAS"))
        atlas_menu.addAction("Terrain (Earth Tones & Snow)", lambda: self.mw.apply_shader_preset("GLOBAL_MAPPER_TERRAIN"))
        atlas_menu.addAction("Magma (High Contrast)", lambda: self.mw.apply_shader_preset("MAGMA"))
        atlas_menu.addAction("Viridis (Perceptual Linear)", lambda: self.mw.apply_shader_preset("VIRIDIS"))
        btn_atlas.setMenu(atlas_menu)
        btn_row.addWidget(btn_atlas)

        # ── 3. Quick Action Buttons ────────────────────────
        items = [
            ("elevation", "Elevation", self.mw.open_dem_elevation_dialog, "DEM / Elevation Symbology & 3D Relief (Ctrl+Shift+E)"),
            ("slope", "Slope", self.mw.open_slope_dialog, "Calculate Slope"),
            ("aspect", "Aspect", self.mw.open_aspect_dialog, "Calculate Aspect Direction"),
            ("hillshade", "Hillshade", self.mw.open_hillshade_dialog, "3D Hillshade Relief"),
            ("view_3d", "3D View", self.mw.open_3d_viewer, "Interactive 3D Elevation Viewer"),
            ("profile", "Profile", self.mw.open_elevation_profile, "Elevation Profile Tool"),
            ("viewshed", "Viewshed", self.mw.open_viewshed, "Line of Sight & Viewshed Analysis"),
            ("profile", "Volumetrics", self.mw.open_volumetric_analysis, "Volumetric Analysis & Stage-Storage Capacity"),
            ("cut_fill", "Cut/Fill", self.mw.open_cut_fill, "Cut / Fill Earthwork Volume"),
            ("watershed", "Watershed", self.mw.open_hydro_watershed, "Watershed Drainage Basin"),
        ]
        for icon_key, text, slot, tip in items:
            btn = QToolButton(container)
            btn.setIcon(get_icon(icon_key))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setStatusTip(tip)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)

        lbl = QLabel("TERRAIN / ELEVATION", container)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #64748b; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding-top: 1px;")
        layout.addWidget(lbl)

        self.addWidget(container)
