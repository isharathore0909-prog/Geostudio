# -*- coding: utf-8 -*-
"""
GeoStudio - Base Theme QSS Styles (Global, Menus, Toolbars, Docks, Tabs, Scrollbars)
"""

from .tokens import FONT_FAMILY, MONO_FONT


def get_theme_base() -> str:
    return f"""
/* ── Global ─────────────────────────────────────────────────── */
QMainWindow, QDialog, QWidget {{
    background-color: #f8fafc;
    color: #0f172a;
    font-family: {FONT_FAMILY};
    font-size: 12px;
}}

/* ── Menu Bar ────────────────────────────────────────────────── */
QMenuBar {{
    background-color: #ffffff;
    color: #334155;
    border-bottom: 1px solid #e2e8f0;
    padding: 3px 6px;
    font-size: 12px;
    font-weight: 500;
}}
QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 4px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: #f1f5f9;
    color: #0f172a;
}}
QMenuBar::item:pressed {{
    background-color: #e2e8f0;
}}

/* ── Floating Menus ──────────────────────────────────────────── */
QMenu {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 0px;
}}
QMenu::item {{
    background-color: transparent;
    color: #1e293b;
    padding: 6px 36px 6px 32px;
    margin: 1px 4px;
    font-size: 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: #e2e8f0;
    color: #0f172a;
    font-weight: 600;
}}
QMenu::item:disabled {{
    color: #94a3b8;
}}
QMenu::icon {{
    position: absolute;
    left: 8px;
    top: 5px;
}}
QMenu::separator {{
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 8px 4px 30px;
}}

/* ── Toolbars (Grouped Ribbon Containers) ────────────────────── */
QToolBar {{
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    spacing: 3px;
    padding: 3px 4px;
}}
QToolBar::separator {{
    background: #e2e8f0;
    width: 1px;
    margin: 4px 6px;
}}
QToolBar::handle:horizontal {{
    background: #cbd5e1;
    width: 4px;
    margin: 6px 2px;
    border-radius: 2px;
}}
QToolButton {{
    background: transparent;
    color: #334155;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 4px 6px;
    margin: 1px 1px;
    font-size: 11px;
    font-weight: 500;
}}
QToolButton:hover {{
    background: #f1f5f9;
    color: #0f172a;
    border: 1px solid #cbd5e1;
}}
QToolButton:pressed {{
    background: #e2e8f0;
    border: 1px solid #94a3b8;
}}
QToolButton:checked {{
    background: #e2e8f0;
    color: #0f172a;
    border: 1px solid #475569;
    font-weight: 600;
}}
QToolButton[popupMode="1"], QToolButton[popupMode="2"] {{
    padding-right: 8px;
}}

/* ── Dock Widgets (Panels) ───────────────────────────────────── */
QDockWidget {{
    color: #0f172a;
    font-weight: 600;
    font-size: 12px;
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background: #f8fafc;
    color: #0f172a;
    padding: 7px 12px;
    border-bottom: 1px solid #e2e8f0;
    border-top: 1px solid #e2e8f0;
    text-align: left;
    font-weight: 700;
}}

/* ── Scroll Bars ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: #f8fafc;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1;
    min-height: 24px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: #f8fafc;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: #cbd5e1;
    min-width: 24px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Tabs (Tab Widget) ───────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid #e2e8f0;
    background: #ffffff;
    border-radius: 6px;
    top: -1px;
}}
QTabWidget::tab-bar {{
    left: 6px;
}}
QTabBar::tab {{
    background: #f1f5f9;
    color: #64748b;
    border: 1px solid #e2e8f0;
    padding: 7px 18px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-right: 4px;
    margin-top: 2px;
    font-size: 11px;
    font-weight: 500;
    min-width: 68px;
}}
QTabBar::tab:selected {{
    background: #ffffff;
    color: #0f172a;
    font-weight: 700;
    border-bottom-color: #ffffff;
    margin-top: 0px;
}}
QTabBar::tab:hover:!selected {{
    background: #e2e8f0;
    color: #0f172a;
}}
"""
