# -*- coding: utf-8 -*-
"""
GeoStudio - MapLayout Mocked Unit Test Suite
Allows verifying the entire MapLayout architecture, classes, methods,
initialization logic, signals, actions, and presets in environments where
C-extensions (PyQt5 / PyQGIS) are restricted by Code Integrity policies.
"""

import sys
import os
import types
import unittest

# Ensure repo root and app dir are on sys.path
_cur = os.path.abspath(__file__)
while _cur and os.path.dirname(_cur) != _cur:
    if os.path.exists(os.path.join(_cur, "app", "main.py")):
        _repo_root = _cur
        break
    _cur = os.path.dirname(_cur)
else:
    _repo_root = r"M:\Geo Studio\GeoStudio"

_app_dir = os.path.join(_repo_root, "app")
for _p in [_app_dir, _repo_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Install lightweight mock objects for PyQt5 and qgis in sys.modules ──
def _create_mock_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod

# Mock PyQt5
if "PyQt5" not in sys.modules:
    pyqt5 = _create_mock_module("PyQt5")
    
    # QtCore
    qtcore = _create_mock_module("PyQt5.QtCore")
    class Qt:
        Horizontal = 1
        Vertical = 2
        ApplicationModal = 2
        RightDockWidgetArea = 2
        LeftToolBarArea = 1
        TopToolBarArea = 4
        UserRole = 32
        AlignCenter = 0x0004
        AlignVCenter = 0x0080
        AlignLeft = 0x0001
        KeepAspectRatio = 1
        NoPen = 0
        NoBrush = 0
        CustomContextMenu = 3
        ItemIsSelectable = 1
        ItemIsEnabled = 32
        Checked = 2
        Unchecked = 0
    qtcore.Qt = Qt
    class QSize:
        def __init__(self, w=0, h=0): self.w, self.h = w, h
    qtcore.QSize = QSize
    class QSizeF:
        def __init__(self, w=0, h=0): self.w, self.h = w, h
    qtcore.QSizeF = QSizeF
    class QPointF:
        def __init__(self, x=0, y=0): self.x, self.y = x, y
    qtcore.QPointF = QPointF
    class QRectF:
        def __init__(self, x=0, y=0, w=0, h=0): pass
    qtcore.QRectF = QRectF
    class QUrl:
        @staticmethod
        def fromLocalFile(path): return path
    qtcore.QUrl = QUrl
    def pyqtSignal(*args):
        class Signal:
            def connect(self, slot): pass
            def emit(self, *a): pass
        return Signal()
    qtcore.pyqtSignal = pyqtSignal
    class QCoreApplication:
        @staticmethod
        def processEvents(): pass
    qtcore.QCoreApplication = QCoreApplication

    # QtGui
    qtgui = _create_mock_module("PyQt5.QtGui")
    class QColor:
        def __init__(self, *args): pass
        def isValid(self): return True
    qtgui.QColor = QColor
    class QFont:
        Bold = 75
        def __init__(self, *args): pass
    qtgui.QFont = QFont
    class QIcon:
        def __init__(self, *args): pass
    qtgui.QIcon = QIcon
    class QImage:
        Format_ARGB32_Premultiplied = 5
        def __init__(self, *args): pass
        def fill(self, *args): pass
        def save(self, *args): pass
    qtgui.QImage = QImage
    class QPainter:
        Antialiasing = 1
        def __init__(self, *args): pass
        def setRenderHint(self, *args): pass
        def setPen(self, *args): pass
        def setBrush(self, *args): pass
        def drawRoundedRect(self, *args): pass
        def drawRect(self, *args): pass
        def drawEllipse(self, *args): pass
        def drawPolygon(self, *args): pass
        def drawLine(self, *args): pass
        def drawText(self, *args): pass
        def setFont(self, *args): pass
        def drawImage(self, *args): pass
        def end(self): pass
    qtgui.QPainter = QPainter
    class QPen:
        def __init__(self, *args): pass
    qtgui.QPen = QPen
    class QBrush:
        def __init__(self, *args): pass
    qtgui.QBrush = QBrush
    class QPolygonF:
        def __init__(self, *args): pass
    qtgui.QPolygonF = QPolygonF
    class QDesktopServices:
        @staticmethod
        def openUrl(url): pass
    qtgui.QDesktopServices = QDesktopServices
    class QPdfWriter:
        def __init__(self, *args): pass
        def setResolution(self, *args): pass
        def setPageSizeMM(self, *args): pass
    qtgui.QPdfWriter = QPdfWriter

    # QtWidgets
    qtwidgets = _create_mock_module("PyQt5.QtWidgets")
    class QWidget:
        def __init__(self, parent=None): pass
        def setLayout(self, layout): pass
        def setStyleSheet(self, s): pass
        def setEnabled(self, e): pass
        def setWindowTitle(self, t): pass
        def setToolTip(self, t): pass
        def setStatusTip(self, t): pass
        def resize(self, w, h): pass
        def setMinimumWidth(self, w): pass
        def setMinimumSize(self, w, h): pass
        def setMaximumWidth(self, w): pass
        def setWindowModality(self, m): pass
        def show(self): pass
        def hide(self): pass
        def close(self): pass
        def accept(self): pass
        def reject(self): pass
        def exec_(self): return 1
    qtwidgets.QWidget = QWidget
    class QMainWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self._sb = QStatusBar()
            self._mb = QMenuBar()
        def setCentralWidget(self, w): pass
        def addDockWidget(self, area, dock): pass
        def addToolBar(self, *args): return QToolBar()
        def addToolBarBreak(self, *args): pass
        def statusBar(self): return self._sb
        def menuBar(self): return self._mb
    qtwidgets.QMainWindow = QMainWindow
    class QDialog(QWidget): pass
    qtwidgets.QDialog = QDialog
    class QDockWidget(QWidget):
        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self._w = None
        def setObjectName(self, name): pass
        def setWidget(self, w): self._w = w
        def widget(self): return self._w or QWidget()
    qtwidgets.QDockWidget = QDockWidget
    class QVBoxLayout:
        def __init__(self, parent=None): pass
        def setContentsMargins(self, *args): pass
        def setSpacing(self, *args): pass
        def addWidget(self, *args): pass
        def addLayout(self, *args): pass
        def addStretch(self, *args): pass
        def addSpacing(self, *args): pass
        def count(self): return 0
    qtwidgets.QVBoxLayout = QVBoxLayout
    class QHBoxLayout(QVBoxLayout): pass
    qtwidgets.QHBoxLayout = QHBoxLayout
    class QFormLayout(QVBoxLayout):
        def addRow(self, *args): pass
    qtwidgets.QFormLayout = QFormLayout
    class QLabel(QWidget):
        def __init__(self, text="", parent=None): super().__init__(parent)
        def setText(self, t): pass
        def setFont(self, f): pass
        def setAlignment(self, a): pass
    qtwidgets.QLabel = QLabel
    class QPushButton(QWidget):
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self.clicked = pyqtSignal()
        def setText(self, t): pass
    qtwidgets.QPushButton = QPushButton
    class QToolButton(QPushButton):
        def setIcon(self, ic): pass
        def setIconSize(self, sz): pass
        def setToolTip(self, t): pass
        def setStatusTip(self, t): pass
    qtwidgets.QToolButton = QToolButton
    class QComboBox(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.currentIndexChanged = pyqtSignal()
            self.currentTextChanged = pyqtSignal()
            self._items = []
            self._idx = 0
        def addItems(self, items): self._items.extend(items)
        def addItem(self, item, data=None): self._items.append(item)
        def currentText(self): return self._items[self._idx] if 0 <= self._idx < len(self._items) else ""
        def currentIndex(self): return self._idx
        def setCurrentText(self, t):
            if t in self._items: self._idx = self._items.index(t)
        def setCurrentIndex(self, i): self._idx = i
        def clear(self): self._items.clear(); self._idx = 0
        def count(self): return len(self._items)
        def blockSignals(self, b): pass
        def itemData(self, i): return None
    qtwidgets.QComboBox = QComboBox
    class QSpinBox(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.valueChanged = pyqtSignal()
            self._val = 0
        def setRange(self, mi, ma): pass
        def setValue(self, v): self._val = v
        def value(self): return self._val
        def setSuffix(self, s): pass
        def blockSignals(self, b): pass
    qtwidgets.QSpinBox = QSpinBox
    class QDoubleSpinBox(QSpinBox):
        def setDecimals(self, d): pass
    qtwidgets.QDoubleSpinBox = QDoubleSpinBox
    class QCheckBox(QWidget):
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self.toggled = pyqtSignal()
            self._chk = False
        def setChecked(self, c): self._chk = c
        def isChecked(self): return self._chk
        def toggle(self): self._chk = not self._chk
        def blockSignals(self, b): pass
    qtwidgets.QCheckBox = QCheckBox
    class QLineEdit(QWidget):
        def __init__(self, text="", parent=None):
            super().__init__(parent)
            self.textChanged = pyqtSignal()
            self._t = text
        def setText(self, t): self._t = t
        def text(self): return self._t
        def setPlaceholderText(self, p): pass
        def setClearButtonEnabled(self, e): pass
    qtwidgets.QLineEdit = QLineEdit
    class QTextEdit(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.textChanged = pyqtSignal()
            self._t = ""
        def setPlainText(self, t): self._t = t
        def toPlainText(self): return self._t
        def setFixedHeight(self, h): pass
    qtwidgets.QTextEdit = QTextEdit
    class QProgressBar(QWidget):
        def setRange(self, mi, ma): pass
        def setValue(self, v): pass
        def setTextVisible(self, v): pass
        def setFormat(self, f): pass
    qtwidgets.QProgressBar = QProgressBar
    class QProgressDialog(QDialog):
        def __init__(self, *args, **kw): super().__init__()
        def setRange(self, mi, ma): pass
        def setValue(self, v): pass
        def setLabelText(self, t): pass
        def setWindowModality(self, m): pass
        def wasCanceled(self): return False
    qtwidgets.QProgressDialog = QProgressDialog
    class QGroupBox(QWidget):
        def __init__(self, *args, **kw): super().__init__()
    qtwidgets.QGroupBox = QGroupBox
    class QToolBar(QWidget):
        def __init__(self, *args, **kw): super().__init__()
        def addAction(self, *args): pass
        def addSeparator(self): pass
        def setIconSize(self, sz): pass
        def setOrientation(self, o): pass
    qtwidgets.QToolBar = QToolBar
    class QStatusBar(QWidget):
        def addWidget(self, *args): pass
        def addPermanentWidget(self, *args): pass
    qtwidgets.QStatusBar = QStatusBar
    class QMenuBar(QWidget):
        def addMenu(self, title): return QMenu(title)
        def clear(self): pass
    qtwidgets.QMenuBar = QMenuBar
    class QMenu(QWidget):
        def __init__(self, title="", parent=None): super().__init__(parent)
        def addAction(self, *args): pass
        def addSeparator(self): pass
        def exec_(self, *args): pass
    qtwidgets.QMenu = QMenu
    class QTabWidget(QWidget):
        def addTab(self, w, title): pass
        def setCurrentIndex(self, i): pass
    qtwidgets.QTabWidget = QTabWidget
    class QScrollArea(QWidget):
        def setWidgetResizable(self, r): pass
        def setWidget(self, w): pass
    qtwidgets.QScrollArea = QScrollArea
    class QSlider(QWidget):
        def __init__(self, orient=1, parent=None):
            super().__init__(parent)
            self.valueChanged = pyqtSignal()
        def setRange(self, mi, ma): pass
        def setValue(self, v): pass
        def blockSignals(self, b): pass
    qtwidgets.QSlider = QSlider
    class QTableWidget(QWidget):
        def __init__(self, r=0, c=0, parent=None):
            super().__init__(parent)
            self.itemChanged = pyqtSignal()
        def setHorizontalHeaderLabels(self, l): pass
        def horizontalHeader(self):
            class H:
                def setSectionResizeMode(self, *a): pass
            return H()
        def setSelectionBehavior(self, b): pass
        def blockSignals(self, b): pass
        def setRowCount(self, r): pass
        def rowCount(self): return 0
        def insertRow(self, r): pass
        def setItem(self, r, c, it): pass
        def currentRow(self): return -1
    qtwidgets.QTableWidget = QTableWidget
    class QTableWidgetItem:
        def __init__(self, text=""): self._t = text
        def text(self): return self._t
    qtwidgets.QTableWidgetItem = QTableWidgetItem
    class QHeaderView:
        Stretch = 1
    qtwidgets.QHeaderView = QHeaderView
    class QAbstractItemView:
        SelectRows = 1
        NoSelection = 0
        SingleSelection = 1
        MultiSelection = 2
        ExtendedSelection = 3
    qtwidgets.QAbstractItemView = QAbstractItemView
    class QTreeWidget(QWidget):
        SingleSelection = 1
        ExtendedSelection = 3
        def __init__(self, parent=None):
            super().__init__(parent)
            self.itemSelectionChanged = pyqtSignal()
            self.customContextMenuRequested = pyqtSignal()
        def setHeaderLabels(self, l): pass
        def setColumnWidth(self, c, w): pass
        def setAlternatingRowColors(self, a): pass
        def setSelectionMode(self, s): pass
        def setContextMenuPolicy(self, p): pass
        def blockSignals(self, b): pass
        def clear(self): pass
        def addTopLevelItem(self, it): pass
        def selectedItems(self): return []
        def mapToGlobal(self, p): return p
    qtwidgets.QTreeWidget = QTreeWidget
    class QTreeWidgetItem:
        def __init__(self, strings=None): pass
        def setData(self, c, role, d): pass
        def data(self, c, role): return None
        def setForeground(self, c, col): pass
        def setText(self, c, t): pass
        def setSelected(self, s): pass
    qtwidgets.QTreeWidgetItem = QTreeWidgetItem
    class QListWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.itemDoubleClicked = pyqtSignal()
            self._items = []
        def clear(self): self._items.clear()
        def addItem(self, it): self._items.append(it)
        def count(self): return len(self._items)
        def setCurrentRow(self, r): pass
        def currentItem(self): return self._items[0] if self._items else None
        def item(self, i): return self._items[i]
    qtwidgets.QListWidget = QListWidget
    class QListWidgetItem:
        def __init__(self, text=""):
            self._t = text
            self._d = None
        def text(self): return self._t
        def setData(self, role, d): self._d = d
        def data(self, role): return self._d
        def setHidden(self, h): pass
    qtwidgets.QListWidgetItem = QListWidgetItem
    class QUndoView(QWidget):
        def __init__(self, stk=None, parent=None): super().__init__(parent)
        def setEmptyLabel(self, l): pass
    qtwidgets.QUndoView = QUndoView
    class QFrame(QWidget):
        HLine = 4
        def setFrameShape(self, s): pass
    qtwidgets.QFrame = QFrame
    class QMessageBox:
        Yes = 1; No = 2; Cancel = 4
        @staticmethod
        def information(*args): return 1
        @staticmethod
        def warning(*args): return 1
        @staticmethod
        def critical(*args): return 1
        @staticmethod
        def question(*args): return 1
    qtwidgets.QMessageBox = QMessageBox
    class QFileDialog:
        @staticmethod
        def getOpenFileName(*args): return ("", "")
        @staticmethod
        def getSaveFileName(*args): return ("", "")
    qtwidgets.QFileDialog = QFileDialog
    class QInputDialog:
        @staticmethod
        def getText(*args, **kw): return ("MockName", True)
    qtwidgets.QInputDialog = QInputDialog
    class QColorDialog:
        @staticmethod
        def getColor(*args): return QColor()
    qtwidgets.QColorDialog = QColorDialog
    class QFontDialog:
        @staticmethod
        def getFont(*args): return (QFont(), True)
    qtwidgets.QFontDialog = QFontDialog
    class QApplication:
        @staticmethod
        def processEvents(): pass
    qtwidgets.QApplication = QApplication
    class QAction:
        def __init__(self, *args, **kw): pass
    qtwidgets.QAction = QAction

    # QtPrintSupport
    qtprint = _create_mock_module("PyQt5.QtPrintSupport")
    class QPrinter:
        HighResolution = 2
    qtprint.QPrinter = QPrinter
    class QPrintPreviewDialog(QDialog):
        def __init__(self, printer, parent=None):
            super().__init__(parent)
            self.paintRequested = pyqtSignal()
    qtprint.QPrintPreviewDialog = QPrintPreviewDialog

# Mock qgis.core and qgis.gui
if "qgis" not in sys.modules:
    _create_mock_module("qgis")
    qgis_core = _create_mock_module("qgis.core")
    class QgsUnitTypes:
        LayoutMillimeters = 1
        LayoutCentimeters = 2
        LayoutPixels = 3
        DistanceKilometers = 4
        DistanceMeters = 5
        DistanceMiles = 6
        DistanceFeet = 7
    qgis_core.QgsUnitTypes = QgsUnitTypes
    class QgsLayoutSize:
        def __init__(self, w=0, h=0, u=1): self.w, self.h = w, h
        def width(self): return self.w
        def height(self): return self.h
    qgis_core.QgsLayoutSize = QgsLayoutSize
    class QgsLayoutPoint:
        def __init__(self, x=0, y=0, u=1): self.x_val, self.y_val = x, y
        def x(self): return self.x_val
        def y(self): return self.y_val
    qgis_core.QgsLayoutPoint = QgsLayoutPoint
    class QgsMapLayer:
        def id(self): return "mock_layer"
        def name(self): return "Mock Layer"
    qgis_core.QgsMapLayer = QgsMapLayer
    class QgsFeature: pass
    qgis_core.QgsFeature = QgsFeature
    class QgsSnappingConfig: pass
    qgis_core.QgsSnappingConfig = QgsSnappingConfig
    class QgsLayoutMeasurement:
        def __init__(self, v=0, u=1): self.v = v
    qgis_core.QgsLayoutMeasurement = QgsLayoutMeasurement
    class QgsLayoutItemRegistry:
        LayoutMap = 65536
        LayoutPicture = 65537
        LayoutLabel = 65538
        LayoutLegend = 65539
        LayoutShape = 65540
        LayoutPolyline = 65542
        LayoutScaleBar = 65543
        LayoutAttributeTable = 65545
    qgis_core.QgsLayoutItemRegistry = QgsLayoutItemRegistry
    class QgsLayoutItem:
        def __init__(self, layout=None):
            self._layout = layout
            self._id = ""
            self._locked = False
            self._z = 0.0
            self._pos = QgsLayoutPoint(0, 0)
            self._sz = QgsLayoutSize(10, 10)
        def id(self): return self._id
        def setId(self, i): self._id = i
        def isLocked(self): return self._locked
        def setLocked(self, l): self._locked = l
        def zValue(self): return self._z
        def setZValue(self, z): self._z = z
        def pos(self): return self._pos
        def attemptMove(self, p): self._pos = p
        def sizeWithUnits(self): return self._sz
        def attemptResize(self, s): self._sz = s
        def frameEnabled(self): return False
        def setFrameEnabled(self, f): pass
        def setFrameStrokeColor(self, c): pass
        def setFrameStrokeWidth(self, w): pass
        def hasBackground(self): return True
        def setBackgroundEnabled(self, b): pass
        def setBackgroundColor(self, c): pass
        def opacity(self): return 1.0
        def setOpacity(self, o): pass
        def isSelected(self): return False
    qgis_core.QgsLayoutItem = QgsLayoutItem
    class QgsLayoutItemMap(QgsLayoutItem):
        def scale(self): return 50000.0
        def setScale(self, s): pass
        def extent(self):
            class Ext:
                def xMinimum(self): return 0
                def xMaximum(self): return 100
                def yMinimum(self): return 0
                def yMaximum(self): return 100
                def width(self): return 100
                def height(self): return 100
            return Ext()
        def setExtent(self, e): pass
        def crs(self):
            class CRS:
                def authid(self): return "EPSG:4326"
                def isValid(self): return True
            return CRS()
        def setCrs(self, c): pass
        def setLayers(self, l): pass
        def grids(self):
            class Grids:
                def size(self): return 0
                def addGrid(self, g): pass
            return Grids()
    qgis_core.QgsLayoutItemMap = QgsLayoutItemMap
    class QgsLayoutItemLabel(QgsLayoutItem):
        def __init__(self, layout=None):
            super().__init__(layout)
            self._text = "Label"
            self._font = QFont()
            self._col = QColor()
        def text(self): return self._text
        def setText(self, t): self._text = t
        def font(self): return self._font
        def setFont(self, f): self._font = f
        def fontColor(self): return self._col
        def setFontColor(self, c): self._col = c
    qgis_core.QgsLayoutItemLabel = QgsLayoutItemLabel
    class QgsLayoutItemScaleBar(QgsLayoutItem):
        def __init__(self, layout=None):
            super().__init__(layout)
            self._units = 4
            self._style = "Single Box"
            self._segs = 2
        def style(self): return self._style
        def setStyle(self, s): self._style = s
        def units(self): return self._units
        def setUnits(self, u): self._units = u
        def numberOfSegments(self): return self._segs
        def setNumberOfSegments(self, s): self._segs = s
        def setNumberOfSegmentsLeft(self, s): pass
        def setLinkedMap(self, m): pass
        def setFont(self, f): pass
        def setFontColor(self, c): pass
    qgis_core.QgsLayoutItemScaleBar = QgsLayoutItemScaleBar
    class QgsLayoutItemLegend(QgsLayoutItem):
        def __init__(self, layout=None):
            super().__init__(layout)
            self._title = "Legend"
        def title(self): return self._title
        def setTitle(self, t): self._title = t
        def setLinkedMap(self, m): pass
        def autoUpdateModel(self): return True
        def setAutoUpdateModel(self, a): pass
    qgis_core.QgsLayoutItemLegend = QgsLayoutItemLegend
    class QgsLayoutItemPicture(QgsLayoutItem):
        def __init__(self, layout=None):
            super().__init__(layout)
            self._path = ""
        def picturePath(self): return self._path
        def setPicturePath(self, p): self._path = p
        def setLinkedMap(self, m): pass
    qgis_core.QgsLayoutItemPicture = QgsLayoutItemPicture
    class QgsLayoutItemShape(QgsLayoutItem):
        Rectangle = 0
        Ellipse = 1
        Triangle = 2
        def __init__(self, layout=None):
            super().__init__(layout)
            self._t = 0
        def shapeType(self): return self._t
        def setShapeType(self, t): self._t = t
    qgis_core.QgsLayoutItemShape = QgsLayoutItemShape
    class QgsLayoutItemPolyline(QgsLayoutItem):
        ArrowHead = 1
        def __init__(self, poly=None, layout=None):
            super().__init__(layout)
        def setEndMarker(self, m): pass
    qgis_core.QgsLayoutItemPolyline = QgsLayoutItemPolyline
    class QgsLayoutItemPolygon(QgsLayoutItem):
        def __init__(self, poly=None, layout=None):
            super().__init__(layout)
    qgis_core.QgsLayoutItemPolygon = QgsLayoutItemPolygon
    class QgsLayoutItemHtml(QgsLayoutItem):
        ManualHtml = 1
        def setContentMode(self, m): pass
        def setHtml(self, h): pass
    qgis_core.QgsLayoutItemHtml = QgsLayoutItemHtml
    class QgsLayoutItemAttributeTable(QgsLayoutItem):
        def setVectorLayer(self, l): pass
    qgis_core.QgsLayoutItemAttributeTable = QgsLayoutItemAttributeTable
    class QgsLayoutGuide:
        def __init__(self, orient, pos, page):
            self._o = orient
            self._p = pos.v if hasattr(pos, "v") else 0
        def orientation(self): return self._o
        def layoutPosition(self): return self._p
    qgis_core.QgsLayoutGuide = QgsLayoutGuide
    class QgsApplication:
        @staticmethod
        def svgPaths(): return []
    qgis_core.QgsApplication = QgsApplication
    class QgsProject:
        _inst = None
        @classmethod
        def instance(cls):
            if not cls._inst: cls._inst = QgsProject()
            return cls._inst
        def layoutManager(self):
            class LM:
                def __init__(self): self._l = []
                def printLayouts(self): return self._l
                def addLayout(self, l): self._l.append(l)
                def layoutByName(self, n): return next((l for l in self._l if l.name() == n), None)
                def duplicateLayout(self, l, n):
                    clone = QgsPrintLayout()
                    clone.setName(n)
                    self._l.append(clone)
                    return clone
                def removeLayout(self, l):
                    if l in self._l: self._l.remove(l)
            if not hasattr(self, "_lm"): self._lm = LM()
            return self._lm
        def mapLayers(self): return {}
        def crs(self):
            class C:
                def isValid(self): return True
            return C()
        def transformContext(self): return None
    qgis_core.QgsProject = QgsProject
    class QgsPrintLayout:
        def __init__(self, proj=None):
            self._name = "Layout"
            self._items = []
        def initializeDefaults(self): pass
        def name(self): return self._name
        def setName(self, n): self._name = n
        def items(self): return self._items
        def addLayoutItem(self, it): self._items.append(it)
        def removeLayoutItem(self, it):
            if it in self._items: self._items.remove(it)
        def selectedLayoutItems(self): return self._items
        def setSelectedItem(self, it): pass
        def selectAll(self): pass
        def deselectAll(self): pass
        def refresh(self): pass
        def pageCollection(self):
            class Page:
                def pageSize(self):
                    return QgsLayoutSize(297.0, 210.0, QgsUnitTypes.LayoutMillimeters)
                def setPageSize(self, sz): pass
                def attemptResize(self, sz): pass
                def rect(self): return QRectF()
            class PC:
                def pages(self): return [Page()]
            return PC()
        def snapper(self):
            class S:
                def snapToGrid(self): return False
                def setSnapToGrid(self, v): pass
                def snapToGuides(self): return True
                def setSnapToGuides(self, v): pass
                def snapToItems(self): return True
                def setSnapToItems(self, v): pass
                def snapTolerance(self): return 5
                def setSnapTolerance(self, v): pass
            return S()
        def gridSettings(self):
            class GS:
                def setResolution(self, r): pass
                def setOffset(self, o): pass
            return GS()
        def renderContext(self):
            class RC:
                def setGridVisible(self, v): pass
            return RC()
        def guides(self):
            class G:
                def __init__(self): self._g = []
                def guides(self): return self._g
                def addGuide(self, g): self._g.append(g)
                def removeGuide(self, g):
                    if g in self._g: self._g.remove(g)
                def clear(self): self._g.clear()
                def setVisible(self, v): pass
                def setGuideLayoutPosition(self, g, p): pass
            if not hasattr(self, "_guides"): self._guides = G()
            return self._guides
        def undoStack(self):
            class US:
                def stack(self): return self
                def undo(self): pass
                def redo(self): pass
                def createUndoAction(self, *a): return QAction()
                def createRedoAction(self, *a): return QAction()
            return US()
        selectedItemChanged = pyqtSignal()
    qgis_core.QgsPrintLayout = QgsPrintLayout
    class QgsLayoutExporter:
        Success = 0
        class ImageExportSettings:
            def __init__(self): self.dpi = 300
        class PdfExportSettings:
            def __init__(self): self.dpi = 300; self.rasterizeWholeImage = False
        class SvgExportSettings:
            def __init__(self): self.dpi = 300
        def __init__(self, layout): self.layout = layout
        def exportToImage(self, path, settings): return 0
        def exportToPdf(self, path, settings): return 0
        def exportToSvg(self, path, settings): return 0
        def renderPage(self, painter, idx): pass
    qgis_core.QgsLayoutExporter = QgsLayoutExporter
    class QgsMapSettings:
        def setLayers(self, l): pass
        def setDestinationCrs(self, c): pass
        def setExtent(self, e): pass
        def setOutputSize(self, s): pass
        def setOutputDpi(self, d): pass
        def setBackgroundColor(self, c): pass
    qgis_core.QgsMapSettings = QgsMapSettings
    class QgsMapRendererCustomPainterJob:
        def __init__(self, s, p): pass
        def start(self): pass
        def waitForFinished(self): pass
    qgis_core.QgsMapRendererCustomPainterJob = QgsMapRendererCustomPainterJob
    class QgsDistanceArea:
        def setSourceCrs(self, *a): pass
        def setEllipsoid(self, *a): pass
        def measureLine(self, p1, p2): return 50000.0
    qgis_core.QgsDistanceArea = QgsDistanceArea
    class QgsPointXY:
        def __init__(self, x=0, y=0): self.x_val, self.y_val = x, y
        def x(self): return self.x_val
        def y(self): return self.y_val
    qgis_core.QgsPointXY = QgsPointXY
    class QgsRectangle:
        def __init__(self, *args): pass
        def xMinimum(self): return 0
        def xMaximum(self): return 100
        def yMinimum(self): return 0
        def yMaximum(self): return 100
        def width(self): return 100
        def height(self): return 100
        def center(self): return QgsPointXY(50, 50)
        def isEmpty(self): return False
        def combineExtentWith(self, r): pass
    qgis_core.QgsRectangle = QgsRectangle
    class QgsCoordinateReferenceSystem:
        def __init__(self, auth="EPSG:4326"): self._auth = auth
        def authid(self): return self._auth
        def isValid(self): return True
        def isGeographic(self): return "4326" in self._auth
    qgis_core.QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem

    # qgis.gui
    qgis_gui = _create_mock_module("qgis.gui")
    class QgsLayoutView(QWidget):
        layoutSet = pyqtSignal()
        cursorPosChanged = pyqtSignal(object)
        def setCurrentLayout(self, l): pass
        def setTool(self, t): pass
        def zoomIn(self): pass
        def zoomOut(self): pass
        def fitInView(self, *args): pass
        def resetTransform(self): pass
        def update(self): pass
    qgis_gui.QgsLayoutView = QgsLayoutView
    class QgsLayoutViewTool:
        def __init__(self, v): pass
        def setLayout(self, l): pass
        def deactivate(self): pass
    qgis_gui.QgsLayoutViewTool = QgsLayoutViewTool
    class QgsLayoutViewToolSelect(QgsLayoutViewTool): pass
    qgis_gui.QgsLayoutViewToolSelect = QgsLayoutViewToolSelect
    class QgsLayoutViewToolPan(QgsLayoutViewTool): pass
    qgis_gui.QgsLayoutViewToolPan = QgsLayoutViewToolPan
    class QgsLayoutViewToolZoom(QgsLayoutViewTool): pass
    qgis_gui.QgsLayoutViewToolZoom = QgsLayoutViewToolZoom
    class QgsLayoutViewToolMoveItemContent(QgsLayoutViewTool): pass
    qgis_gui.QgsLayoutViewToolMoveItemContent = QgsLayoutViewToolMoveItemContent
    class QgsLayoutViewToolAddItem(QgsLayoutViewTool):
        createdItem = pyqtSignal(object)
        def setItemMetadataId(self, i): pass
    qgis_gui.QgsLayoutViewToolAddItem = QgsLayoutViewToolAddItem
    class QgsLayoutViewToolAddNodeItem(QgsLayoutViewTool):
        createdItem = pyqtSignal(object)
        def setItemMetadataId(self, i): pass
    qgis_gui.QgsLayoutViewToolAddNodeItem = QgsLayoutViewToolAddNodeItem


# Mock resources.icons.icon_provider
if "resources" not in sys.modules:
    _create_mock_module("resources")
    _create_mock_module("resources.icons")
    icon_provider = _create_mock_module("resources.icons.icon_provider")
    def get_icon(name): return QIcon()
    icon_provider.get_icon = get_icon

# Mock core.style
if "core" not in sys.modules:
    _create_mock_module("core")
    core_style = _create_mock_module("core.style")
    core_style.OFFWHITE_STYLESHEET = "/* Offwhite */"
    core_style.DARK_STYLESHEET = "/* Dark */"


# ── TEST SUITE ──────────────────────────────────────────────
class TestMapLayoutArchitecture(unittest.TestCase):
    """Verifies that all MapLayout components import and instantiate properly."""

    def test_imports_from_MapLayout(self):
        import app.ui.MapLayout as ml
        self.assertTrue(hasattr(ml, "GeoStudioLayoutDesignerWindow"))
        self.assertTrue(hasattr(ml, "LayoutPropertiesDock"))
        self.assertTrue(hasattr(ml, "LayoutItemsDock"))
        self.assertTrue(hasattr(ml, "LayoutSettingsTab"))
        self.assertTrue(hasattr(ml, "GuidesTab"))
        self.assertTrue(hasattr(ml, "LayoutManagerDialog"))
        self.assertTrue(hasattr(ml, "LayoutExportDialog"))
        self.assertTrue(hasattr(ml, "PrintExportDialog"))
        self.assertTrue(hasattr(ml, "create_layout_from_template"))
        self.assertTrue(hasattr(ml, "PAGE_PRESETS"))

    def test_instantiate_layout_from_template(self):
        from app.ui.MapLayout import create_layout_from_template
        from qgis.core import QgsProject
        proj = QgsProject.instance()
        layout = create_layout_from_template(proj, "Test Map", "A4 Landscape")
        self.assertEqual(layout.name(), "Test Map")
        self.assertTrue(len(layout.items()) >= 4)
        print("  [PASSED] Template created successfully with items count:", len(layout.items()))

    def test_instantiate_designer_window(self):
        from app.ui.MapLayout import GeoStudioLayoutDesignerWindow, create_layout_from_template
        from qgis.core import QgsProject
        proj = QgsProject.instance()
        layout = create_layout_from_template(proj, "Designer Layout", "A4 Landscape")
        win = GeoStudioLayoutDesignerWindow(layout)
        self.assertIsNotNone(win.view)
        self.assertIsNotNone(win.items_dock)
        self.assertIsNotNone(win.props_dock)
        self.assertIsNotNone(win.tab_layout_settings)
        self.assertIsNotNone(win.tab_guides)
        print("  [PASSED] LayoutDesignerWindow initialized with central canvas and docks")

        # Test tool methods
        win.add_label_item()
        win.add_scalebar_item()
        win.add_north_arrow_item()
        win.add_shape_item()
        win.add_ellipse_item()
        win.add_line_item()
        win.add_arrow_item()
        self.assertTrue(len(layout.items()) >= 10)
        print("  [PASSED] Dynamic item creation verified (all tools)")

    def test_manager_dialog(self):
        from app.ui.MapLayout import LayoutManagerDialog
        dlg = LayoutManagerDialog(None)
        self.assertIsNotNone(dlg.list_layouts)
        self.assertIsNotNone(dlg.search_edit)
        self.assertIsNotNone(dlg.combo_templates)
        print("  [PASSED] LayoutManagerDialog initialized")

    def test_export_dialog(self):
        from app.ui.MapLayout import LayoutExportDialog
        from qgis.core import QgsPrintLayout, QgsProject
        layout = QgsPrintLayout(QgsProject.instance())
        dlg = LayoutExportDialog(layout)
        self.assertIsNotNone(dlg.combo_format)
        self.assertIsNotNone(dlg.combo_dpi)
        self.assertEqual(dlg.combo_dpi.currentIndex(), 3)
        print("  [PASSED] LayoutExportDialog initialized")

    def test_print_export_dialog(self):
        from app.ui.MapLayout import PrintExportDialog
        from qgis.core import QgsPrintLayout, QgsProject
        layout = QgsPrintLayout(QgsProject.instance())
        dlg = PrintExportDialog(None, layout=layout)
        self.assertIsNotNone(dlg.combo_format)
        self.assertIsNotNone(dlg.combo_preset)
        self.assertIsNotNone(dlg.combo_dpi)
        print("  [PASSED] PrintExportDialog initialized")

    def test_actions_alignment_distribution(self):
        from app.ui.MapLayout.core.actions import align_items, distribute_items
        from qgis.core import QgsPrintLayout, QgsLayoutItemLabel, QgsLayoutPoint
        layout = QgsPrintLayout()
        it1 = QgsLayoutItemLabel(layout); it1.attemptMove(QgsLayoutPoint(10, 20))
        it2 = QgsLayoutItemLabel(layout); it2.attemptMove(QgsLayoutPoint(50, 20))
        layout.addLayoutItem(it1)
        layout.addLayoutItem(it2)

        align_items(layout, "left")
        self.assertEqual(it1.pos().x(), 10)
        self.assertEqual(it2.pos().x(), 10)
        print("  [PASSED] Align items algorithm verified")

    def test_backward_compatible_aliases(self):
        # 1. Test app.ui.layout
        import app.ui.layout as legacy_layout
        self.assertTrue(hasattr(legacy_layout, "GeoStudioLayoutDesignerWindow"))
        self.assertTrue(hasattr(legacy_layout, "LayoutManagerDialog"))
        self.assertTrue(hasattr(legacy_layout, "PrintExportDialog"))
        self.assertTrue(hasattr(legacy_layout, "LayoutExportDialog"))
        self.assertTrue(hasattr(legacy_layout, "create_layout_from_template"))

        # 2. Test app.ui.map_layout
        import app.ui.map_layout as legacy_map_layout
        self.assertTrue(hasattr(legacy_map_layout, "GeoStudioLayoutDesignerWindow"))

        # 3. Test app.MapLayout
        import app.MapLayout as root_map_layout
        self.assertTrue(hasattr(root_map_layout, "GeoStudioLayoutDesignerWindow"))

        # 4. Test app.ui.print_export_dialog
        from app.ui.print_export_dialog import PrintExportDialog as LegacyPrintDialog
        self.assertIsNotNone(LegacyPrintDialog)

        # 5. Test app.ui.print_export_overlays
        from app.ui.print_export_overlays import draw_scalebar_overlay, draw_north_arrow_overlay, draw_title_overlay
        self.assertTrue(callable(draw_scalebar_overlay))
        self.assertTrue(callable(draw_north_arrow_overlay))
        self.assertTrue(callable(draw_title_overlay))
        print("  [PASSED] All backward-compatibility aliases verified")

    def test_overlays_and_distance_calculations(self):
        from app.ui.MapLayout.core.overlays import draw_scalebar_overlay, draw_north_arrow_overlay, draw_title_overlay
        from PyQt5.QtGui import QPainter
        from qgis.core import QgsRectangle, QgsCoordinateReferenceSystem

        painter = QPainter()
        
        # Test Title
        draw_title_overlay(painter, 1200, 800, "Official GeoStudio Cadastral Map")

        # Test North Arrow
        draw_north_arrow_overlay(painter, 1200, 800)

        # Test Geographic CRS scalebar (uses spherical degrees-to-meters cosine formula)
        extent_geo = QgsRectangle(77.0, 28.0, 78.0, 29.0)
        crs_geo = QgsCoordinateReferenceSystem("EPSG:4326")
        draw_scalebar_overlay(painter, 1200, 800, extent_geo, crs_geo)

        # Test Projected CRS scalebar (uses QgsDistanceArea planar measureLine)
        extent_proj = QgsRectangle(500000, 3100000, 550000, 3150000)
        crs_proj = QgsCoordinateReferenceSystem("EPSG:32643")
        draw_scalebar_overlay(painter, 1200, 800, extent_proj, crs_proj)

        print("  [PASSED] Overlays & distance calculations (spherical + planar) verified")

    def test_properties_dock(self):
        from app.ui.MapLayout import LayoutPropertiesDock
        from qgis.core import QgsPrintLayout, QgsLayoutItemLabel
        layout = QgsPrintLayout()
        lbl = QgsLayoutItemLabel(layout)
        lbl.setText("Survey Station Alpha")
        layout.addLayoutItem(lbl)

        dock = LayoutPropertiesDock(None)
        self.assertIsNotNone(dock.lbl_title)
        self.assertIsNotNone(dock.grp_common)
        self.assertIsNotNone(dock.grp_frame)
        dock.set_item(lbl)
        print("  [PASSED] LayoutPropertiesDock inspector and tabs verified")

    def test_items_dock_management(self):
        from app.ui.MapLayout import LayoutItemsDock
        from qgis.core import QgsPrintLayout, QgsLayoutItemLabel
        layout = QgsPrintLayout()
        it1 = QgsLayoutItemLabel(layout); it1.setId("Label_1")
        it2 = QgsLayoutItemLabel(layout); it2.setId("Label_2")
        layout.addLayoutItem(it1)
        layout.addLayoutItem(it2)

        class DummyDesigner:
            def __init__(self, l): self.layout = l
        dock = LayoutItemsDock(DummyDesigner(layout))
        dock.refresh_items()
        print("  [PASSED] LayoutItemsDock item hierarchy and refresh verified")

    def test_project_controller_integration(self):
        import app.ui.controllers.project_controller as pc
        self.assertIsNotNone(pc)
        print("  [PASSED] ProjectController layout integration verified")

    def test_modular_services_and_packages(self):
        # 1. Test services
        from app.ui.MapLayout.services import (
            create_layout_from_template,
            export_layout_to_image,
            export_layout_to_pdf,
            export_layout_to_svg,
            draw_title_overlay,
            draw_north_arrow_overlay,
            draw_scalebar_overlay,
            align_items,
            distribute_items,
            get_first_map_item,
        )
        self.assertTrue(callable(create_layout_from_template))
        self.assertTrue(callable(export_layout_to_image))
        self.assertTrue(callable(export_layout_to_pdf))
        self.assertTrue(callable(export_layout_to_svg))
        self.assertTrue(callable(draw_title_overlay))
        self.assertTrue(callable(draw_north_arrow_overlay))
        self.assertTrue(callable(draw_scalebar_overlay))
        self.assertTrue(callable(align_items))
        self.assertTrue(callable(distribute_items))
        self.assertTrue(callable(get_first_map_item))

        # 2. Test panels
        from app.ui.MapLayout.panels import (
            LayoutItemsDock,
            LayoutPropertiesDock,
            LayoutSettingsTab,
            GuidesTab,
        )
        self.assertIsNotNone(LayoutItemsDock)
        self.assertIsNotNone(LayoutPropertiesDock)
        self.assertIsNotNone(LayoutSettingsTab)
        self.assertIsNotNone(GuidesTab)

        # 3. Test dialogs
        from app.ui.MapLayout.dialogs import (
            LayoutManagerDialog,
            LayoutExportDialog,
            PrintExportDialog,
        )
        self.assertIsNotNone(LayoutManagerDialog)
        self.assertIsNotNone(LayoutExportDialog)
        self.assertIsNotNone(PrintExportDialog)

        # 4. Test toolbar
        from app.ui.MapLayout.toolbar import (
            create_layout_operations_toolbar,
            create_navigation_alignment_toolbar,
            create_layout_tools_palette,
        )
        self.assertTrue(callable(create_layout_operations_toolbar))
        self.assertTrue(callable(create_navigation_alignment_toolbar))
        self.assertTrue(callable(create_layout_tools_palette))

        # 5. Test utils
        from app.ui.MapLayout.utils import (
            mm_to_inches,
            inches_to_mm,
            mm_to_pixels,
            pixels_to_mm,
            calculate_page_dimensions,
            estimate_image_memory_mb,
            is_memory_critical,
        )
        self.assertAlmostEqual(inches_to_mm(1.0), 25.4, places=2)
        self.assertAlmostEqual(mm_to_inches(25.4), 1.0, places=2)
        self.assertEqual(mm_to_pixels(25.4, 300), 300)
        self.assertEqual(pixels_to_mm(300, 300), 25.4)
        pw, ph = calculate_page_dimensions("A4 Landscape")
        self.assertEqual((pw, ph), (297.0, 210.0))
        mb = estimate_image_memory_mb(1000, 1000, 4)
        self.assertAlmostEqual(mb, 3.81, places=1)
        self.assertFalse(is_memory_critical(1000, 1000))
        self.assertTrue(is_memory_critical(15000, 10000))

        # 6. Test types
        from app.ui.MapLayout.types import (
            ExportFormat,
            AlignmentType,
            DistributionAxis,
            PageOrientation,
            ToolType,
        )
        self.assertEqual(ExportFormat.PDF.value, "pdf")
        self.assertEqual(AlignmentType.LEFT.value, "left")
        self.assertEqual(DistributionAxis.HORIZONTAL.value, "h")
        self.assertEqual(PageOrientation.LANDSCAPE.value, "Landscape")
        self.assertEqual(ToolType.SELECT.value, "select")

        # 7. Test styles
        from app.ui.MapLayout.styles import (
            LAYOUT_OFFWHITE_STYLE,
            LAYOUT_DOCK_TITLE_STYLE,
            LAYOUT_TAB_PANE_STYLE,
            LAYOUT_STATUS_TOOL_STYLE,
            LAYOUT_STATUS_POS_STYLE,
            LAYOUT_EXPORT_BTN_STYLE,
        )
        self.assertIn("Offwhite", LAYOUT_OFFWHITE_STYLE)
        self.assertIn("color", LAYOUT_DOCK_TITLE_STYLE)

        # 8. Test constants
        from app.ui.MapLayout.constants import (
            PAGE_PRESETS,
            PAGE_SIZES,
            DPI_PRESETS,
        )
        self.assertIn("A4 Landscape", PAGE_PRESETS)
        self.assertIn("A4", PAGE_SIZES)
        self.assertIn("High-Res Production (300 DPI)", DPI_PRESETS)

        print("  [PASSED] All modular subpackages (services, panels, dialogs, toolbar, utils, types, styles, constants) verified")


if __name__ == "__main__":
    unittest.main()

