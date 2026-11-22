"""Main application window: two tabs plus a File menu.

Nada's SFGTab and Nesma's RouthTab replace the placeholders as soon as
their modules exist (see _make_sfg_tab and _make_routh_tab).
"""
import json

from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QAction, QFileDialog, QMessageBox,
                             QPushButton, QActionGroup, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QGuiApplication

from core.graph import Graph
from gui.styles import VELVET_DUSK_QSS, LIGHT_THEME_QSS, apply_title_bar, apply_dark_title_bar


def _placeholder(text: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    label = QLabel(text)
    label.setAlignment(Qt.AlignCenter)
    lay.addWidget(label)
    return w


def _make_sfg_tab() -> QWidget:
    try:
        from gui.sfg_tab import SFGTab          # Nada (#2)
        return SFGTab()
    except ImportError:
        return _placeholder("Signal Flow Graph tab (waiting for Nada's gui/sfg_tab.py)")


def _make_routh_tab() -> QWidget:
    try:
        from gui.routh_tab import RouthTab      # Nesma (#5)
        return RouthTab()
    except ImportError:
        return _placeholder("Routh Stability tab (waiting for Nesma's gui/routh_tab.py)")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_dark = True
        self.setWindowTitle("CSE 341: Signal Flow Graphs (Mason) and Routh Stability")
        self._fit_to_screen()
        self.setStyleSheet(VELVET_DUSK_QSS)

        self.tabs = QTabWidget()
        # Qt sizes tabs with the tab bar's own font; make it bold like the
        # stylesheet draws it, so tab titles are never cut off.
        tab_font = self.tabs.tabBar().font()
        tab_font.setBold(True)
        self.tabs.tabBar().setFont(tab_font)
        self.tabs.tabBar().setElideMode(Qt.ElideNone)
        self.setCentralWidget(self.tabs)

        self.sfg_tab = _make_sfg_tab()
        self.routh_tab = _make_routh_tab()
        if hasattr(self.sfg_tab, "load_builtin_example"):
            self.sfg_tab.load_builtin_example()
        self.tabs.addTab(self._scrollable(self.sfg_tab), "⬡  Signal Flow Graph (Mason)")
        self.tabs.addTab(self._scrollable(self.routh_tab), "◈  Routh Stability (Hurwitz)")

        self._build_menu()
        self.statusBar().showMessage("Ready")
        apply_title_bar(self, self.is_dark)

    def showEvent(self, event):
        super().showEvent(event)
        apply_title_bar(self, self.is_dark)
        QTimer.singleShot(50, lambda: apply_title_bar(self, self.is_dark))
        QTimer.singleShot(200, lambda: apply_title_bar(self, self.is_dark))

    def _build_menu(self):
        # File Menu
        menu = self.menuBar().addMenu("▤  File")
        for text, handler in [("📂  Load graph...", self.load_graph),
                              ("💾  Save graph...", self.save_graph),
                              ("✕   Exit", self.close)]:
            action = QAction(text, self)
            action.triggered.connect(handler)
            menu.addAction(action)

        # Theme Menu
        theme_menu = self.menuBar().addMenu("🎨  Theme")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        self.dark_action = QAction("🌙  Velvet Dusk (Dark)", self, checkable=True)
        self.dark_action.setChecked(True)
        self.dark_action.triggered.connect(lambda: self.set_theme(True))
        self.theme_group.addAction(self.dark_action)
        theme_menu.addAction(self.dark_action)

        self.light_action = QAction("☀️  Soft Light (Light)", self, checkable=True)
        self.light_action.setChecked(False)
        self.light_action.triggered.connect(lambda: self.set_theme(False))
        self.theme_group.addAction(self.light_action)
        theme_menu.addAction(self.light_action)

        # Quick corner toggle button in menu bar
        self.theme_btn = QPushButton("🌙  Dark")
        self.theme_btn.setToolTip("Switch between Dark (Velvet Dusk) and Light theme")
        self.theme_btn.setStyleSheet("font-weight: 600; padding: 4px 12px; margin-right: 8px; border-radius: 12px;")
        self.theme_btn.clicked.connect(self.toggle_theme)
        # wide enough for both labels, so switching to "Light" is never cut off
        widths = []
        for label in ("🌙  Dark", "☀️  Light"):
            self.theme_btn.setText(label)
            widths.append(self.theme_btn.sizeHint().width())
        self.theme_btn.setText("🌙  Dark")
        self.theme_btn.setMinimumWidth(max(widths) + 8)
        self.menuBar().setCornerWidget(self.theme_btn, Qt.TopRightCorner)

    @staticmethod
    def _scrollable(tab):
        """Wrap a tab so a screen smaller than the tab's minimum size scrolls
        instead of cutting widgets off. On normal screens no scrollbar appears."""
        area = QScrollArea()
        area.setWidget(tab)
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setStyleSheet("QScrollArea { background: transparent; }")
        area.viewport().setAutoFillBackground(False)
        return area

    def _fit_to_screen(self):
        """Open at 1200x800, shrunk to fit the screen at any display scale, centred."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1200, 800)
            return
        avail = screen.availableGeometry()      # already in scaled (logical) pixels
        w = min(1200, int(avail.width() * 0.95))
        h = min(800, int(avail.height() * 0.92))
        self.resize(w, h)
        self.move(avail.x() + (avail.width() - w) // 2,
                  avail.y() + (avail.height() - h) // 2)
        # very small or heavily scaled screens: use all of it
        if avail.width() < 1100 or avail.height() < 700:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

    def toggle_theme(self):
        self.set_theme(not self.is_dark)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.setStyleSheet(VELVET_DUSK_QSS if is_dark else LIGHT_THEME_QSS)
        apply_title_bar(self, is_dark)
        self.theme_btn.setText("🌙  Dark" if is_dark else "☀️  Light")
        self.dark_action.setChecked(is_dark)
        self.light_action.setChecked(not is_dark)

        if hasattr(self.sfg_tab, "set_theme"):
            self.sfg_tab.set_theme(is_dark)
        if hasattr(self.routh_tab, "set_theme"):
            self.routh_tab.set_theme(is_dark)
        self.statusBar().showMessage(f"Theme switched to {'Velvet Dusk (Dark)' if is_dark else 'Soft Light (Light)'}", 3000)

    def _sfg_ready(self) -> bool:
        """True when Nada's real tab is installed (it has get_graph/set_graph)."""
        if hasattr(self.sfg_tab, "get_graph") and hasattr(self.sfg_tab, "set_graph"):
            return True
        QMessageBox.information(self, "Not available yet",
                                "The Signal Flow Graph tab is not installed yet.")
        return False

    def load_graph(self):
        if not self._sfg_ready():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Load graph", "examples",
                                              "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                graph = Graph.from_dict(json.load(f))
            self.sfg_tab.set_graph(graph)
            self.tabs.setCurrentWidget(self.sfg_tab)
            self.statusBar().showMessage(f"Loaded {path}")
        except Exception as e:
            QMessageBox.critical(self, "Load error", str(e))

    def save_graph(self):
        if not self._sfg_ready():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save graph", "examples",
                                              "JSON files (*.json)")
        if not path:
            return
        try:
            graph = self.sfg_tab.get_graph()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(graph.to_dict(), f, indent=2)
            self.statusBar().showMessage(f"Saved {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))
