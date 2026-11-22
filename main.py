import os
import subprocess
import sys
from pathlib import Path

# If PyQt5 is not in current environment (e.g. user ran system python or double-clicked),
# automatically forward execution to the project's virtual environment.
try:
    import PyQt5
except ImportError:
    venv_py = Path(__file__).resolve().parent / "venv" / "Scripts" / "python.exe"
    if venv_py.exists() and Path(sys.executable) != venv_py:
        sys.exit(subprocess.call([str(venv_py)] + sys.argv))
    raise

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow


def enable_high_dpi():
    """Scale the whole UI with the Windows display scale (100%, 125%, 150%, ...).

    Without this, sizes given in px stay small while fonts given in pt grow,
    and the layout falls apart on scaled screens. PassThrough keeps 125%/150%
    exact instead of rounding them to 100%/200%. Must run before QApplication.
    """
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


def main():
    enable_high_dpi()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
