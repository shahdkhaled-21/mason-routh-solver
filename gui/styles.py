"""Styling and theme system for Mason-Routh Solver (PyQt5).

Supports both:
1. Velvet Dusk (Dark) - A warm, eye-comforting dark palette inspired by
   Catppuccin Mocha/Macchiato with pastel lavender, mint, sky and peach accents.
2. Soft Light (Light) - A clean, eye-comforting academic light theme with
   slate typography, soft indigo accents, and glare-free off-white surfaces.
"""

DARK_PALETTE = {
    "base": "#1E1E2E",
    "mantle": "#181825",
    "crust": "#11111B",
    "surface": "#313244",
    "surface_hover": "#45475A",
    "tab_hover": "#262638",
    "text": "#CDD6F4",
    "subtext": "#A6ADC8",
    "overlay": "#6C7086",
    "accent": "#CBA6F7",
    "accent_hover": "#B4BEFE",
    "mint": "#A6E3A1",
    "sky": "#89DCEB",
    "peach": "#FAB387",
    "coral": "#F38BA8",
    "amber": "#F9E2AF",
    "btn_text": "#CDD6F4",
    "btn_text_hover": "#FFFFFF",
    "tab_selected_bg": "#313244",
    "border_light": "#45475A",
    "title_caption": 0x001B1111,
    "title_text": 0x00F7A6CB,
    "title_border": 0x00443231,
    "is_dark_mode": 1,
}

LIGHT_PALETTE = {
    "base": "#F1F5F9",          # Slate 100 soft background
    "mantle": "#FFFFFF",        # White cards
    "crust": "#E2E8F0",         # Slate 200 deeper surface (inputs/header)
    "surface": "#CBD5E1",       # Slate 300 borders
    "surface_hover": "#94A3B8", # Slate 400
    "tab_hover": "#E2E8F0",
    "text": "#0F172A",          # Slate 900 primary text
    "subtext": "#475569",       # Slate 600 secondary text
    "overlay": "#64748B",
    "accent": "#6366F1",        # Indigo primary accent
    "accent_hover": "#4F46E5",
    "mint": "#10B981",          # Emerald
    "sky": "#0284C7",           # Sky 600
    "peach": "#EA580C",         # Orange
    "coral": "#DC2626",         # Red
    "amber": "#D97706",         # Amber
    "btn_text": "#1E293B",
    "btn_text_hover": "#000000",
    "tab_selected_bg": "#FFFFFF",
    "border_light": "#CBD5E1",
    "title_caption": 0x00F0E8E2,
    "title_text": 0x002A170F,
    "title_border": 0x00E1D5CB,
    "is_dark_mode": 0,
}

# Compatibility constants (defaulting to Velvet Dusk dark)
COLOR_BASE = DARK_PALETTE["base"]
COLOR_MANTLE = DARK_PALETTE["mantle"]
COLOR_CRUST = DARK_PALETTE["crust"]
COLOR_SURFACE = DARK_PALETTE["surface"]
COLOR_SURFACE_HOVER = DARK_PALETTE["surface_hover"]
COLOR_TEXT = DARK_PALETTE["text"]
COLOR_SUBTEXT = DARK_PALETTE["subtext"]
COLOR_OVERLAY = DARK_PALETTE["overlay"]
COLOR_LAVENDER = DARK_PALETTE["accent"]
COLOR_LAVENDER_HOVER = DARK_PALETTE["accent_hover"]
COLOR_MINT = DARK_PALETTE["mint"]
COLOR_SKY = DARK_PALETTE["sky"]
COLOR_PEACH = DARK_PALETTE["peach"]
COLOR_CORAL = DARK_PALETTE["coral"]
COLOR_AMBER = DARK_PALETTE["amber"]

# Canvas Colors
CANVAS_BG = "#181825"
CANVAS_GRID_DOT = "#2A2A3C"
CANVAS_NODE_SRC = "#A6E3A1"
CANVAS_NODE_SINK = "#FAB387"
CANVAS_NODE_DEFAULT = "#89DCEB"
CANVAS_NODE_TEXT = "#11111B"
CANVAS_EDGE = "#89DCEB"
CANVAS_HIGHLIGHT = "#CBA6F7"
CANVAS_LABEL_BG = "#11111B"
CANVAS_LABEL_BORDER = "#45475A"
CANVAS_LABEL_TEXT = "#CDD6F4"


