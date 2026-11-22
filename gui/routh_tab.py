#GUI OF ROUTH 
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSplitter,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout, QWidget, QAbstractItemView)
from PyQt5.QtCore import Qt

from core.routh import analyze, fmt_cell, RouthInputError

STABLE_EXAMPLE = "s^4 + 10s^3 + 35s^2 + 50s + 24 = 0"
UNSTABLE_EXAMPLE = "s^5 + s^4 + 10s^3 + 72s^2 + 152s + 240 = 0"


class RouthTab(QWidget):
    """Input -> Routh table + steps -> verdict -> numerical root check."""

    def __init__(self, parent=None):
        super().__init__(parent)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)

        # input row
        self.input = QLineEdit()
        self.input.setPlaceholderText("s^3 + 6s^2 + 11s + 6 = 0   or   1, 6, 11, 6")
        self.input.returnPressed.connect(self.calculate)
        btn_calc = QPushButton("Calculate")
        btn_calc.clicked.connect(self.calculate)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear)
        btn_st = QPushButton("Load stable example")
        btn_st.clicked.connect(lambda: self._load(STABLE_EXAMPLE))
        btn_un = QPushButton("Load unstable example")
        btn_un.clicked.connect(lambda: self._load(UNSTABLE_EXAMPLE))
        top = QHBoxLayout()
        top.addWidget(QLabel("Characteristic equation:"))
        top.addWidget(self.input, 1)
        for b in (btn_calc, btn_clear, btn_st, btn_un):
            top.addWidget(b)

        # table
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFont(mono)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # steps
        self.steps = QTextEdit()
        self.steps.setReadOnly(True)
        self.steps.setFont(mono)

        # roots
        self.roots = QTableWidget(0, 3)
        self.roots.setHorizontalHeaderLabels(["Pole", "Real part", "Half-plane"])
        self.roots.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.roots.setFont(mono)
        self.roots.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.roots.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("Routh table"))
        lv.addWidget(self.table)
        lv.addWidget(QLabel("Numerical poles (numpy.roots)"))
        lv.addWidget(self.roots)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addWidget(QLabel("Calculation steps"))
        rv.addWidget(self.steps)
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([480, 520])

        self.verdict = QLabel("")
        self.verdict.setWordWrap(True)
        self.verdict.setStyleSheet("font-size:14px; padding:8px; border-radius:6px;")
        self.check = QLabel("")
        self.check.setWordWrap(True)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(split, 1)
        root.addWidget(self.verdict)
        root.addWidget(self.check)

    # ---- actions ----
    def _load(self, text):
        self.input.setText(text)
        self.calculate()

    def clear(self):
        self.input.clear()
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.roots.setRowCount(0)
        self.steps.clear()
        self.verdict.clear()
        self.verdict.setStyleSheet("")
        self.check.clear()

    def calculate(self):
        try:
            res, rt, agrees = analyze(self.input.text())
        except RouthInputError as e:
            QMessageBox.warning(self, "Invalid input", str(e))
            return
        self._show_table(res)
        self.steps.setPlainText(self._steps_text(res))
        if res.special_case:
            self._set_verdict(res.special_case, "#b45309", "#fef3c7")
            self.roots.setRowCount(0)
            self.check.setText("")
            return
        if res.stable:
            self._set_verdict("No sign changes in the first column: STABLE "
                              "(0 poles in the right half-plane).",
                              "#166534", "#dcfce7")
        else:
            self._set_verdict(f"{res.sign_changes} sign change(s) in the first "
                              f"column: UNSTABLE ({res.sign_changes} pole(s) in "
                              "the right half-plane).", "#991b1b", "#fee2e2")
        self._show_roots(rt)
        mark = "agrees with" if agrees else "DOES NOT agree with"
        self.check.setText(f"Numerical RHP poles = {rt['rhp_count']} "
                           f"(tolerance {rt['tol']:g}); Routh count = "
                           f"{res.sign_changes}: {mark} the Routh result.")

    # ---- rendering helpers ----
    def _set_verdict(self, text, fg, bg):
        self.verdict.setText(text)
        self.verdict.setStyleSheet(
            f"font-size:14px; padding:8px; border-radius:6px; color:{fg}; background:{bg};")

    def _show_table(self, res):
        cols = len(res.rows[0])
        self.table.clear()
        self.table.setRowCount(len(res.rows))
        self.table.setColumnCount(cols)
        self.table.setHorizontalHeaderLabels([f"col {i+1}" for i in range(cols)])
        self.table.setVerticalHeaderLabels(res.labels[:len(res.rows)])
        for i, row in enumerate(res.rows):
            for j, v in enumerate(row):
                item = QTableWidgetItem(fmt_cell(v))
                item.setTextAlignment(Qt.AlignCenter)
                if j == 0 and not res.special_case:
                    item.setBackground(QColor("#fee2e2") if v < 0 else QColor("#e0f2fe"))
                self.table.setItem(i, j, item)

    def _steps_text(self, res):
        lines = ["Rule: cell = (lower[0]·upper[j+1] − upper[0]·lower[j+1]) / lower[0]",
                 "(lower = row just above the new row, upper = row above lower)", ""]
        lines += res.steps
        if res.first_column:
            lines += ["", "First column: " + ", ".join(fmt_cell(v) for v in res.first_column),
                      f"Sign changes = {res.sign_changes}"]
        return "\n".join(lines)

    def _show_roots(self, rt):
        self.roots.setRowCount(len(rt["roots"]))
        for i, r in enumerate(rt["roots"]):
            rhp = r.real > rt["tol"]
            vals = [f"{r.real:.4f} {'+' if r.imag >= 0 else '-'} {abs(r.imag):.4f}j",
                    f"{r.real:.4f}", "RHP" if rhp else "LHP"]
            for j, t in enumerate(vals):
                item = QTableWidgetItem(t)
                item.setTextAlignment(Qt.AlignCenter)
                if rhp:
                    item.setBackground(QColor("#fee2e2"))
                self.roots.setItem(i, j, item)