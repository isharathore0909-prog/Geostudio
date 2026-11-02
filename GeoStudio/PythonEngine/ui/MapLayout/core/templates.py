# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Template Engine
Defines standard professional cartographic layout templates:
- A4 Portrait / Landscape
- A3 Portrait / Landscape
- A2, A1, A0 Presets
- Map Report, Survey Map, and Thematic layouts
"""

import math
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutItemShape, QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes,
    QgsLayoutMeasurement
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

from ..config.presets import PAGE_SIZES


def create_layout_from_template(project, name: str, template_type: str = "A4 Landscape", map_canvas=None):
    """
    Creates and populates a QgsPrintLayout based on a named template preset.
    """
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)

    page = layout.pageCollection().pages()[0]

    # 1. Determine Page Dimensions & Orientation
    is_landscape = "Landscape" in template_type or "Empty" in template_type or template_type in ["A0", "A1", "A2", "Survey Map", "Thematic Map"]
    size_key = "A4"
    for k in PAGE_SIZES:
        if k in template_type:
            size_key = k
            break

    pw, ph = PAGE_SIZES[size_key]
    if is_landscape and pw < ph:
        pw, ph = ph, pw
    elif (not is_landscape) and pw > ph:
        pw, ph = ph, pw

    page.setPageSize(QgsLayoutSize(pw, ph, QgsUnitTypes.LayoutMillimeters))

    if "Empty" in template_type:
        return layout

    # 2. Add Border / Neatline Frame
    margin = 8.0
    frame_w = pw - (margin * 2)
    frame_h = ph - (margin * 2)

    border = QgsLayoutItemShape(layout)
    border.setShapeType(QgsLayoutItemShape.Rectangle)
    border.attemptResize(QgsLayoutSize(frame_w, frame_h, QgsUnitTypes.LayoutMillimeters))
    border.attemptMove(QgsLayoutPoint(margin, margin, QgsUnitTypes.LayoutMillimeters))
    border.setFrameEnabled(True)
    border.setFrameStrokeWidth(QgsLayoutMeasurement(0.6, QgsUnitTypes.LayoutMillimeters))
    border.setFrameStrokeColor(QColor("#0f172a"))
    border.setBackgroundEnabled(False)
    layout.addLayoutItem(border)

    # 3. Add Main Map Item
    map_x = margin + 4.0
    map_y = margin + 18.0

    # Reserve space for right sidebar legend in landscape
    sidebar_w = 55.0 if pw >= 250.0 else 0.0
    map_w = frame_w - 8.0 - (sidebar_w + 4.0 if sidebar_w > 0 else 0.0)
    map_h = frame_h - 26.0

    map_item = QgsLayoutItemMap(layout)
    map_item.setId("Main Map")
    map_item.attemptResize(QgsLayoutSize(map_w, map_h, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptMove(QgsLayoutPoint(map_x, map_y, QgsUnitTypes.LayoutMillimeters))
    map_item.setFrameEnabled(True)
    map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.4, QgsUnitTypes.LayoutMillimeters))
    map_item.setFrameStrokeColor(QColor("#475569"))
    map_item.setBackgroundColor(QColor("#ffffff"))

    if map_canvas and getattr(map_canvas, "canvas", None) and not map_canvas.canvas.extent().isEmpty():
        map_item.setExtent(map_canvas.canvas.extent())
        map_item.setCrs(map_canvas.canvas.mapSettings().destinationCrs())
        map_item.setLayers(map_canvas.canvas.layers())
    else:
        valid_layers = [l for l in project.mapLayers().values() if l.isValid()]
        map_item.setLayers(valid_layers)
        if valid_layers:
            from qgis.core import QgsRectangle
            comb_ext = QgsRectangle(valid_layers[0].extent())
            for l in valid_layers[1:]:
                comb_ext.combineExtentWith(l.extent())
            map_item.setExtent(comb_ext)
        else:
            from qgis.core import QgsRectangle
            map_item.setExtent(QgsRectangle(-180.0, -90.0, 180.0, 90.0))
        if project.crs().isValid():
            map_item.setCrs(project.crs())

    layout.addLayoutItem(map_item)

    # 4. Add Title Banner
    title_item = QgsLayoutItemLabel(layout)
    title_item.setId("Title")
    title_item.setText(f"{name} — GeoStudio")
    title_font = QFont("Segoe UI", 14, QFont.Bold)
    title_item.setFont(title_font)
    title_item.setFontColor(QColor("#0f172a"))
    title_item.attemptResize(QgsLayoutSize(map_w, 14.0, QgsUnitTypes.LayoutMillimeters))
    title_item.attemptMove(QgsLayoutPoint(map_x, margin + 2.0, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(title_item)

    # 5. Add Scale Bar Item
    scale_item = QgsLayoutItemScaleBar(layout)
    scale_item.setId("Scale Bar")
    scale_item.setLinkedMap(map_item)
    scale_item.setStyle("Single Box")
    scale_item.setUnits(QgsUnitTypes.DistanceKilometers)
    scale_item.setNumberOfSegments(3)
    scale_item.setNumberOfSegmentsLeft(0)
    scale_item.setFont(QFont("Segoe UI", 8))
    scale_item.setFontColor(QColor("#0f172a"))
    scale_item.attemptResize(QgsLayoutSize(45.0, 10.0, QgsUnitTypes.LayoutMillimeters))
    scale_item.attemptMove(QgsLayoutPoint(map_x + 4.0, map_y + map_h - 14.0, QgsUnitTypes.LayoutMillimeters))
    scale_item.setBackgroundEnabled(True)
    scale_item.setBackgroundColor(QColor(255, 255, 255, 220))
    layout.addLayoutItem(scale_item)

    # 6. Add North Arrow
    north_item = QgsLayoutItemPicture(layout)
    north_item.setId("North Arrow")
    north_item.attemptResize(QgsLayoutSize(14.0, 18.0, QgsUnitTypes.LayoutMillimeters))
    north_item.attemptMove(QgsLayoutPoint(map_x + map_w - 18.0, map_y + 4.0, QgsUnitTypes.LayoutMillimeters))
    north_item.setLinkedMap(map_item)
    north_item.setBackgroundEnabled(True)
    north_item.setBackgroundColor(QColor(255, 255, 255, 200))
    layout.addLayoutItem(north_item)

    # 7. Add Legend Item (in right sidebar or bottom right)
    if sidebar_w > 0:
        legend_x = map_x + map_w + 4.0
        legend_y = map_y
        legend_w = sidebar_w
        legend_h = map_h

        legend_item = QgsLayoutItemLegend(layout)
        legend_item.setId("Legend")
        legend_item.setTitle("Legend")
        legend_item.setLinkedMap(map_item)
        legend_item.attemptResize(QgsLayoutSize(legend_w, legend_h, QgsUnitTypes.LayoutMillimeters))
        legend_item.attemptMove(QgsLayoutPoint(legend_x, legend_y, QgsUnitTypes.LayoutMillimeters))
        legend_item.setFrameEnabled(True)
        legend_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
        legend_item.setFrameStrokeColor(QColor("#cbd5e1"))
        legend_item.setBackgroundColor(QColor("#ffffff"))
        layout.addLayoutItem(legend_item)

    return layout