def apply_title_bar(window, is_dark: bool = True):
    """Style the native Windows OS title bar using Windows DWM API."""
    try:
        import ctypes
        hwnd = int(window.winId())
        palette = DARK_PALETTE if is_dark else LIGHT_PALETTE

        # 1. Enable/disable immersive dark mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20, or 19 on older Win10)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        val = ctypes.c_int(palette["is_dark_mode"])
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(val), ctypes.sizeof(val)
        )
        if res != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 19, ctypes.byref(val), ctypes.sizeof(val)
            )

        # 2. Windows 11 custom caption background color (attribute 35)
        DWMWA_CAPTION_COLOR = 35
        caption_color = ctypes.c_uint32(palette["title_caption"])
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption_color), ctypes.sizeof(caption_color)
        )

        # 3. Windows 11 custom title text color (attribute 36)
        DWMWA_TEXT_COLOR = 36
        text_color = ctypes.c_uint32(palette["title_text"])
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_TEXT_COLOR, ctypes.byref(text_color), ctypes.sizeof(text_color)
        )

        # 4. Windows 11 custom border color (attribute 34)
        DWMWA_BORDER_COLOR = 34
        border_color = ctypes.c_uint32(palette["title_border"])
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(border_color), ctypes.sizeof(border_color)
        )

        # 5. Force DWM to repaint the non-client title bar frame immediately
        SWP_FRAMECHANGED = 0x0020
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
        )
    except Exception:
        pass


def apply_dark_title_bar(window):
    """Backwards-compatible helper for dark title bar."""
    apply_title_bar(window, is_dark=True)


