"""Main application window: two tabs plus a File menu.

Nada's SFGTab and Nesma's RouthTab replace the placeholders as soon as
their modules exist (see _make_sfg_tab and _make_routh_tab).
"""
import json

from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QLabel, QAction, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

from core.graph import Graph


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
        self.setWindowTitle("CSE 341: Signal Flow Graphs (Mason) and Routh Stability")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.sfg_tab = _make_sfg_tab()
        self.routh_tab = _make_routh_tab()
        self.tabs.addTab(self.sfg_tab, "Signal Flow Graph")
        self.tabs.addTab(self.routh_tab, "Routh Stability")

        self._build_menu()
        self.statusBar().showMessage("Ready")

    def _build_menu(self):
        menu = self.menuBar().addMenu("&File")
        for text, handler in [("Load graph...", self.load_graph),
                              ("Save graph...", self.save_graph),
                              ("Exit", self.close)]:
            action = QAction(text, self)
            action.triggered.connect(handler)
            menu.addAction(action)

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
