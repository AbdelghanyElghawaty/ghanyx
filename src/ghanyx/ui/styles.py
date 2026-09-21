"""
QSS (Qt Style Sheet) builder for Ghanyx.

Generates a global stylesheet string from the current Theme.
Widgets don't hard-code colors — they use `objectName` selectors
and the stylesheet handles the look.

Usage:
    from ghanyx.ui.styles import build_stylesheet

    qapp.setStyleSheet(build_stylesheet(get_theme()))

Design:
    - No PySide6 import needed to build the string (pure Python).
    - Uses only the semantic roles from `colors.REQUIRED_ROLES`.
    - Every widget selector is prefixed with `Q` (Qt) for consistency.
    - Comments in the output help debugging.
"""

from __future__ import annotations

from ghanyx.ui.theme import Theme


# ============================================================
# Public API
# ============================================================
def build_stylesheet(theme: Theme) -> str:
    """
    Return the full QSS string for the given theme.

    Call `qapp.setStyleSheet(build_stylesheet(theme))` to apply.
    """
    c = theme.color

    return f"""
/* ============================================================
 * Ghanyx — Global stylesheet
 * Theme: {theme.name} ({'dark' if theme.is_dark else 'light'})
 * ============================================================ */

/* ----- Base ----- */
QWidget {{
    background-color: {c('bg')};
    color: {c('text')};
    font-family: "{theme.font_family}";
    font-size: {theme.font_size}pt;
}}

QMainWindow, QDialog {{
    background-color: {c('bg')};
}}

/* ----- Labels ----- */
QLabel {{
    background: transparent;
    color: {c('text')};
}}
QLabel[muted="true"] {{
    color: {c('text_muted')};
}}
QLabel[dim="true"] {{
    color: {c('text_dim')};
}}
QLabel[heading="true"] {{
    font-size: {theme.font_size + 4}pt;
    font-weight: bold;
    color: {c('primary')};
}}

/* ----- Buttons ----- */
QPushButton {{
    background-color: {c('surface')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {c('surface_alt')};
    border-color: {c('primary')};
}}
QPushButton:pressed {{
    background-color: {c('primary_dark')};
    color: white;
}}
QPushButton:disabled {{
    background-color: {c('surface')};
    color: {c('text_dim')};
    border-color: {c('border')};
}}

QPushButton[primary="true"] {{
    background-color: {c('primary')};
    color: white;
    border: none;
    font-weight: bold;
}}
QPushButton[primary="true"]:hover {{
    background-color: {c('primary_hover')};
}}
QPushButton[primary="true"]:pressed {{
    background-color: {c('primary_dark')};
}}

QPushButton[danger="true"] {{
    background-color: {c('danger')};
    color: white;
    border: none;
}}
QPushButton[danger="true"]:hover {{
    background-color: {c('danger_hover')};
}}

QPushButton[success="true"] {{
    background-color: {c('success')};
    color: white;
    border: none;
}}
QPushButton[success="true"]:hover {{
    background-color: {c('success_hover')};
}}

/* ----- Line Edits ----- */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c('surface')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {c('primary')};
    selection-color: white;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {c('primary')};
}}
QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {c('bg')};
    color: {c('text_dim')};
}}

/* ----- Combo Box ----- */
QComboBox {{
    background-color: {c('surface')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 26px;
}}
QComboBox:hover {{
    border-color: {c('primary')};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {c('surface')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    selection-background-color: {c('primary')};
    selection-color: white;
}}

/* ----- Check Box / Radio ----- */
QCheckBox, QRadioButton {{
    color: {c('text')};
    spacing: 6px;
    background: transparent;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {c('border_strong')};
    background-color: {c('surface')};
}}
QCheckBox::indicator {{
    border-radius: 3px;
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c('primary')};
    border-color: {c('primary')};
}}

/* ----- Spin Box ----- */
QSpinBox, QDoubleSpinBox {{
    background-color: {c('surface')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    border-radius: 6px;
    padding: 5px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {c('primary')};
}}

/* ----- Tabs ----- */
QTabWidget::pane {{
    border: 1px solid {c('border')};
    background-color: {c('bg')};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: {c('surface')};
    color: {c('text_muted')};
    padding: 8px 18px;
    border: 1px solid {c('border')};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {c('primary')};
    color: white;
    font-weight: bold;
}}
QTabBar::tab:hover:!selected {{
    background-color: {c('surface_alt')};
}}

/* ----- Tables / Trees ----- */
QTableView, QTreeView, QListView {{
    background-color: {c('surface')};
    alternate-background-color: {c('surface_alt')};
    color: {c('text')};
    border: 1px solid {c('border')};
    gridline-color: {c('border')};
    selection-background-color: {c('primary')};
    selection-color: white;
}}
QHeaderView::section {{
    background-color: {c('surface_alt')};
    color: {c('text')};
    padding: 6px 10px;
    border: none;
    border-right: 1px solid {c('border')};
    border-bottom: 1px solid {c('border')};
    font-weight: bold;
}}
QHeaderView::section:hover {{
    background-color: {c('border')};
}}

/* ----- Scrollbars ----- */
QScrollBar:vertical {{
    background-color: {c('bg')};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {c('border_strong')};
    border-radius: 6px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {c('primary')};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {c('bg')};
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {c('border_strong')};
    border-radius: 6px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {c('primary')};
}}

/* ----- Menus ----- */
QMenuBar {{
    background-color: {c('surface')};
    color: {c('text')};
    border-bottom: 1px solid {c('border')};
}}
QMenuBar::item:selected {{
    background-color: {c('primary')};
    color: white;
}}
QMenu {{
    background-color: {c('surface')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {c('primary')};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background-color: {c('border')};
    margin: 4px 8px;
}}

/* ----- Status Bar ----- */
QStatusBar {{
    background-color: {c('statusbar')};
    color: {c('text_muted')};
    border-top: 1px solid {c('border')};
}}
QStatusBar::item {{
    border: none;
}}

/* ----- Tooltips ----- */
QToolTip {{
    background-color: {c('tooltip')};
    color: {c('text')};
    border: 1px solid {c('border_strong')};
    padding: 4px 8px;
    border-radius: 4px;
}}

/* ----- Progress Bar ----- */
QProgressBar {{
    background-color: {c('surface_alt')};
    border: 1px solid {c('border')};
    border-radius: 6px;
    text-align: center;
    color: {c('text')};
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {c('primary')};
    border-radius: 5px;
}}

/* ----- Group Box ----- */
QGroupBox {{
    background-color: {c('surface')};
    border: 1px solid {c('border')};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {c('primary')};
    left: 12px;
}}

/* ----- Frame (cards) ----- */
QFrame[card="true"] {{
    background-color: {c('surface')};
    border: 1px solid {c('border')};
    border-radius: 8px;
    padding: 12px;
}}

/* ----- Splitter ----- */
QSplitter::handle {{
    background-color: {c('border')};
}}
QSplitter::handle:hover {{
    background-color: {c('primary')};
}}

/* ----- Custom object names ----- */
QFrame#header {{
    background-color: {c('surface')};
    border-bottom: 2px solid {c('primary')};
}}
QLabel#title {{
    color: {c('primary')};
    font-size: {theme.font_size + 6}pt;
    font-weight: bold;
}}
QLabel#subtitle {{
    color: {c('text_muted')};
    font-size: {theme.font_size - 1}pt;
}}
"""