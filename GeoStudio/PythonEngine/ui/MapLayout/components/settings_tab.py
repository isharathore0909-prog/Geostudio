# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Settings Tab
Controls page presets, custom paper dimensions, grid spacing, snapping, and layout export settings.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QLabel,
    QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from qgis.core import (
    QgsLayoutSize, QgsUnitTypes, QgsLayoutMeasurement, QgsLayoutPoint,
    QgsLayoutItemMap
)

from ..config.presets import PAGE_PRESETS


class LayoutSettingsTab(QWidget):
    """Layout settings panel showing General Page Settings, Guides/Grid, and Export settings."""

    def __init__(self, designer, parent=None):
        super().__init__(parent)
        self.designer = designer
        self._build_ui()
        self._load_current_settings()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: #ffffff; }")

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # 1. Page & General Settings
        grp_gen = QGroupBox("Page & General Settings")
        f_gen = QFormLayout(grp_gen)
        f_gen.setSpacing(6)

        self.combo_page_size = QComboBox()
        self.combo_page_size.addItems(list(PAGE_PRESETS.keys()) + ["Custom"])
        self.combo_page_size.currentTextChanged.connect(self._on_page_preset_changed)
        f_gen.addRow("Page Preset:", self.combo_page_size)

        h_custom_size = QHBoxLayout()
        self.spn_page_w = QDoubleSpinBox()
        self.spn_page_w.setRange(10.0, 5000.0)
        self.spn_page_w.setValue(297.0)
        self.spn_page_w.setSuffix(" mm")
        self.spn_page_w.valueChanged.connect(self._on_custom_page_size_changed)

        self.spn_page_h = QDoubleSpinBox()
        self.spn_page_h.setRange(10.0, 5000.0)
        self.spn_page_h.setValue(210.0)
        self.spn_page_h.setSuffix(" mm")
        self.spn_page_h.valueChanged.connect(self._on_custom_page_size_changed)

        h_custom_size.addWidget(self.spn_page_w)
        h_custom_size.addWidget(QLabel("×"))
        h_custom_size.addWidget(self.spn_page_h)
        f_gen.addRow("Dimensions:", h_custom_size)

        self.combo_ref_map = QComboBox()
        self.combo_ref_map.addItem("Current Map")
        self.combo_ref_map.currentIndexChanged.connect(self._on_ref_map_changed)
        f_gen.addRow("Reference Map:", self.combo_ref_map)

        vbox.addWidget(grp_gen)

        # 2. Guides and Grid
        grp_grid = QGroupBox("Guides and Grid")
        f_grid = QFormLayout(grp_grid)
        f_grid.setSpacing(6)

        h_spacing = QHBoxLayout()
        self.spn_spacing = QDoubleSpinBox()
        self.spn_spacing.setRange(0.1, 500.0)
        self.spn_spacing.setValue(10.0)
        self.spn_spacing.valueChanged.connect(self._apply_grid_settings)

        self.combo_grid_units = QComboBox()
        self.combo_grid_units.addItems(["mm", "cm", "px"])
        self.combo_grid_units.currentTextChanged.connect(self._apply_grid_settings)

        h_spacing.addWidget(self.spn_spacing, 1)
        h_spacing.addWidget(self.combo_grid_units)
        f_grid.addRow("Grid spacing:", h_spacing)

        h_offset_x = QHBoxLayout()
        self.spn_off_x = QDoubleSpinBox()
        self.spn_off_x.setRange(-500.0, 500.0)
        self.spn_off_x.setValue(0.0)
        self.spn_off_x.valueChanged.connect(self._apply_grid_settings)
        h_offset_x.addWidget(self.spn_off_x, 1)
        h_offset_x.addWidget(QLabel("mm"))
        f_grid.addRow("Grid offset X:", h_offset_x)

        h_offset_y = QHBoxLayout()
        self.spn_off_y = QDoubleSpinBox()
        self.spn_off_y.setRange(-500.0, 500.0)
        self.spn_off_y.setValue(0.0)
        self.spn_off_y.valueChanged.connect(self._apply_grid_settings)
        h_offset_y.addWidget(self.spn_off_y, 1)
        h_offset_y.addWidget(QLabel("mm"))
        f_grid.addRow("Grid offset Y:", h_offset_y)

        self.spn_snap_tol = QSpinBox()
        self.spn_snap_tol.setRange(1, 50)
        self.spn_snap_tol.setValue(5)
        self.spn_snap_tol.setSuffix(" px")
        self.spn_snap_tol.valueChanged.connect(self._apply_snapping_settings)
        f_grid.addRow("Snap tolerance:", self.spn_snap_tol)

        self.chk_show_grid = QCheckBox("Show Grid")
        self.chk_show_grid.toggled.connect(self._on_toggle_grid)
        f_grid.addRow(self.chk_show_grid)

        self.chk_snap_grid = QCheckBox("Snap to Grid")
        self.chk_snap_grid.toggled.connect(self._apply_snapping_settings)
        f_grid.addRow(self.chk_snap_grid)

        self.chk_snap_guides = QCheckBox("Snap to Guides")
        self.chk_snap_guides.setChecked(True)
        self.chk_snap_guides.toggled.connect(self._apply_snapping_settings)
        f_grid.addRow(self.chk_snap_guides)

        self.chk_snap_items = QCheckBox("Snap to Items")
        self.chk_snap_items.setChecked(True)
        self.chk_snap_items.toggled.connect(self._apply_snapping_settings)
        f_grid.addRow(self.chk_snap_items)

        vbox.addWidget(grp_grid)

        # 3. Export Settings
        grp_export = QGroupBox("Export Settings")
        f_exp = QFormLayout(grp_export)
        f_exp.setSpacing(6)

        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["72 dpi", "96 dpi", "150 dpi", "200 dpi", "300 dpi", "600 dpi", "1200 dpi"])
        self.combo_dpi.setCurrentText("300 dpi")
        self.combo_dpi.currentTextChanged.connect(self._on_dpi_changed)
        f_exp.addRow("Export resolution:", self.combo_dpi)

        self.chk_raster = QCheckBox("Print as raster")
        f_exp.addRow(self.chk_raster)

        self.chk_vectors = QCheckBox("Always export as vectors")
        self.chk_vectors.setChecked(True)
        f_exp.addRow(self.chk_vectors)

        btn_open_export = QPushButton("Open GeoStudio Export Dialog...")
        btn_open_export.setStyleSheet("font-weight: bold; padding: 6px;")
        btn_open_export.clicked.connect(self.designer.open_export_dialog)
        f_exp.addRow(btn_open_export)

        vbox.addWidget(grp_export)
        vbox.addStretch()

        self.scroll.setWidget(container)
        root_layout.addWidget(self.scroll)

    def _load_current_settings(self):
        if not self.designer.layout:
            return
        layout = self.designer.layout
        pages = layout.pageCollection().pages()
        if pages:
            p = pages[0]
            w = p.pageSize().width()
            h = p.pageSize().height()
            self.spn_page_w.blockSignals(True)
            self.spn_page_h.blockSignals(True)
            self.spn_page_w.setValue(w)
            self.spn_page_h.setValue(h)
            self.spn_page_w.blockSignals(False)
            self.spn_page_h.blockSignals(False)

            # Match preset
            matched = False
            for name, (pw, ph) in PAGE_PRESETS.items():
                if abs(pw - w) < 1.0 and abs(ph - h) < 1.0:
                    self.combo_page_size.blockSignals(True)
                    self.combo_page_size.setCurrentText(name)
                    self.combo_page_size.blockSignals(False)
                    matched = True
                    break
            if not matched:
                self.combo_page_size.blockSignals(True)
                self.combo_page_size.setCurrentText("Custom")
                self.combo_page_size.blockSignals(False)

        # Snapper settings
        if hasattr(layout, "snapper") and layout.snapper():
            s = layout.snapper()
            self.chk_snap_grid.blockSignals(True)
            self.chk_snap_grid.setChecked(s.snapToGrid())
            self.chk_snap_grid.blockSignals(False)

            self.chk_snap_guides.blockSignals(True)
            self.chk_snap_guides.setChecked(s.snapToGuides())
            self.chk_snap_guides.blockSignals(False)

            self.chk_snap_items.blockSignals(True)
            self.chk_snap_items.setChecked(s.snapToItems())
            self.chk_snap_items.blockSignals(False)

            self.spn_snap_tol.blockSignals(True)
            self.spn_snap_tol.setValue(s.snapTolerance())
            self.spn_snap_tol.blockSignals(False)

        # Export DPI setting
        if hasattr(layout, "renderContext") and layout.renderContext():
            try:
                cur_dpi = int(layout.renderContext().dpi())
                for i in range(self.combo_dpi.count()):
                    if str(cur_dpi) in self.combo_dpi.itemText(i):
                        self.combo_dpi.blockSignals(True)
                        self.combo_dpi.setCurrentIndex(i)
                        self.combo_dpi.blockSignals(False)
                        break
            except Exception:
                pass

    def _on_dpi_changed(self, text):
        if not self.designer.layout:
            return
        try:
            dpi_val = int(text.split()[0])
            if hasattr(self.designer.layout, "renderContext") and self.designer.layout.renderContext():
                self.designer.layout.renderContext().setDpi(dpi_val)
            if hasattr(self.designer.layout, "refresh"):
                self.designer.layout.refresh()
            if self.designer.view:
                self.designer.view.update()
        except Exception as e:
            print(f"[LayoutSettingsTab] Error setting DPI: {e}")

    def _on_page_preset_changed(self, text):
        if text in PAGE_PRESETS:
            w, h = PAGE_PRESETS[text]
            self.spn_page_w.setValue(w)
            self.spn_page_h.setValue(h)
            self._set_page_size(w, h)

    def _on_custom_page_size_changed(self):
        w = self.spn_page_w.value()
        h = self.spn_page_h.value()
        self._set_page_size(w, h)

    def _set_page_size(self, w: float, h: float):
        if not self.designer.layout:
            return
        pages = self.designer.layout.pageCollection().pages()
        if pages:
            pages[0].attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
            self.designer.view.update()
            self.designer.zoom_to_page()

    def _apply_grid_settings(self):
        if not self.designer.layout or not hasattr(self.designer.layout, "gridSettings"):
            return
        gs = self.designer.layout.gridSettings()
        val = self.spn_spacing.value()
        unit_str = self.combo_grid_units.currentText()
        unit = QgsUnitTypes.LayoutMillimeters
        if unit_str == "cm":
            unit = QgsUnitTypes.LayoutCentimeters
        elif unit_str == "px":
            unit = QgsUnitTypes.LayoutPixels

        gs.setResolution(QgsLayoutMeasurement(val, unit))
        gs.setOffset(QgsLayoutPoint(self.spn_off_x.value(), self.spn_off_y.value(), unit))
        self.designer.view.update()

    def _apply_snapping_settings(self):
        if not self.designer.layout or not hasattr(self.designer.layout, "snapper"):
            return
        snapper = self.designer.layout.snapper()
        snapper.setSnapToGrid(self.chk_snap_grid.isChecked())
        snapper.setSnapToGuides(self.chk_snap_guides.isChecked())
        snapper.setSnapToItems(self.chk_snap_items.isChecked())
        snapper.setSnapTolerance(self.spn_snap_tol.value())

    def _on_toggle_grid(self, checked):
        if not self.designer.layout:
            return
        self.designer.layout.renderContext().setGridVisible(checked)
        self.designer.view.update()

    def refresh_maps(self):
        self.combo_ref_map.blockSignals(True)
        self.combo_ref_map.clear()
        self.combo_ref_map.addItem("Current Map")
        if self.designer.layout:
            for item in self.designer.layout.items():
                if isinstance(item, QgsLayoutItemMap):
                    name = item.id() or "Map Frame"
                    self.combo_ref_map.addItem(name)
        self.combo_ref_map.blockSignals(False)

    def _on_ref_map_changed(self, idx):
        pass
