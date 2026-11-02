# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Core Actions
Geometric alignment, distribution, and canvas-to-layout synchronization logic.
"""

from qgis.core import QgsLayoutPoint, QgsUnitTypes, QgsLayoutItemMap


def align_items(layout, align_type: str):
    """
    Align selected items in the layout:
    'left', 'right', 'top', 'bottom', 'center', 'middle'
    """
    selected = layout.selectedLayoutItems()
    if len(selected) < 2:
        return
    if align_type == "left":
        min_x = min(it.pos().x() for it in selected)
        for it in selected:
            it.attemptMove(QgsLayoutPoint(min_x, it.pos().y(), QgsUnitTypes.LayoutMillimeters))
    elif align_type == "right":
        max_r = max(it.pos().x() + (it.sizeWithUnits().width() if hasattr(it, "sizeWithUnits") else it.rect().width()) for it in selected)
        for it in selected:
            w = it.sizeWithUnits().width() if hasattr(it, "sizeWithUnits") else it.rect().width()
            it.attemptMove(QgsLayoutPoint(max_r - w, it.pos().y(), QgsUnitTypes.LayoutMillimeters))
    elif align_type == "top":
        min_y = min(it.pos().y() for it in selected)
        for it in selected:
            it.attemptMove(QgsLayoutPoint(it.pos().x(), min_y, QgsUnitTypes.LayoutMillimeters))
    elif align_type == "bottom":
        max_b = max(it.pos().y() + (it.sizeWithUnits().height() if hasattr(it, "sizeWithUnits") else it.rect().height()) for it in selected)
        for it in selected:
            h = it.sizeWithUnits().height() if hasattr(it, "sizeWithUnits") else it.rect().height()
            it.attemptMove(QgsLayoutPoint(it.pos().x(), max_b - h, QgsUnitTypes.LayoutMillimeters))
    elif align_type == "center":
        avg_x = sum(it.pos().x() + (it.sizeWithUnits().width() if hasattr(it, "sizeWithUnits") else it.rect().width()) / 2.0 for it in selected) / len(selected)
        for it in selected:
            w = it.sizeWithUnits().width() if hasattr(it, "sizeWithUnits") else it.rect().width()
            it.attemptMove(QgsLayoutPoint(avg_x - w / 2.0, it.pos().y(), QgsUnitTypes.LayoutMillimeters))
    elif align_type == "middle":
        avg_y = sum(it.pos().y() + (it.sizeWithUnits().height() if hasattr(it, "sizeWithUnits") else it.rect().height()) / 2.0 for it in selected) / len(selected)
        for it in selected:
            h = it.sizeWithUnits().height() if hasattr(it, "sizeWithUnits") else it.rect().height()
            it.attemptMove(QgsLayoutPoint(it.pos().x(), avg_y - h / 2.0, QgsUnitTypes.LayoutMillimeters))


def distribute_items(layout, axis: str):
    """
    Distribute selected items evenly along axis:
    'h' (horizontally) or 'v' (vertically).
    """
    selected = sorted(layout.selectedLayoutItems(), key=lambda it: it.pos().x() if axis == "h" else it.pos().y())
    if len(selected) < 3:
        return
    if axis == "h":
        start_x = selected[0].pos().x()
        end_x = selected[-1].pos().x()
        step = (end_x - start_x) / (len(selected) - 1)
        for i, it in enumerate(selected):
            it.attemptMove(QgsLayoutPoint(start_x + i * step, it.pos().y(), QgsUnitTypes.LayoutMillimeters))
    else:
        start_y = selected[0].pos().y()
        end_y = selected[-1].pos().y()
        step = (end_y - start_y) / (len(selected) - 1)
        for i, it in enumerate(selected):
            it.attemptMove(QgsLayoutPoint(it.pos().x(), start_y + i * step, QgsUnitTypes.LayoutMillimeters))


def get_first_map_item(layout):
    """Finds and returns the primary QgsLayoutItemMap in the layout."""
    for item in layout.items():
        if isinstance(item, QgsLayoutItemMap):
            return item
    return None
