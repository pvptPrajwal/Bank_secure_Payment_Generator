APP_TITLE   = "Bank Payment File Generator - Enterprise Edition"
APP_VERSION = "2.0.0"

PRIMARY = "#0B3D2E"
ACCENT  = "#1F6F43"
DANGER  = "#8C1D1D"

STYLESHEET = f"""
QWidget {{
    background-color: #F4F6F5;
    color: #1A1A1A;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QFrame#Card {{
    background-color: white;
    border-radius: 8px;
    border: 1px solid #E0E0E0;
}}
QLabel#Title {{
    font-size: 20px;
    font-weight: 600;
    color: {PRIMARY};
}}
QLabel#Section {{
    font-size: 14px;
    font-weight: 600;
    color: {PRIMARY};
}}
QPushButton {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 18px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {ACCENT}; }}
QPushButton:disabled {{ background-color: #9E9E9E; }}
QPushButton#Danger {{ background-color: {DANGER}; }}
QPushButton#Danger:hover {{ background-color: #B33030; }}
QPushButton#Gray {{ background-color: #E0E0E0; color: #1A1A1A; }}
QPushButton#Gray:hover {{ background-color: #CFCFCF; }}
QLineEdit, QComboBox {{
    border: 1px solid #C9C9C9;
    border-radius: 4px;
    padding: 6px 8px;
    background: white;
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QTableWidget {{
    background: white;
    border: 1px solid #E0E0E0;
    gridline-color: #EEEEEE;
}}
QHeaderView::section {{
    background-color: {PRIMARY};
    color: white;
    padding: 6px;
    border: none;
    font-weight: 600;
}}
QTabBar::tab {{
    background: #E5E9E7;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{ background: {PRIMARY}; color: white; }}
QTabWidget::pane {{ border: 1px solid #E0E0E0; background: white; }}
"""
