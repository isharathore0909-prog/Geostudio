# -*- coding: utf-8 -*-
"""
GeoStudio Python Pipeline - Map Layout & Cartography Workstation Tasks
High-performance warm-instance server and layout designer launcher.
"""

import os
import sys
import json
import socket
import queue
import threading
from common import report_progress, report_result

LAYOUT_SERVER_PORT = 48199
_ipc_queue = queue.Queue()


def _bring_window_to_front(window):
    """Ensures the Qt window is restored, shown, raised, and given foreground focus on Windows."""
    try:
        from PyQt5.QtCore import Qt
        window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()
    except Exception:
        try:
            window.show()
            window.raise_()
        except Exception:
            pass

    try:
        import ctypes
        hwnd = int(window.winId())
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _send_ipc_command(cmd: str, file_path: str = None, timeout: float = 0.35) -> bool:
    """Attempts to send command to an already running warm Map Layout instance."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", LAYOUT_SERVER_PORT))
        payload = json.dumps({"cmd": cmd, "file": file_path or ""}) + "\n"
        s.sendall(payload.encode("utf-8"))
        resp = s.recv(1024)
        s.close()
        return bool(resp)
    except Exception:
        return False


def _start_ipc_server(designer, app):
    """Background TCP server feeding incoming requests into the thread-safe queue."""
    from PyQt5.QtCore import QTimer

    def server_thread():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", LAYOUT_SERVER_PORT))
            server.listen(5)
        except Exception as e:
            print(f"[MapLayout IPC Server] Port {LAYOUT_SERVER_PORT} unavailable: {e}")
            return

        while True:
            try:
                conn, _ = server.accept()
                data = b""
                while not data.endswith(b"\n"):
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk

                if not data:
                    conn.close()
                    continue

                msg = json.loads(data.decode("utf-8").strip())
                cmd = msg.get("cmd", "")
                target_file = msg.get("file", "")

                if cmd == "open":
                    _ipc_queue.put(("open", target_file))
                    conn.sendall(b'{"status":"ok"}\n')
                elif cmd == "ping":
                    conn.sendall(b'{"status":"pong"}\n')
                elif cmd == "shutdown":
                    _ipc_queue.put(("shutdown", ""))
                    conn.sendall(b'{"status":"shutting_down"}\n')
                    conn.close()
                    break
                else:
                    conn.sendall(b'{"status":"unknown"}\n')
                conn.close()
            except Exception:
                pass

        try:
            server.close()
        except Exception:
            pass

    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

    # Qt main-thread event loop poller for zero-lag thread-safe window actions
    def _poll_queue():
        while not _ipc_queue.empty():
            try:
                action, val = _ipc_queue.get_nowait()
                if action == "open":
                    if hasattr(designer, "load_layer") and val:
                        designer.load_layer(val)
                    _bring_window_to_front(designer)
                elif action == "shutdown":
                    designer._keep_warm = False
                    designer.close()
                    app.quit()
            except Exception as ex:
                print(f"[MapLayout Queue Error] {ex}")

    queue_timer = QTimer(designer)
    queue_timer.timeout.connect(_poll_queue)
    queue_timer.start(50)  # Check every 50ms


def task_launch_map_layout(args):
    """Launches the interactive QGIS Map Layout & Cartography Designer workstation."""
    file_path = args.input if (args.input and os.path.exists(args.input)) else None

    try:
        report_progress(10, "Initializing Map Layout Designer...")

        # Configure GDAL memory cache and optimized I/O for BigTIFF
        try:
            from osgeo import gdal
            gdal.SetCacheMax(1024 * 1024 * 1024)  # 1GB RAM cache
            gdal.SetConfigOption("GDAL_CACHEMAX", "1024")
            gdal.SetConfigOption("GDAL_NUM_THREADS", "ALL_CPUS")
            gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
            gdal.SetConfigOption("VSI_CACHE", "TRUE")
            gdal.SetConfigOption("VSI_CACHE_SIZE", "67108864")
        except Exception:
            pass

        from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsPrintLayout
        from ui.MapLayout import GeoStudioLayoutDesignerWindow

        app = QgsApplication.instance()
        if app is None:
            argv = [sys.argv[0].encode("utf-8")] if sys.argv else [b"GeoStudio"]
            app = QgsApplication(argv, True)
            app.initQgis()
            try:
                QgsApplication.setMaxThreads(max(2, (os.cpu_count() or 4) - 1))
            except Exception:
                pass

        prj = QgsProject.instance()
        if file_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".tif", ".tiff", ".img", ".asc", ".vrt"):
                rl = QgsRasterLayer(file_path, base_name)
                if rl.isValid():
                    prj.addMapLayer(rl)
                    if rl.crs().isValid():
                        prj.setCrs(rl.crs())
            elif ext in (".shp", ".geojson", ".gpkg", ".kml"):
                vl = QgsVectorLayer(file_path, base_name, "ogr")
                if vl.isValid():
                    prj.addMapLayer(vl)
                    if vl.crs().isValid():
                        prj.setCrs(vl.crs())

        report_progress(60, "Composing cartographic canvas...")
        if not prj.crs().isValid():
            from qgis.core import QgsCoordinateReferenceSystem
            prj.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))

        # Initialize layout
        layout = QgsPrintLayout(prj)
        layout.initializeDefaults()
        layout.setName("Map Layout 1")
        prj.layoutManager().addLayout(layout)

        designer = GeoStudioLayoutDesignerWindow(layout=layout)
        designer._keep_warm = False

        _bring_window_to_front(designer)

        report_progress(100, "Map Layout Designer active")
        report_result(True, {"message": "Map Layout Designer Launched", "file": file_path})
        sys.exit(app.exec_())
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            qapp = QApplication.instance() or QApplication([sys.argv[0]])
            QMessageBox.critical(None, "GeoStudio Map Layout Error", f"Failed to open Map Layout:\n\n{e}\n\n{err}")
        except Exception:
            pass
        report_result(False, {}, str(e))
        sys.exit(1)
