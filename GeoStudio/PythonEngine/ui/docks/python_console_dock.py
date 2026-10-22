# -*- coding: utf-8 -*-
"""GeoStudio - Python Console Dock."""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QTextCursor
import sys
import io
import code
import traceback


class PythonConsoleDock(QDockWidget):
    """
    Interactive Python console dock.
    Gives access to the full QGIS/PyQGIS API from inside GeoStudio.
    """

    PROMPT = ">>> "

    def __init__(self, parent=None):
        super().__init__("🐍 Python Console", parent)
        self.setObjectName("python_console_dock")
        self.setMinimumHeight(180)
        self.setMaximumHeight(380)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self._history = []
        self._history_idx = 0
        self._locals = self._build_locals()
        self._build_ui()
        self._print_banner()

    def _build_locals(self):
        """Build the namespace available in the console."""
        ns = {
            "__name__": "__geostudio_console__",
            "__doc__": "GeoStudio Python Console",
        }
        try:
            from qgis.core import QgsProject, QgsApplication, QgsVectorLayer, QgsRasterLayer
            from qgis.gui import QgsMapCanvas
            import processing
            ns.update({
                "QgsProject": QgsProject,
                "project": QgsProject.instance(),
                "QgsVectorLayer": QgsVectorLayer,
                "QgsRasterLayer": QgsRasterLayer,
                "processing": processing,
            })
        except ImportError:
            pass
        return ns

    def _build_ui(self):
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget { background: #0d1117; }
            QTextEdit { background: #0d1117; color: #e6edf3; font-family: 'Consolas', 'Courier New', monospace;
                        font-size: 11px; border: none; }
            QLineEdit { background: #161b22; color: #58a6ff; font-family: 'Consolas', 'Courier New', monospace;
                        font-size: 11px; border: 1px solid #30363d; border-radius: 3px; padding: 4px 8px; }
            QPushButton { background: #21262d; color: #58a6ff; border: 1px solid #30363d;
                          border-radius: 3px; padding: 4px 12px; font-size: 11px; }
            QPushButton:hover { background: #30363d; }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.output, 1)

        # Input row
        input_row = QHBoxLayout()
        prompt_label = QLabel(">>>")
        prompt_label.setStyleSheet("color: #58a6ff; font-family: monospace; font-weight: bold;")
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Enter Python command...")
        self.input_line.returnPressed.connect(self._run_command)
        self.input_line.installEventFilter(self)

        btn_run = QPushButton("▶ Run")
        btn_run.clicked.connect(self._run_command)
        btn_clear = QPushButton("🗑 Clear")
        btn_clear.clicked.connect(self.output.clear)

        input_row.addWidget(prompt_label)
        input_row.addWidget(self.input_line, 1)
        input_row.addWidget(btn_run)
        input_row.addWidget(btn_clear)
        layout.addLayout(input_row)

        widget.setLayout(layout)
        self.setWidget(widget)

    def _print_banner(self):
        banner = (
            '<span style="color:#58a6ff;">GeoStudio Python Console</span><br>'
            '<span style="color:#8b949e;">Python ' + sys.version.split()[0] + ' — PyQGIS 3.40</span><br>'
            '<span style="color:#8b949e;">Type Python commands. Available: QgsProject, project, processing, QgsVectorLayer, QgsRasterLayer</span><br>'
            '<span style="color:#3fb950;">Example: layers = list(project.mapLayers().values()); print(len(layers))</span><br><br>'
        )
        self.output.insertHtml(banner)

    def _run_command(self):
        cmd = self.input_line.text().strip()
        if not cmd:
            return
        self._history.append(cmd)
        self._history_idx = len(self._history)
        self.input_line.clear()

        # Print the command
        self._append(f'<span style="color:#58a6ff;">&gt;&gt;&gt; {self._escape(cmd)}</span><br>')

        # Execute
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            try:
                result = eval(compile(cmd, "<console>", "eval"), self._locals)
                if result is not None:
                    self._append(f'<span style="color:#e6edf3;">{self._escape(repr(result))}</span><br>')
            except SyntaxError:
                exec(compile(cmd, "<console>", "exec"), self._locals)
        except Exception:
            tb = traceback.format_exc()
            self._append(f'<span style="color:#f85149;">{self._escape(tb)}</span><br>')
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        out = stdout_capture.getvalue()
        err = stderr_capture.getvalue()
        if out:
            self._append(f'<span style="color:#adbac7;">{self._escape(out)}</span><br>')
        if err:
            self._append(f'<span style="color:#f85149;">{self._escape(err)}</span><br>')

        self.output.moveCursor(QTextCursor.End)

    def _append(self, html):
        self.output.moveCursor(QTextCursor.End)
        self.output.insertHtml(html)

    @staticmethod
    def _escape(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        from PyQt5.QtGui import QKeyEvent
        from PyQt5.QtCore import Qt as QtConst
        if obj == self.input_line and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == QtConst.Key_Up and self._history:
                self._history_idx = max(0, self._history_idx - 1)
                self.input_line.setText(self._history[self._history_idx])
                return True
            elif key == QtConst.Key_Down:
                self._history_idx = min(len(self._history), self._history_idx + 1)
                if self._history_idx < len(self._history):
                    self.input_line.setText(self._history[self._history_idx])
                else:
                    self.input_line.clear()
                return True
        return super().eventFilter(obj, event)
