# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Type Definitions & Enumerations
Provides typing hints, protocols, and enumerations for MapLayout operations.
"""

from enum import Enum, auto
from typing import Tuple, Dict, Any, Optional, Union, List


class ExportFormat(Enum):
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpg"
    TIFF = "tif"
    SVG = "svg"


class AlignmentType(Enum):
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    MIDDLE = "middle"


class DistributionAxis(Enum):
    HORIZONTAL = "h"
    VERTICAL = "v"


class PageOrientation(Enum):
    LANDSCAPE = "Landscape"
    PORTRAIT = "Portrait"


class ToolType(Enum):
    SELECT = "select"
    PAN = "pan"
    MOVE_CONTENT = "move_content"
    MAP = "map"
    LABEL = "label"
    LEGEND = "legend"
    SCALEBAR = "scalebar"
    NORTH_ARROW = "north_arrow"
    IMAGE = "image"
    TABLE = "table"
    SHAPE = "shape"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    LINE = "line"
    ARROW = "arrow"


# Dimensions: (width_mm, height_mm)
PageDimensionTuple = Tuple[float, float]

__all__ = [
    "ExportFormat",
    "AlignmentType",
    "DistributionAxis",
    "PageOrientation",
    "ToolType",
    "PageDimensionTuple",
]
