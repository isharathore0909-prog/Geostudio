# -*- coding: utf-8 -*-
"""
GeoStudio - Standalone GIS Application
Entry point: bootstraps QGIS engine then launches the main window.
"""

import sys
import os

# ── Bootstrap QGIS environment ──────────────────────────────────────────────
QGIS_ROOT = r"C:\Program Files\QGIS 3.40.14"
QGIS_APP  = os.path.join(QGIS_ROOT, "apps", "qgis-ltr")
QGIS_PY   = os.path.join(QGIS_ROOT, "apps", "Python312")

# Add DLL directories for Windows Python 3.8+
if hasattr(os, 'add_dll_directory'):
    for dll_dir in [
        os.path.join(QGIS_ROOT, "bin"),
        os.path.join(QGIS_APP, "bin"),
        os.path.join(QGIS_ROOT, "apps", "Qt5", "bin"),
        QGIS_PY,
        os.path.join(QGIS_PY, "Scripts"),
    ]:
        if os.path.exists(dll_dir):
            try:
                os.add_dll_directory(dll_dir)
            except Exception:
                pass

# Add QGIS Python bindings and plugins to path
for p in [
    os.path.join(QGIS_APP, "python"),
    os.path.join(QGIS_APP, "python", "plugins"),
    os.path.join(QGIS_PY, "Lib", "site-packages"),
    os.path.join(QGIS_PY, "Lib"),
    os.path.dirname(os.path.abspath(__file__)),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set QGIS prefix path & environment variables
os.environ["QGIS_PREFIX_PATH"]  = QGIS_APP
os.environ["GDAL_DATA"]         = os.path.join(QGIS_ROOT, "share", "gdal")
os.environ["PROJ_LIB"]          = os.path.join(QGIS_ROOT, "share", "proj")
os.environ["QT_PLUGIN_PATH"]    = os.path.join(QGIS_ROOT, "apps", "Qt5", "plugins")
os.environ["QT_LOGGING_RULES"]   = "*.debug=false;qt.qpa.*=false;qt.core.mimetype.*=false;" + os.environ.get("QT_LOGGING_RULES", "")

# ── Suppress harmless internal Qt MIME database & font warnings ───────────────
try:
    from PyQt5.QtCore import qInstallMessageHandler, QtMsgType
    def _qt_message_handler(msg_type, context, message):
        if any(s in message for s in ("QMimeDatabase", "internal MIME data", "Premature end of document", "qpa")):
            return
        if msg_type in (QtMsgType.QtFatalMsg, QtMsgType.QtCriticalMsg):
            sys.stderr.write(f"[Qt] {message}\n")
    qInstallMessageHandler(_qt_message_handler)
except Exception:
    pass

# ── Qt & QGIS Application (Single Unified Instance) ───────────────────────────
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont, QLinearGradient, QBrush, QPalette
from qgis.core import QgsApplication

# High DPI Scaling for 2K/4K Displays
try:
    from PyQt5.QtCore import Qt
    QgsApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QgsApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
except Exception:
    pass

# Create sole application object
argv_bytes = [arg.encode('utf-8') if isinstance(arg, str) else arg for arg in sys.argv] if sys.argv else [b"GeoStudio"]
app = QgsApplication(argv_bytes, True)
app.setPrefixPath(QGIS_APP, True)
app.initQgis()
app.setApplicationName("GeoStudio")
app.setOrganizationName("GeoStudio")
app.setStyle("Fusion")

# Global Palette Highlight -> Grey
pal = app.palette()
pal.setColor(QPalette.Highlight, QColor("#e2e8f0"))
pal.setColor(QPalette.HighlightedText, QColor("#0f172a"))
app.setPalette(pal)

# ── Splash Screen ─────────────────────────────────────────────────────────────
splash_pix = QPixmap(480, 280)
splash_pix.fill(QColor("#0d1b2a"))

painter = QPainter(splash_pix)
painter.setRenderHint(QPainter.Antialiasing)

gradient = QLinearGradient(0, 0, 480, 280)
gradient.setColorAt(0.0, QColor("#0d1b2a"))
gradient.setColorAt(1.0, QColor("#1a3a5c"))
painter.fillRect(0, 0, 480, 280, QBrush(gradient))

# Title
font = QFont("Segoe UI", 32, QFont.Bold)
painter.setFont(font)
painter.setPen(QColor("#4fc3f7"))
painter.drawText(40, 110, "🌍 GeoStudio")

# Subtitle
font2 = QFont("Segoe UI", 11)
painter.setFont(font2)
painter.setPen(QColor("#90caf9"))
painter.drawText(44, 140, "Standalone Geospatial Analysis System")

# Version
font3 = QFont("Segoe UI", 9)
painter.setFont(font3)
painter.setPen(QColor("#546e7a"))
painter.drawText(44, 200, "Version 1.0  ·  Powered by QGIS Engine 3.40  ·  PyQGIS")

# Loading bar background
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#1e3a5f"))
painter.drawRoundedRect(40, 230, 400, 12, 6, 6)
painter.setBrush(QColor("#4fc3f7"))
painter.drawRoundedRect(40, 230, 200, 12, 6, 6)
painter.end()

splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
splash.show()
splash.showMessage("  Initializing geospatial engine...", Qt.AlignBottom | Qt.AlignLeft, QColor("#4fc3f7"))
app.processEvents()

# ── Initialize Processing ───────────────────────────────────────────────────
try:
    import processing
    from processing.core.Processing import Processing
    Processing.initialize()
    splash.showMessage("  Building interface...", Qt.AlignBottom | Qt.AlignLeft, QColor("#a5d6a7"))
    app.processEvents()
except Exception as e:
    print(f"[Warning] Processing initialize: {e}")

# ── Launch Main Window ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.main_window import GeoStudioMainWindow

window = GeoStudioMainWindow(qgs_app=app)
window.show()

# Close splash after window shows
QTimer.singleShot(1400, splash.close)
QTimer.singleShot(1400, window.raise_)

# ── Run Event Loop ────────────────────────────────────────────────────────────
exit_code = app.exec_()

try:
    from qgis.core import QgsProject
    QgsProject.instance().clear()
except Exception:
    pass

try:
    app.exitQgis()
except Exception:
    pass

os._exit(0 if exit_code is None else exit_code)

