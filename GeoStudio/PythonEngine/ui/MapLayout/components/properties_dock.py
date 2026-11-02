# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Item Properties Dock
Provides property inspectors for layout elements:
- Common geometry: X, Y, Width, Height, Rotation, Frame, Background, Opacity, Lock
- Specific editors for Map, Title/Label, Scale Bar, Legend, North Arrow/Picture, Shapes, Tables
"""

import os
import glob
from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QPushButton, QLabel, QTextEdit, QColorDialog, QFontDialog,
    QScrollArea, QHBoxLayout, QSlider, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QIcon

from qgis.core import (
    QgsApplication, QgsUnitTypes, QgsLayoutSize, QgsLayoutPoint,
    QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemScaleBar,
    QgsLayoutItemLegend, QgsLayoutItemPicture, QgsLayoutItemShape,
    QgsLayoutItemPolyline, QgsLayoutMeasurement, QgsProject
)


class LayoutPropertiesDock(QDockWidget):
    """Properties panel showing context-sensitive properties for selected layout items."""

    def __init__(self, layout_designer, parent=None):
        parent_widget = parent if isinstance(parent, QWidget) else (layout_designer if isinstance(layout_designer, QWidget) else None)
        super().__init__("Item Properties", parent_widget)
        self.designer = layout_designer
        self.setObjectName("layout_properties_dock")
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)

        self._current_item = None
        self._build_ui()

    def _build_ui(self):
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")

        self.container = QWidget()
        self.layout_v = QVBoxLayout(self.container)
        self.layout_v.setContentsMargins(6, 6, 6, 6)
        self.layout_v.setSpacing(6)

        # ── Item Header ──────────────────────────────────────────
        self.lbl_title = QLabel("No Item Selected")
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_title.setStyleSheet("color: #0f172a; padding: 5px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px;")
        self.layout_v.addWidget(self.lbl_title)

        # ── Common Position & Size Group ─────────────────────────
        self.grp_common = QGroupBox("Position and Size (mm)")
        form_pos = QFormLayout(self.grp_common)
        form_pos.setSpacing(5)

        self.spn_x = QDoubleSpinBox(); self.spn_x.setRange(-2000, 5000); self.spn_x.setDecimals(1)
        self.spn_y = QDoubleSpinBox(); self.spn_y.setRange(-2000, 5000); self.spn_y.setDecimals(1)
        self.spn_w = QDoubleSpinBox(); self.spn_w.setRange(0.5, 5000); self.spn_w.setDecimals(1)
        self.spn_h = QDoubleSpinBox(); self.spn_h.setRange(0.5, 5000); self.spn_h.setDecimals(1)
        self.spn_rot = QDoubleSpinBox(); self.spn_rot.setRange(-360, 360); self.spn_rot.setDecimals(1)

        self.spn_x.valueChanged.connect(self._on_pos_changed)
        self.spn_y.valueChanged.connect(self._on_pos_changed)
        self.spn_w.valueChanged.connect(self._on_size_changed)
        self.spn_h.valueChanged.connect(self._on_size_changed)
        self.spn_rot.valueChanged.connect(self._on_rot_changed)

        form_pos.addRow("X:", self.spn_x)
        form_pos.addRow("Y:", self.spn_y)
        form_pos.addRow("Width:", self.spn_w)
        form_pos.addRow("Height:", self.spn_h)
        form_pos.addRow("Rotation (°):", self.spn_rot)

        self.chk_lock = QCheckBox("Lock Position and Size")
        self.chk_lock.toggled.connect(self._on_lock_toggled)
        form_pos.addRow(self.chk_lock)

        self.layout_v.addWidget(self.grp_common)

        # ── Frame, Background & Opacity Group ────────────────────
        self.grp_frame = QGroupBox("Rendering & Appearance")
        form_frame = QFormLayout(self.grp_frame)
        form_frame.setSpacing(5)

        h_frame = QHBoxLayout()
        self.chk_has_frame = QCheckBox("Draw Frame")
        self.chk_has_frame.toggled.connect(self._on_frame_toggled)
        h_frame.addWidget(self.chk_has_frame)
        self.btn_frame_color = QPushButton("Color...")
        self.btn_frame_color.clicked.connect(self._pick_frame_color)
        h_frame.addWidget(self.btn_frame_color)
        form_frame.addRow(h_frame)

        h_bg = QHBoxLayout()
        self.chk_has_bg = QCheckBox("Background")
        self.chk_has_bg.toggled.connect(self._on_bg_toggled)
        h_bg.addWidget(self.chk_has_bg)
        self.btn_bg_color = QPushButton("Color...")
        self.btn_bg_color.clicked.connect(self._pick_bg_color)
        h_bg.addWidget(self.btn_bg_color)
        form_frame.addRow(h_bg)

        # Opacity Slider
        h_op = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(100)
        self.lbl_opacity = QLabel("100%")
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)
        h_op.addWidget(self.slider_opacity)
        h_op.addWidget(self.lbl_opacity)
        form_frame.addRow("Opacity:", h_op)

        self.layout_v.addWidget(self.grp_frame)

        # ── Element Specific Container ───────────────────────────
        self.element_container = QWidget()
        self.element_layout = QVBoxLayout(self.element_container)
        self.element_layout.setContentsMargins(0, 0, 0, 0)
        self.element_layout.setSpacing(6)
        self.layout_v.addWidget(self.element_container)

        self.layout_v.addStretch()
        self.scroll.setWidget(self.container)
        self.setWidget(self.scroll)

    def set_item(self, item):
        """Loads properties of the given layout item into the inspector."""
        self._current_item = item
        if not item:
            self.lbl_title.setText("No Item Selected")
            self.grp_common.setEnabled(False)
            self.grp_frame.setEnabled(False)
            self._clear_element_ui()
            return

        self.grp_common.setEnabled(True)
        self.grp_frame.setEnabled(True)

        name = item.id() if hasattr(item, "id") and item.id() else (item.displayName() if hasattr(item, "displayName") else type(item).__name__)
        item_type = type(item).__name__.replace("QgsLayoutItem", "")
        self.lbl_title.setText(f"{name} ({item_type})")

        try:
            # Load Position & Size
            pos = item.pos()
            if hasattr(item, "sizeWithUnits"):
                sz = item.sizeWithUnits()
                w_val = sz.width()
                h_val = sz.height()
            elif hasattr(item, "rect"):
                sz = item.rect()
                w_val = sz.width()
                h_val = sz.height()
            elif hasattr(item, "boundingRect"):
                sz = item.boundingRect()
                w_val = sz.width()
                h_val = sz.height()
            else:
                w_val = 10.0
                h_val = 10.0
            self.spn_x.blockSignals(True); self.spn_x.setValue(pos.x()); self.spn_x.blockSignals(False)
            self.spn_y.blockSignals(True); self.spn_y.setValue(pos.y()); self.spn_y.blockSignals(False)
            self.spn_w.blockSignals(True); self.spn_w.setValue(w_val); self.spn_w.blockSignals(False)
            self.spn_h.blockSignals(True); self.spn_h.setValue(h_val); self.spn_h.blockSignals(False)
            rot = item.itemRotation() if hasattr(item, "itemRotation") else (item.rotation() if hasattr(item, "rotation") else 0.0)
            self.spn_rot.blockSignals(True); self.spn_rot.setValue(rot); self.spn_rot.blockSignals(False)
            self.chk_lock.blockSignals(True); self.chk_lock.setChecked(item.isLocked() if hasattr(item, "isLocked") else False); self.chk_lock.blockSignals(False)

            frame_val = item.frameEnabled() if hasattr(item, "frameEnabled") else (item.hasFrame() if hasattr(item, "hasFrame") else False)
            bg_val = item.hasBackground() if hasattr(item, "hasBackground") else (item.backgroundEnabled() if hasattr(item, "backgroundEnabled") else False)
            self.chk_has_frame.blockSignals(True); self.chk_has_frame.setChecked(frame_val); self.chk_has_frame.blockSignals(False)
            self.chk_has_bg.blockSignals(True); self.chk_has_bg.setChecked(bg_val); self.chk_has_bg.blockSignals(False)

            # Opacity
            op = int(item.opacity() * 100) if hasattr(item, "opacity") else 100
            self.slider_opacity.blockSignals(True)
            self.slider_opacity.setValue(op)
            self.lbl_opacity.setText(f"{op}%")
            self.slider_opacity.blockSignals(False)

            self._clear_element_ui()

            # Build element-specific editor
            if isinstance(item, QgsLayoutItemMap):
                self._build_map_editor(item)
            elif isinstance(item, QgsLayoutItemLabel):
                self._build_label_editor(item)
            elif isinstance(item, QgsLayoutItemScaleBar):
                self._build_scalebar_editor(item)
            elif isinstance(item, QgsLayoutItemLegend):
                self._build_legend_editor(item)
            elif isinstance(item, QgsLayoutItemPicture):
                self._build_picture_editor(item)
            elif isinstance(item, QgsLayoutItemShape):
                self._build_shape_editor(item)
            elif hasattr(item, "setVectorLayer"):  # Attribute Table
                self._build_table_editor(item)
        except Exception as e:
            print(f"[LayoutPropertiesDock] Warning loading properties: {e}")

    def _clear_element_ui(self):
        while self.element_layout.count() > 0:
            it = self.element_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    # ── Map Item Editor ──────────────────────────────────────────
    # ── Map Item Editor ──────────────────────────────────────────
    def _build_map_editor(self, map_item):
        grp = QGroupBox("Map Properties & Cartography")
        form = QFormLayout(grp)
        form.setSpacing(5)

        # Scale Control
        self.spn_scale = QDoubleSpinBox()
        self.spn_scale.blockSignals(True)
        self.spn_scale.setRange(1, 100_000_000)
        self.spn_scale.setDecimals(0)
        self.spn_scale.setValue(map_item.scale())
        self.spn_scale.blockSignals(False)
        self.spn_scale.valueChanged.connect(lambda val: self._on_map_scale_changed(val, map_item))
        form.addRow("Scale 1 :", self.spn_scale)

        # Preset Scales Dropdown
        self.combo_scale_preset = QComboBox()
        self.combo_scale_preset.addItem("Scale Presets...")
        preset_scales = [
            ("1 : 500", 500),
            ("1 : 1,000", 1000),
            ("1 : 2,500", 2500),
            ("1 : 5,000", 5000),
            ("1 : 10,000", 10000),
            ("1 : 25,000", 25000),
            ("1 : 50,000", 50000),
            ("1 : 100,000", 100000),
            ("1 : 250,000", 250000),
            ("1 : 500,000", 500000),
            ("1 : 1,000,000", 1000000),
        ]
        for name, scale_val in preset_scales:
            self.combo_scale_preset.addItem(name, scale_val)
        self.combo_scale_preset.currentIndexChanged.connect(
            lambda idx: self._on_preset_scale_chosen(idx, map_item)
        )
        form.addRow("Presets:", self.combo_scale_preset)

        # Quick Zoom Buttons
        h_zoom = QHBoxLayout()
        btn_zoom_in = QPushButton("Zoom In 2×")
        btn_zoom_in.setToolTip("Zoom into map content (halves scale value)")
        btn_zoom_in.clicked.connect(lambda: self._zoom_map_item(map_item, 0.5))
        btn_zoom_out = QPushButton("Zoom Out 2×")
        btn_zoom_out.setToolTip("Zoom out of map content (doubles scale value)")
        btn_zoom_out.clicked.connect(lambda: self._zoom_map_item(map_item, 2.0))
        h_zoom.addWidget(btn_zoom_in)
        h_zoom.addWidget(btn_zoom_out)
        form.addRow("Quick Zoom:", h_zoom)

        # Extent Info Label
        ext = map_item.extent()
        dx = ext.width() if hasattr(ext, "width") else (ext.xMaximum() - ext.xMinimum())
        dy = ext.height() if hasattr(ext, "height") else (ext.yMaximum() - ext.yMinimum())
        self.lbl_map_ext = QLabel(
            f"X: [{ext.xMinimum():.1f}, {ext.xMaximum():.1f}] (w: {dx:.1f} m)\n"
            f"Y: [{ext.yMinimum():.1f}, {ext.yMaximum():.1f}] (h: {dy:.1f} m)"
        )
        self.lbl_map_ext.setStyleSheet("color: #475569; font-size: 10px; font-family: monospace;")
        form.addRow("Extent:", self.lbl_map_ext)

        # Fit to Layer Extents Button
        btn_full_ext = QPushButton("Zoom to Full Layer Extent")
        btn_full_ext.setToolTip("Fits the combined bounding box of all project layers into the map frame")
        btn_full_ext.setStyleSheet("font-weight: 500;")
        btn_full_ext.clicked.connect(lambda: self._zoom_to_layers_extent(map_item))
        form.addRow(btn_full_ext)

        # CRS
        crs_str = map_item.crs().authid() if map_item.crs().isValid() else "Not set"
        lbl_crs = QLabel(crs_str)
        lbl_crs.setStyleSheet("color: #0284c7; font-weight: 600;")
        form.addRow("CRS:", lbl_crs)

        # Raster Smoothing / Interpolation
        self.combo_resampling = QComboBox()
        self.combo_resampling.blockSignals(True)
        self.combo_resampling.addItem("Bilinear (Smooth - Recommended)", "bilinear")
        self.combo_resampling.addItem("Cubic (High detail bicubic)", "cubic")
        self.combo_resampling.addItem("Nearest Neighbour (Raw pixel grid)", "nearest")
        self.combo_resampling.setToolTip("Smooths pixelated or blocky raster/DEM cells with bilinear or bicubic filtering.")
        self.combo_resampling.setCurrentIndex(0)
        self.combo_resampling.blockSignals(False)
        self.combo_resampling.currentIndexChanged.connect(
            lambda idx: self._apply_raster_resampling(idx, map_item)
        )
        form.addRow("Raster Resampling:", self.combo_resampling)

        # Canvas Synchronization
        btn_canvas_ext = QPushButton("Sync Extent from Main Map")
        btn_canvas_ext.setToolTip("Copies current zoom extent and scale from main map canvas into layout map")
        btn_canvas_ext.clicked.connect(lambda: self._sync_extent_from_canvas(map_item))
        form.addRow(btn_canvas_ext)

        btn_apply_to_canvas = QPushButton("Set Main Map Extent from Layout")
        btn_apply_to_canvas.setToolTip("Applies this layout map's extent to the main application map canvas")
        btn_apply_to_canvas.clicked.connect(lambda: self._sync_canvas_from_map(map_item))
        form.addRow(btn_apply_to_canvas)

        # Coordinate Frame / Grid
        chk_grid = QCheckBox("Draw Coordinate Grid & Ticks")
        chk_grid.setChecked(map_item.grids().size() > 0 and map_item.grids().grid(0).isEnabled())
        chk_grid.toggled.connect(lambda chk: self._toggle_map_grid(map_item, chk))
        form.addRow(chk_grid)

        # Connect live extent changes (e.g. from Move Item Content tool)
        if hasattr(map_item, "extentChanged"):
            try:
                map_item.extentChanged.connect(lambda: self._on_map_extent_changed(map_item))
            except Exception:
                pass

        self.element_layout.addWidget(grp)

    def _on_map_scale_changed(self, val, map_item):
        if not map_item:
            return
        if abs(map_item.scale() - val) > 0.5:
            map_item.setScale(val)
            if hasattr(map_item, "refresh"):
                map_item.refresh()
            self._update_map_extent_label(map_item)
            if self.designer and hasattr(self.designer, "view") and self.designer.view:
                self.designer.view.update()

    def _on_preset_scale_chosen(self, idx, map_item):
        if idx <= 0 or not map_item:
            return
        scale_val = self.combo_scale_preset.itemData(idx)
        if scale_val:
            self.spn_scale.setValue(scale_val)

    def _zoom_map_item(self, map_item, factor: float):
        if not map_item:
            return
        new_scale = max(1.0, map_item.scale() * factor)
        self.spn_scale.setValue(new_scale)

    def _on_map_extent_changed(self, map_item):
        if not hasattr(self, "spn_scale") or not self.spn_scale:
            return
        self.spn_scale.blockSignals(True)
        self.spn_scale.setValue(map_item.scale())
        self.spn_scale.blockSignals(False)
        self._update_map_extent_label(map_item)

    def _update_map_extent_label(self, map_item):
        if not hasattr(self, "lbl_map_ext") or not self.lbl_map_ext:
            return
        ext = map_item.extent()
        dx = ext.width() if hasattr(ext, "width") else (ext.xMaximum() - ext.xMinimum())
        dy = ext.height() if hasattr(ext, "height") else (ext.yMaximum() - ext.yMinimum())
        self.lbl_map_ext.setText(
            f"X: [{ext.xMinimum():.1f}, {ext.xMaximum():.1f}] (w: {dx:.1f} m)\n"
            f"Y: [{ext.yMinimum():.1f}, {ext.yMaximum():.1f}] (h: {dy:.1f} m)"
        )

    def _zoom_to_layers_extent(self, map_item):
        try:
            from qgis.core import QgsRectangle, QgsCoordinateTransform
        except (ImportError, AttributeError):
            return

        prj = getattr(self.designer.layout, "project", lambda: None)() if self.designer and self.designer.layout else None
        if not prj:
            try:
                from qgis.core import QgsProject
                prj = QgsProject.instance()
            except Exception:
                prj = None

        layers = map_item.layers() if (hasattr(map_item, "layers") and map_item.layers()) else (list(prj.mapLayers().values()) if prj else [])
        valid_layers = [l for l in layers if hasattr(l, "isValid") and l.isValid()]
        if not valid_layers:
            return

        comb_ext = QgsRectangle()
        comb_ext.setNull()
        crs = map_item.crs() if (hasattr(map_item, "crs") and map_item.crs().isValid()) else (prj.crs() if prj else None)

        for lyr in valid_layers:
            lext = lyr.extent()
            if not lext.isNull() and not lext.isEmpty():
                if crs and lyr.crs().isValid() and lyr.crs() != crs and prj:
                    try:
                        tr = QgsCoordinateTransform(lyr.crs(), crs, prj)
                        lext = tr.transformBoundingBox(lext)
                    except Exception:
                        pass
                if comb_ext.isNull():
                    comb_ext = QgsRectangle(lext)
                else:
                    comb_ext.combineExtentWith(lext)

        if not comb_ext.isNull() and not comb_ext.isEmpty():
            comb_ext.scale(1.05)
            map_item.setExtent(comb_ext)
            if hasattr(map_item, "zoomToExtent"):
                map_item.zoomToExtent(comb_ext)
            if hasattr(map_item, "refresh"):
                map_item.refresh()
            self._on_map_extent_changed(map_item)
            if self.designer and hasattr(self.designer, "view") and self.designer.view:
                self.designer.view.update()

    def _apply_raster_resampling(self, idx, map_item):
        mode = self.combo_resampling.itemData(idx) if hasattr(self, "combo_resampling") else "bilinear"
        try:
            from qgis.core import (
                QgsRasterLayer, QgsRasterResampleFilter,
                QgsBilinearRasterResampler, QgsCubicRasterResampler
            )
        except (ImportError, AttributeError):
            return

        prj = getattr(self.designer.layout, "project", lambda: None)() if self.designer and self.designer.layout else None
        if not prj:
            try:
                from qgis.core import QgsProject
                prj = QgsProject.instance()
            except Exception:
                prj = None

        layers = map_item.layers() if (hasattr(map_item, "layers") and map_item.layers()) else (list(prj.mapLayers().values()) if prj else [])
        for lyr in layers:
            if isinstance(lyr, QgsRasterLayer):
                pipe = lyr.pipe()
                if pipe:
                    rf = pipe.resampleFilter()
                    if not rf:
                        rf = QgsRasterResampleFilter()
                        pipe.set(rf)
                    if mode == "bilinear":
                        rf.setZoomedInResampler(QgsBilinearRasterResampler())
                        rf.setZoomedOutResampler(QgsBilinearRasterResampler())
                        rf.setMaxOversampling(2.0)
                    elif mode == "cubic":
                        rf.setZoomedInResampler(QgsCubicRasterResampler())
                        rf.setZoomedOutResampler(QgsCubicRasterResampler())
                        rf.setMaxOversampling(2.0)
                    else:  # nearest
                        rf.setZoomedInResampler(None)
                        rf.setZoomedOutResampler(None)
                        rf.setMaxOversampling(1.0)
                    lyr.triggerRepaint()

        if hasattr(map_item, "refresh"):
            map_item.refresh()
        if self.designer and hasattr(self.designer, "view") and self.designer.view:
            self.designer.view.update()

    def _sync_extent_from_canvas(self, map_item):
        main_canvas = getattr(self.designer.mw, "map_canvas", None) if self.designer else None
        if main_canvas and getattr(main_canvas, "canvas", None) and not main_canvas.canvas.extent().isEmpty():
            map_item.setExtent(main_canvas.canvas.extent())
            map_item.setScale(main_canvas.canvas.scale())
            if hasattr(map_item, "refresh"):
                map_item.refresh()
            self._on_map_extent_changed(map_item)
            if self.designer and hasattr(self.designer, "view") and self.designer.view:
                self.designer.view.update()

    def _sync_canvas_from_map(self, map_item):
        main_canvas = getattr(self.designer.mw, "map_canvas", None) if self.designer else None
        if main_canvas and getattr(main_canvas, "canvas", None):
            main_canvas.canvas.setExtent(map_item.extent())
            main_canvas.canvas.refresh()

    def _toggle_map_grid(self, map_item, enabled: bool):
        try:
            from qgis.core import QgsLayoutItemMapGrid
            if map_item.grids().size() == 0 and enabled:
                grid = QgsLayoutItemMapGrid("Grid 1", map_item)
                grid.setEnabled(True)
                grid.setIntervalX(1000.0)
                grid.setIntervalY(1000.0)
                map_item.grids().addGrid(grid)
            elif map_item.grids().size() > 0:
                map_item.grids().grid(0).setEnabled(enabled)
            if hasattr(map_item, "refresh"):
                map_item.refresh()
            if self.designer and hasattr(self.designer, "view") and self.designer.view:
                self.designer.view.update()
        except Exception:
            pass

    # ── Label Item Editor ────────────────────────────────────────
    def _build_label_editor(self, label_item):
        grp = QGroupBox("Label & Text Properties")
        v = QVBoxLayout(grp)

        self.txt_label = QTextEdit()
        self.txt_label.setPlainText(label_item.text())
        self.txt_label.setFixedHeight(70)
        self.txt_label.textChanged.connect(lambda: (label_item.setText(self.txt_label.toPlainText()), self.designer.view.update()))
        v.addWidget(QLabel("Text:"))
        v.addWidget(self.txt_label)

        h_btn = QHBoxLayout()
        btn_font = QPushButton("Font...")
        btn_font.clicked.connect(lambda: self._pick_font(label_item))
        h_btn.addWidget(btn_font)

        btn_font_color = QPushButton("Font Color...")
        btn_font_color.clicked.connect(lambda: self._pick_font_color(label_item))
        h_btn.addWidget(btn_font_color)
        v.addLayout(h_btn)

        self.element_layout.addWidget(grp)

    def _pick_font(self, label_item):
        font, ok = QFontDialog.getFont(label_item.font(), self, "Select Font")
        if ok:
            label_item.setFont(font)
            self.designer.view.update()

    def _pick_font_color(self, label_item):
        col = QColorDialog.getColor(label_item.fontColor(), self, "Font Color")
        if col.isValid():
            label_item.setFontColor(col)
            self.designer.view.update()

    # ── Scale Bar Editor ─────────────────────────────────────────
    def _build_scalebar_editor(self, sb_item):
        grp = QGroupBox("Scale Bar Properties")
        form = QFormLayout(grp)
        form.setSpacing(5)

        combo_style = QComboBox()
        combo_style.addItems(["Single Box", "Double Box", "Line Ticks Up", "Line Ticks Down", "Numeric"])
        combo_style.setCurrentText(sb_item.style())
        combo_style.currentTextChanged.connect(lambda st: (sb_item.setStyle(st), self.designer.view.update()))
        form.addRow("Style:", combo_style)

        combo_units = QComboBox()
        combo_units.addItems(["Kilometers", "Meters", "Miles", "Feet"])
        combo_units.currentTextChanged.connect(lambda u: self._set_scalebar_units(sb_item, u))
        form.addRow("Units:", combo_units)

        spn_seg = QSpinBox()
        spn_seg.setRange(1, 10)
        spn_seg.setValue(sb_item.numberOfSegments())
        spn_seg.valueChanged.connect(lambda v: (sb_item.setNumberOfSegments(v), self.designer.view.update()))
        form.addRow("Segments (Right):", spn_seg)

        self.element_layout.addWidget(grp)

    def _set_scalebar_units(self, sb_item, unit_str):
        unit_map = {
            "Kilometers": QgsUnitTypes.DistanceKilometers,
            "Meters": QgsUnitTypes.DistanceMeters,
            "Miles": QgsUnitTypes.DistanceMiles,
            "Feet": QgsUnitTypes.DistanceFeet
        }
        sb_item.setUnits(unit_map.get(unit_str, QgsUnitTypes.DistanceKilometers))
        self.designer.view.update()

    # ── Legend Editor ────────────────────────────────────────────
    def _build_legend_editor(self, leg_item):
        grp = QGroupBox("Legend Properties")
        form = QFormLayout(grp)
        form.setSpacing(5)

        txt_leg_title = QLineEdit(leg_item.title())
        txt_leg_title.textChanged.connect(lambda t: (leg_item.setTitle(t), self.designer.view.update()))
        form.addRow("Title:", txt_leg_title)

        chk_auto = QCheckBox("Auto Update Layers")
        chk_auto.setChecked(leg_item.autoUpdateModel())
        chk_auto.toggled.connect(lambda c: (leg_item.setAutoUpdateModel(c), self.designer.view.update()))
        form.addRow(chk_auto)

        self.element_layout.addWidget(grp)

    # ── Picture / North Arrow Editor ─────────────────────────────
    def _build_picture_editor(self, pic_item):
        grp = QGroupBox("Picture / SVG Properties")
        v = QVBoxLayout(grp)

        lbl_path = QLabel(os.path.basename(pic_item.picturePath()) or "No image selected")
        lbl_path.setStyleSheet("color: #475569; font-size: 10px;")
        v.addWidget(lbl_path)

        btn_browse = QPushButton("Browse Image / SVG...")
        btn_browse.clicked.connect(lambda: self._browse_picture(pic_item, lbl_path))
        v.addWidget(btn_browse)

        self.element_layout.addWidget(grp)

    def _browse_picture(self, pic_item, lbl_path):
        f, _ = QFileDialog.getOpenFileName(self, "Select Image or SVG", "", "Images (*.png *.jpg *.jpeg *.svg *.webp)")
        if f:
            pic_item.setPicturePath(f)
            lbl_path.setText(os.path.basename(f))
            self.designer.view.update()

    # ── Shape Editor ─────────────────────────────────────────────
    def _build_shape_editor(self, shape_item):
        grp = QGroupBox("Shape Properties")
        form = QFormLayout(grp)
        form.setSpacing(5)

        combo_type = QComboBox()
        combo_type.addItems(["Rectangle", "Ellipse", "Triangle"])
        shape_types = [QgsLayoutItemShape.Rectangle, QgsLayoutItemShape.Ellipse, QgsLayoutItemShape.Triangle]
        cur_type = shape_item.shapeType()
        combo_type.setCurrentIndex(shape_types.index(cur_type) if cur_type in shape_types else 0)
        combo_type.currentIndexChanged.connect(lambda idx: (shape_item.setShapeType(shape_types[idx]), self.designer.view.update()))
        form.addRow("Shape Type:", combo_type)

        self.element_layout.addWidget(grp)

    # ── Table Editor ─────────────────────────────────────────────
    def _build_table_editor(self, table_item):
        grp = QGroupBox("Attribute Table Properties")
        form = QFormLayout(grp)
        form.setSpacing(5)

        combo_lyr = QComboBox()
        layers = [l for l in QgsProject.instance().mapLayers().values() if l.isValid() and l.type() == 0]
        for l in layers:
            combo_lyr.addItem(l.name(), l)

        combo_lyr.currentIndexChanged.connect(lambda idx: self._set_table_layer(table_item, combo_lyr.itemData(idx)))
        form.addRow("Vector Layer:", combo_lyr)

        self.element_layout.addWidget(grp)

    def _set_table_layer(self, table_item, layer):
        if layer and hasattr(table_item, "setVectorLayer"):
            table_item.setVectorLayer(layer)
            self.designer.view.update()

    # ── Common Callbacks ─────────────────────────────────────────
    def _on_pos_changed(self):
        if not self._current_item:
            return
        x = self.spn_x.value()
        y = self.spn_y.value()
        self._current_item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
        self.designer.view.update()

    def _on_size_changed(self):
        if not self._current_item:
            return
        w = max(0.5, self.spn_w.value())
        h = max(0.5, self.spn_h.value())
        self._current_item.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
        self.designer.view.update()

    def _on_rot_changed(self):
        if not self._current_item:
            return
        r = self.spn_rot.value()
        if hasattr(self._current_item, "setItemRotation"):
            self._current_item.setItemRotation(r)
        self.designer.view.update()

    def _on_lock_toggled(self, locked):
        if self._current_item and hasattr(self._current_item, "setLocked"):
            self._current_item.setLocked(locked)
            self.designer.items_dock.refresh_items()

    def _on_frame_toggled(self, checked):
        if self._current_item and hasattr(self._current_item, "setFrameEnabled"):
            self._current_item.setFrameEnabled(checked)
            self.designer.view.update()

    def _on_bg_toggled(self, checked):
        if self._current_item and hasattr(self._current_item, "setBackgroundEnabled"):
            self._current_item.setBackgroundEnabled(checked)
            self.designer.view.update()

    def _on_opacity_changed(self, val):
        if self._current_item and hasattr(self._current_item, "setOpacity"):
            self._current_item.setOpacity(val / 100.0)
            self.lbl_opacity.setText(f"{val}%")
            self.designer.view.update()

    def _pick_frame_color(self):
        if not self._current_item:
            return
        cur_col = self._current_item.frameStrokeColor() if hasattr(self._current_item, "frameStrokeColor") else QColor("#000000")
        col = QColorDialog.getColor(cur_col, self, "Frame Stroke Color")
        if col.isValid() and hasattr(self._current_item, "setFrameStrokeColor"):
            self._current_item.setFrameStrokeColor(col)
            self.designer.view.update()

    def _pick_bg_color(self):
        if not self._current_item:
            return
        cur_col = self._current_item.backgroundColor() if hasattr(self._current_item, "backgroundColor") else QColor("#ffffff")
        col = QColorDialog.getColor(cur_col, self, "Background Color")
        if col.isValid() and hasattr(self._current_item, "setBackgroundColor"):
            self._current_item.setBackgroundColor(col)
            self.designer.view.update()
