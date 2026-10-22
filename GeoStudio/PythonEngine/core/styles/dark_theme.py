# -*- coding: utf-8 -*-
"""
GeoStudio - Slate Pro Dark Workstation Theme
"""

from .tokens import FONT_FAMILY, MONO_FONT

DARK_STYLESHEET = f"""
/* ═══════════════════════════════════════════════════════════════
   GeoStudio — Professional Slate Pro Dark Theme
   ═══════════════════════════════════════════════════════════════ */
QMainWindow, QDialog, QWidget {{
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: {FONT_FAMILY};
    font-size: 12px;
}}
QMenuBar {{
    background: #090e1a;
    color: #94a3b8;
    border-bottom: 1px solid #1e293b;
    padding: 3px 6px;
    font-size: 12px;
    font-weight: 500;
}}
QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background: #1e293b;
    color: #f8fafc;
}}
QMenu {{
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 0px;
}}
QMenu::item {{
    background-color: transparent;
    color: #e2e8f0;
    padding: 6px 36px 6px 32px;
    margin: 1px 4px;
    font-size: 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: #334155;
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: #64748b;
}}
QMenu::separator {{
    height: 1px;
    background-color: #334155;
    margin: 4px 8px 4px 30px;
}}
QToolBar {{
    background: #090e1a;
    border-bottom: 1px solid #1e293b;
    border-right: 1px solid #1e293b;
    spacing: 3px;
    padding: 3px 4px;
}}
QToolBar::separator {{
    background: #334155;
    width: 1px;
    margin: 4px 6px;
}}
QToolButton {{
    background: transparent;
    color: #94a3b8;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 4px 6px;
    margin: 1px 1px;
    font-size: 11px;
    font-weight: 500;
}}
QToolButton:hover {{
    background: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
}}
QToolButton:pressed {{
    background: #334155;
    color: #ffffff;
}}
QToolButton:checked {{
    background: #334155;
    color: #ffffff;
    border: 1px solid #64748b;
    font-weight: 600;
}}
QDockWidget {{
    color: #f8fafc;
    font-weight: 600;
    font-size: 12px;
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background: #1e293b;
    color: #e2e8f0;
    padding: 7px 12px;
    border-bottom: 1px solid #334155;
    border-top: 1px solid #334155;
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.3px;
}}
QDockWidget::close-button:hover {{ background: #7f1d1d; color: #f87171; }}
QDockWidget::float-button:hover {{ background: #334155; color: #ffffff; }}
QSplitter::handle {{ background: #1e293b; }}
QSplitter::handle:hover {{ background: #475569; }}
QScrollBar:vertical {{ background: #0f172a; width: 8px; border-radius: 4px; }}
QScrollBar::handle:vertical {{ background: #334155; min-height: 28px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: #475569; }}
QScrollBar:horizontal {{ background: #0f172a; height: 8px; border-radius: 4px; }}
QScrollBar::handle:horizontal {{ background: #334155; min-width: 28px; border-radius: 4px; }}
QScrollBar::handle:horizontal:hover {{ background: #475569; }}
QTabWidget::pane {{ border: 1px solid #334155; background: #0f172a; border-radius: 6px; }}
QTabBar::tab {{ background: #090e1a; color: #64748b; border: 1px solid #334155; padding: 6px 14px; margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
QTabBar::tab:selected {{ background: #334155; color: #ffffff; font-weight: 600; }}
QPushButton {{ background: #334155; color: #ffffff; border: none; border-radius: 5px; padding: 6px 14px; font-weight: 600; }}
QPushButton:hover {{ background: #475569; }}
QPushButton:pressed {{ background: #1e293b; }}
QPushButton:disabled {{ background: #1e293b; color: #64748b; }}
QLineEdit, QTextEdit, QPlainTextEdit {{ background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 5px 8px; }}
QLineEdit:focus, QTextEdit:focus {{ border: 1.5px solid #64748b; }}
QComboBox {{ background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 5px 8px; }}
QComboBox:focus {{ border: 1.5px solid #64748b; }}
QComboBox QAbstractItemView {{ background: #1e293b; color: #f8fafc; selection-background-color: #334155; border: 1px solid #334155; }}
QSpinBox, QDoubleSpinBox {{ background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 5px 6px; }}
QGroupBox {{ border: 1px solid #334155; border-radius: 6px; margin-top: 14px; padding: 10px 8px 8px 8px; color: #f8fafc; font-weight: 600; background: #0f172a; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 6px; background: #0f172a; }}
QListWidget, QTreeWidget, QTableWidget {{ background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; outline: none; }}
QListWidget::item:selected, QTreeWidget::item:selected {{ background: #334155; color: #ffffff; font-weight: 600; }}
QHeaderView::section {{ background: #090e1a; color: #94a3b8; border: none; border-bottom: 1px solid #334155; border-right: 1px solid #334155; padding: 6px 10px; font-weight: 600; }}
QCheckBox, QRadioButton {{ color: #94a3b8; spacing: 7px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; border: 1px solid #475569; border-radius: 3px; background: #1e293b; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: #475569; border: 1px solid #64748b; }}
QProgressBar {{ border: 1px solid #334155; border-radius: 4px; background: #1e293b; text-align: center; color: #e2e8f0; font-size: 11px; }}
QProgressBar::chunk {{ background: #475569; border-radius: 3px; }}
QStatusBar {{ background-color: #090e1a; color: #94a3b8; border-top: 1px solid #1e293b; min-height: 26px; }}
QToolTip {{ background-color: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 5px; padding: 6px 10px; font-size: 11px; font-family: {FONT_FAMILY}; }}
"""
