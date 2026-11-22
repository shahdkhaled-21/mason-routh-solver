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

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