def generate_qss(p: dict) -> str:
    """Generate complete application stylesheet from palette dictionary."""
    return f"""
/* Global Window */
QWidget {{
    background-color: {p['base']};
    color: {p['text']};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {p['base']};
}}

/* Menu Bar */
QMenuBar {{
    background-color: {p['crust']};
    color: {p['text']};
    border-bottom: 1.5px solid {p['surface']};
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
}}

QMenuBar::item {{
    background-color: {p['mantle']};
    color: {p['text']};
    border: 1px solid {p['surface']};
    padding: 6px 16px;
    border-radius: 10px;
    margin-right: 8px;
    font-weight: 600;
}}

QMenuBar::item:selected, QMenuBar::item:pressed {{
    background-color: {p['surface']};
    color: {p['accent']};
    border: 1px solid {p['accent']};
}}

QMenu {{
    background-color: {p['mantle']};
    color: {p['text']};
    border: 1.5px solid {p['surface']};
    border-radius: 12px;
    padding: 6px;
}}

QMenu::item {{
    padding: 7px 24px;
    border-radius: 8px;
    margin: 2px 0px;
}}

QMenu::item:selected {{
    background-color: {p['surface']};
    color: {p['accent']};
    font-weight: 600;
}}

QMenu::separator {{
    height: 1px;
    background-color: {p['surface']};
    margin: 4px 8px;
}}

/* Tab Widget - Segmented Pill Capsule */
QTabWidget {{
    background-color: {p['base']};
}}

QTabWidget::pane {{
    border: 1px solid {p['surface']};
    background-color: {p['base']};
    border-radius: 12px;
    margin-top: 8px;
    padding: 2px;
}}

QTabWidget::tab-bar {{
    alignment: center;
}}

QTabBar {{
    background-color: {p['crust']};
    border: 1.5px solid {p['surface']};
    border-radius: 20px;
    padding: 3px 6px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {p['subtext']};
    border: 1px solid transparent;
    padding: 8px 26px;
    font-weight: 700;
    font-size: 12px;
    border-radius: 16px;
    margin: 2px 4px;
}}

QTabBar::tab:selected {{
    background-color: {p['tab_selected_bg']};
    color: {p['accent']};
    border: 1.5px solid {p['accent']};
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {p['tab_hover']};
    color: {p['text']};
    border: 1px solid {p['surface_hover']};
}}

/* Group Box */
QGroupBox {{
    font-weight: bold;
    border: 1px solid {p['surface']};
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    background-color: {p['mantle']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {p['accent']};
    font-size: 12px;
    font-weight: bold;
}}

/* Buttons */
QPushButton {{
    background-color: {p['surface']};
    color: {p['text']};
    border: 1px solid {p['surface_hover']};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {p['surface_hover']};
    border-color: {p['accent']};
    color: {p['btn_text_hover']};
}}

QPushButton:pressed {{
    background-color: {p['crust']};
}}

QPushButton#fontBtn {{
    padding: 1px 4px;
    font-size: 11px;
    font-weight: bold;
    min-width: 26px;
    border-radius: 6px;
}}

/* Solve & Primary Calculate Buttons */
QPushButton#solveButton, QPushButton#primaryButton {{
    background-color: {p['accent']};
    color: #FFFFFF;
    font-weight: bold;
    border: 1px solid {p['accent']};
    border-radius: 6px;
    padding: 7px 16px;
}}

QPushButton#solveButton:hover, QPushButton#primaryButton:hover {{
    background-color: {p['accent_hover']};
    border-color: {p['accent_hover']};
    color: #FFFFFF;
}}

QPushButton#solveButton:pressed, QPushButton#primaryButton:pressed {{
    background-color: {p['crust']};
}}

/* Inputs & Combos */
QLineEdit {{
    background-color: {p['crust']};
    color: {p['text']};
    border: 1px solid {p['surface']};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {p['surface_hover']};
}}

QLineEdit:focus {{
    border: 1px solid {p['accent']};
}}

QComboBox {{
    background-color: {p['crust']};
    color: {p['text']};
    border: 1px solid {p['surface']};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 20px;
}}

QComboBox:focus, QComboBox:hover {{
    border: 1px solid {p['accent']};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {p['crust']};
    color: {p['text']};
    border: 1px solid {p['surface']};
    selection-background-color: {p['surface']};
    selection-color: {p['accent']};
    outline: none;
    padding: 4px;
}}

/* Tables */
QTableWidget {{
    background-color: {p['crust']};
    color: {p['text']};
    gridline-color: {p['surface']};
    border: 1px solid {p['surface']};
    border-radius: 6px;
    selection-background-color: {p['surface_hover']};
    selection-color: {p['text']};
}}

QTableWidget::item {{
    padding: 4px;
}}

QTableWidget::item:selected {{
    background-color: {p['surface_hover']};
}}

QHeaderView::section {{
    background-color: {p['mantle']};
    color: {p['subtext']};
    font-weight: 600;
    font-size: 11px;
    padding: 6px 8px;
    border: 1px solid {p['surface']};
    border-top: none;
    border-left: none;
}}

/* Text Displays */
QTextEdit, QPlainTextEdit {{
    background-color: {p['crust']};
    color: {p['text']};
    border: 1px solid {p['surface']};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {p['surface_hover']};
}}

QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {p['accent']};
}}

/* Splitters */
QSplitter::handle {{
    background-color: {p['surface']};
}}

QSplitter::handle:hover {{
    background-color: {p['accent']};
}}

QSplitter::handle:horizontal {{
    width: 3px;
}}

QSplitter::handle:vertical {{
    height: 3px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {p['crust']};
    color: {p['subtext']};
    border-top: 1px solid {p['surface']};
    font-size: 11px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background-color: {p['mantle']};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {p['surface']};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {p['surface_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {p['mantle']};
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {p['surface']};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {p['surface_hover']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* the empty track around the handle (otherwise Qt draws a striped pattern) */
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}

/* top-left corner square of tables (otherwise it stays white) */
QTableCornerButton::section {{
    background-color: {p['mantle']};
    border: none;
}}
"""

VELVET_DUSK_QSS = generate_qss(DARK_PALETTE)
LIGHT_THEME_QSS = generate_qss(LIGHT_PALETTE)
