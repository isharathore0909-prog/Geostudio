# -*- coding: utf-8 -*-
"""
GeoStudio - Controls Theme QSS Styles (Buttons, Inputs, Lists, Trees, Checkboxes, Sliders, Status)
"""

from .tokens import FONT_FAMILY


def get_theme_controls() -> str:
    return f"""
/* ── Buttons ─────────────────────────────────────────────────── */
QPushButton {{
    background: #0f172a;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
    min-height: 20px;
}}
QPushButton:hover   {{ background: #1e293b; }}
QPushButton:pressed {{ background: #334155; }}
QPushButton:disabled {{ background: #e2e8f0; color: #94a3b8; }}
QPushButton:flat    {{ background: transparent; color: #0f172a; font-weight: 600; padding: 4px 8px; }}
QPushButton:flat:hover {{ background: #f1f5f9; }}

/* ── Input Fields ────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
    selection-background-color: #cbd5e1;
    selection-color: #0f172a;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid #0f172a;
    outline: none;
}}

/* ── Combo Box / Spin Box ────────────────────────────────────── */
QComboBox {{
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
}}
QComboBox:focus {{ border: 1.5px solid #0f172a; }}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: #ffffff;
    color: #1e293b;
    selection-background-color: #e2e8f0;
    selection-color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 2px;
}}

QSpinBox, QDoubleSpinBox {{
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 6px;
    font-size: 12px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1.5px solid #0f172a; }}

/* ── Group Box ───────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
    color: #0f172a;
    background: #ffffff;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    background: #ffffff;
    color: #0f172a;
    font-weight: 600;
}}

/* ── Progress Bar ────────────────────────────────────────────── */
QProgressBar {{
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    background: #f1f5f9;
    text-align: center;
    color: #334155;
    font-size: 11px;
    font-weight: 600;
    min-height: 18px;
}}
QProgressBar::chunk {{
    background: #0f172a;
    border-radius: 3px;
}}

/* ── List / Tree / Table Widgets ─────────────────────────────── */
QListWidget, QTreeWidget, QTableWidget, QTreeView, QTableView {{
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    outline: none;
    font-size: 12px;
    selection-background-color: #e2e8f0;
    selection-color: #0f172a;
}}
QTreeWidget::branch, QTreeView::branch {{
    background: transparent;
}}
QTreeWidget::branch:selected, QTreeView::branch:selected {{
    background: #e2e8f0;
}}
QTreeWidget::branch:hover:!selected, QTreeView::branch:hover:!selected {{
    background: #f8fafc;
}}
QListWidget::item, QTreeWidget::item, QTableWidget::item, QTreeView::item, QTableView::item {{
    padding: 5px 8px;
    border-radius: 4px;
}}
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected, QTreeView::item:selected, QTableView::item:selected {{
    background: #e2e8f0;
    color: #0f172a;
    font-weight: 600;
}}
QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected, QTableWidget::item:hover:!selected, QTreeView::item:hover:!selected, QTableView::item:hover:!selected {{
    background: #f8fafc;
}}
QHeaderView::section {{
    background: #f8fafc;
    color: #475569;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    padding: 6px 10px;
    font-weight: 600;
    font-size: 11px;
}}

/* ── Check Box / Radio ───────────────────────────────────────── */
QCheckBox, QRadioButton {{
    color: #334155;
    spacing: 7px;
    font-size: 12px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px; height: 15px;
    border: 1px solid #94a3b8;
    border-radius: 3px;
    background: #ffffff;
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: #0f172a;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: #0f172a;
    border: 1px solid #000000;
}}

/* ── Tooltip ─────────────────────────────────────────────────── */
QToolTip {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 11px;
    font-family: {FONT_FAMILY};
}}

/* ── Slider ──────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: #e2e8f0;
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #0f172a;
    width: 16px; height: 16px;
    border-radius: 8px;
    margin: -5px 0;
}}
QSlider::handle:horizontal:hover {{ background: #334155; }}

/* ── Status Bar ──────────────────────────────────────────────── */
QStatusBar {{
    background-color: #ffffff;
    color: #475569;
    border-top: 1px solid #e2e8f0;
    font-size: 11px;
    min-height: 26px;
}}
"""
