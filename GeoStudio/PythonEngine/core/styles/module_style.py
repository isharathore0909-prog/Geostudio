# -*- coding: utf-8 -*-
"""
GeoStudio - Module / Dialog Stylesheet
"""

from .tokens import FONT_FAMILY, MONO_FONT

MODULE_STYLE = f"""
    QWidget {{
        background: #ffffff;
        color: #0f172a;
        font-family: {FONT_FAMILY};
        font-size: 12px;
    }}
    QDialog {{
        background-color: #f8fafc;
        color: #0f172a;
    }}
    QGroupBox {{
        font-weight: 600;
        font-size: 11px;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        margin-top: 14px;
        padding: 10px 8px 8px 8px;
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
    QPushButton {{
        background: #0f172a;
        color: #ffffff;
        border: none;
        border-radius: 5px;
        padding: 6px 16px;
        font-weight: 600;
        font-size: 12px;
        min-height: 20px;
    }}
    QPushButton:hover {{ background: #1e293b; }}
    QPushButton:pressed {{ background: #334155; }}
    QPushButton:disabled {{ background: #e2e8f0; color: #94a3b8; }}
    QPushButton#blueBtn {{
        background: #0f172a;
        color: #ffffff;
    }}
    QPushButton#blueBtn:hover {{ background: #1e293b; }}
    QPushButton#grayBtn, QPushButton#toolBtn, QPushButton#secondaryBtn, QPushButton[text="Browse..."], QPushButton#browseBtn {{
        background: #f8fafc;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 5px;
        padding: 4px 14px;
        font-weight: 500;
        font-size: 11px;
        min-height: 22px;
    }}
    QPushButton#grayBtn:hover, QPushButton#toolBtn:hover, QPushButton#secondaryBtn:hover, QPushButton[text="Browse..."]:hover, QPushButton#browseBtn:hover {{
        background: #e2e8f0;
        color: #0f172a;
        border-color: #94a3b8;
    }}
    QPushButton#grayBtn:pressed, QPushButton#toolBtn:pressed, QPushButton#secondaryBtn:pressed, QPushButton[text="Browse..."]:pressed, QPushButton#browseBtn:pressed {{
        background: #cbd5e1;
    }}
    QPushButton:checked {{
        background: #e2e8f0;
        color: #0f172a;
        border: 1px solid #475569;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 5px;
        padding: 4px 8px;
        font-size: 12px;
        min-height: 28px;
        selection-background-color: #cbd5e1;
        selection-color: #0f172a;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1.5px solid #2563eb;
        background: #ffffff;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
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
    QLabel {{
        color: #334155;
        font-size: 12px;
        font-weight: 500;
    }}
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
        background: #2563eb;
        border-radius: 3px;
    }}
    QListWidget, QTreeWidget, QTableWidget, QTreeView, QTableView {{
        background: #ffffff;
        color: #1e293b;
        border: 1px solid #e2e8f0;
        border-radius: 5px;
        font-size: 12px;
        outline: none;
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
    QCheckBox, QRadioButton {{
        color: #1e293b;
        font-size: 12px;
        spacing: 8px;
        font-weight: 500;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid #94a3b8;
        border-radius: 3px;
        background: #ffffff;
    }}
    QRadioButton::indicator {{
        border-radius: 8px;
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: #2563eb;
    }}
    QCheckBox::indicator:checked {{
        background-color: #2563eb;
        border: 1px solid #1d4ed8;
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
    }}
    QRadioButton::indicator:checked {{
        background-color: #2563eb;
        border: 3px solid #ffffff;
        outline: 1.5px solid #2563eb;
    }}
    QTabWidget::pane {{
        border: 1px solid #e2e8f0;
        background: #ffffff;
        border-radius: 6px;
    }}
    QTabWidget::tab-bar {{
        left: 8px;
    }}
    QTabBar::tab {{
        background: #f1f5f9;
        color: #64748b;
        padding: 8px 22px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
        min-width: 68px;
    }}
    QTabBar::tab:selected {{
        background: #ffffff;
        color: #0f172a;
        border-bottom: 2px solid #2563eb;
    }}
    QTabBar::tab:hover:!selected {{
        background: #e2e8f0;
        color: #0f172a;
    }}
    QToolTip {{
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 5px;
        padding: 6px 10px;
        font-size: 11px;
    }}
"""


# ═══════════════════════════════════════════════════════════════════
# 2. OFF-WHITE PRO LIGHT THEME (Default Standalone GIS Workstation)
# ═══════════════════════════════════════════════════════════════════
