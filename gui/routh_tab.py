#GUI OF ROUTH 
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSlider, QSplitter,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout, QWidget, QAbstractItemView)
from PyQt5.QtCore import Qt

from core.routh import analyze, fmt_cell, RouthInputError
from gui.splane_canvas import SPlaneCanvas

STABLE_EXAMPLE = "s^4 + 10s^3 + 35s^2 + 50s + 24 = 0"
UNSTABLE_EXAMPLE = "s^5 + s^4 + 10s^3 + 72s^2 + 152s + 240 = 0"


class RouthTab(QWidget):
    """Input -> Routh table + steps -> verdict -> numerical root check."""

    def __init__(self, parent=None):
        super().__init__(parent)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)

        # input row
        lbl_eq = QLabel("Characteristic equation:")
        lbl_eq.setStyleSheet("font-size: 14px; font-weight: 600;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("s^3 + 6s^2 + 11s + 6 = 0   or   1, 6, 11, 6")
        self.input.setStyleSheet("font-family: Consolas, 'Segoe UI', monospace; font-size: 15px; font-weight: 600; padding: 6px 12px;")
        self.input.returnPressed.connect(self.calculate)
        btn_calc = QPushButton("Calculate")
        btn_calc.setObjectName("primaryButton")
        btn_calc.clicked.connect(self.calculate)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear)
        btn_st = QPushButton("Load stable example")
        btn_st.clicked.connect(lambda: self._load(STABLE_EXAMPLE))
        btn_un = QPushButton("Load unstable example")
        btn_un.clicked.connect(lambda: self._load(UNSTABLE_EXAMPLE))
        top = QHBoxLayout()
        top.addWidget(lbl_eq)
        top.addWidget(self.input, 1)
        for b in (btn_calc, btn_clear, btn_st, btn_un):
            top.addWidget(b)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFont(mono)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self._on_cell_clicked)

        # Interactive S-Plane Pole-Zero Map
        self.splane = SPlaneCanvas()
        self.splane.pole_clicked.connect(self._on_pole_clicked)

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
        self.roots.itemSelectionChanged.connect(self._on_roots_selection_changed)

        # Interactive parameter slider row
        slider_row = QHBoxLayout()
        slider_label = QLabel("Interactive Gain Tuning:")
        slider_label.setStyleSheet("font-weight:600; color:#CBA6F7;")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 200)   # K: 0.0 to 20.0
        self.slider.setValue(40)       # K = 4.0
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.slider_val_label = QLabel("K = 4.0")
        self.slider_val_label.setStyleSheet("font-family:Consolas; font-weight:bold; color:#A6E3A1; min-width:60px;")
        
        btn_demo_k = QPushButton("Load K-parameter system (s³ + 3s² + 2s + K = 0)")
        btn_demo_k.setToolTip("Test live stability boundary crossing at K = 6.0")
        btn_demo_k.clicked.connect(self._load_k_demo)

        slider_row.addWidget(slider_label)
        slider_row.addWidget(self.slider, 1)
        slider_row.addWidget(self.slider_val_label)
        slider_row.addWidget(btn_demo_k)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("Routh table (click any cell to inspect derivation)"))
        lv.addWidget(self.table, 3)
        lv.addWidget(QLabel("Interactive Complex S-Plane Map (s = \u03C3 + j\u03C9)"))
        lv.addWidget(self.splane, 3)
        lv.addWidget(QLabel("Numerical poles (numpy.roots)"))
        lv.addWidget(self.roots, 2)
        right = QWidget()
        rv = QVBoxLayout(right)

        header_row = QHBoxLayout()
        header_label = QLabel("Calculation steps")
        header_label.setStyleSheet("font-weight: 600; font-size: 13px;")

        self._font_size = 14
        self._is_dark = True

        font_tag = QLabel("Font:")
        font_tag.setStyleSheet("color:#A6ADC8; font-weight:600; font-size:11px; margin-left:8px;")
        btn_dec = QPushButton("A-")
        btn_dec.setObjectName("fontBtn")
        btn_dec.setToolTip("Decrease calculation font size")
        btn_dec.setFixedSize(30, 24)
        btn_dec.clicked.connect(self._dec_font)
        self.font_size_label = QLabel(f"{self._font_size}px")
        self.font_size_label.setStyleSheet("font-weight:bold; font-size:12px; min-width:32px;")
        self.font_size_label.setAlignment(Qt.AlignCenter)
        btn_inc = QPushButton("A+")
        btn_inc.setObjectName("fontBtn")
        btn_inc.setToolTip("Increase calculation font size")
        btn_inc.setFixedSize(30, 24)
        btn_inc.clicked.connect(self._inc_font)

        header_row.addWidget(header_label)
        header_row.addStretch(1)
        header_row.addWidget(font_tag)
        header_row.addWidget(btn_dec)
        header_row.addWidget(self.font_size_label)
        header_row.addWidget(btn_inc)

        rv.addLayout(header_row)
        rv.addWidget(self.steps)
        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        split.setSizes([460, 740])

        self.verdict = QLabel("")
        self.verdict.setWordWrap(True)
        self.verdict.setStyleSheet("font-size:14px; padding:8px; border-radius:6px;")
        self.check = QLabel("")
        self.check.setWordWrap(True)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addLayout(slider_row)
        root.addWidget(split, 1)
        root.addWidget(self.verdict)
        root.addWidget(self.check)

        self._last_res = None
        self.input.setText("s^4 + 2 s^3 + 3 s^2 + 4 s + 5")
        self.calculate()

    # ---- actions ----
    def _load(self, text):
        self.input.setText(text)
        self.calculate()

    def clear(self):
        self._last_res = None
        self.splane.clear()
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
        self._last_res = res
        self._last_rt = rt
        self._show_table(res)
        self.steps.setHtml(self._steps_html(res))
        if res.special_case:
            self._set_verdict(res.special_case, "#F9E2AF", "#3B2E1C", "#6B5328")
            self.roots.setRowCount(0)
            self.splane.clear()
            self.check.setText("")
            return
        if res.stable:
            self._set_verdict("No sign changes in the first column: STABLE "
                              "(0 poles in the right half-plane).",
                              "#A6E3A1", "#1C3B2B", "#2E6044")
        else:
            self._set_verdict(f"{res.sign_changes} sign change(s) in the first "
                              f"column: UNSTABLE ({res.sign_changes} pole(s) in "
                              "the right half-plane).", "#F38BA8", "#3D1F28", "#6E2E3E")
        self._show_roots(rt)
        self.splane.set_roots(rt["roots"], rt["tol"])
        mark = "agrees with" if agrees else "DOES NOT agree with"
        self.check.setStyleSheet("color: #A6ADC8; font-size: 12px; padding: 4px;")
        self.check.setText(f"Numerical RHP poles = {rt['rhp_count']} "
                           f"(tolerance {rt['tol']:g}); Routh count = "
                           f"{res.sign_changes}: {mark} the Routh result.")

    # ---- interactive handlers ----
    def _on_slider_changed(self, val):
        k = val / 10.0
        self.slider_val_label.setText(f"K = {k:.1f}")
        current = self.input.text().strip()
        if not current or "s^3 + 3s^2 + 2s" in current or "K" in current or "k" in current:
            self.input.setText(f"s^3 + 3s^2 + 2s + {k:.1f} = 0")
            self.calculate()

    def _load_k_demo(self):
        self.slider.setValue(40)
        self.input.setText("s^3 + 3s^2 + 2s + 4.0 = 0")
        self.calculate()

    def _on_roots_selection_changed(self):
        sel = self.roots.selectedIndexes()
        if sel:
            self.splane.select_root(sel[0].row())

    def _on_pole_clicked(self, index):
        if 0 <= index < self.roots.rowCount():
            self.roots.selectRow(index)

    def _on_cell_clicked(self, row, col):
        if not hasattr(self, "_last_res") or not self._last_res:
            return
        res = self._last_res
        if row >= 2 and row < len(res.rows) and col < len(res.rows[row]):
            val = res.rows[row][col]
            lower_0 = res.rows[row - 1][0]
            upper_next = res.rows[row - 2][col + 1] if col + 1 < len(res.rows[row - 2]) else 0.0
            upper_0 = res.rows[row - 2][0]
            lower_next = res.rows[row - 1][col + 1] if col + 1 < len(res.rows[row - 1]) else 0.0

            formula = (f"Cell derivation [{res.labels[row]}, col {col+1}]: "
                       f"({fmt_cell(lower_0)} \u00B7 {fmt_cell(upper_next)} \u2212 "
                       f"{fmt_cell(upper_0)} \u00B7 {fmt_cell(lower_next)}) / {fmt_cell(lower_0)} = {fmt_cell(val)}")
            self.verdict.setText(formula)
            self.verdict.setStyleSheet("font-size:13px; font-weight:600; padding:10px 14px; border-radius:8px; "
                                       "color:#CBA6F7; background:#1E1E2E; border:1px solid #CBA6F7;")

    # ---- rendering helpers ----
    def _set_verdict(self, text, fg, bg, border="transparent"):
        self.verdict.setText(text)
        self.verdict.setStyleSheet(
            f"font-size:13px; font-weight:600; padding:10px 14px; border-radius:8px; "
            f"color:{fg}; background:{bg}; border:1px solid {border};")

    def _inc_font(self):
        if self._font_size < 26:
            self._font_size += 1
            self.font_size_label.setText(f"{self._font_size}px")
            if self._last_res:
                self.steps.setHtml(self._steps_html(self._last_res))

    def _dec_font(self):
        if self._font_size > 10:
            self._font_size -= 1
            self.font_size_label.setText(f"{self._font_size}px")
            if self._last_res:
                self.steps.setHtml(self._steps_html(self._last_res))

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self.splane.set_theme(is_dark)
        if hasattr(self, 'font_size_label'):
            accent = "#CBA6F7" if is_dark else "#6366F1"
            self.font_size_label.setStyleSheet(f"color:{accent}; font-weight:bold; font-size:12px; min-width:32px;")
        if self._last_res:
            self._show_table(self._last_res)
            self.steps.setHtml(self._steps_html(self._last_res))
            if hasattr(self, '_last_rt') and self._last_rt:
                self._show_roots(self._last_rt)
            if self._last_res.special_case:
                self._set_verdict(self._last_res.special_case, "#D97706" if not is_dark else "#F9E2AF", "#FEF3C7" if not is_dark else "#3B2E1C", "#F59E0B" if not is_dark else "#6B5328")
            elif self._last_res.stable:
                self._set_verdict("No sign changes in the first column: STABLE (0 poles in the right half-plane).",
                                  "#059669" if not is_dark else "#A6E3A1",
                                  "#ECFDF5" if not is_dark else "#1C3B2B",
                                  "#10B981" if not is_dark else "#2E6044")
            else:
                self._set_verdict(f"{self._last_res.sign_changes} sign change(s) in the first column: UNSTABLE ({self._last_res.sign_changes} pole(s) in the right half-plane).",
                                  "#DC2626" if not is_dark else "#F38BA8",
                                  "#FEF2F2" if not is_dark else "#3D1F28",
                                  "#EF4444" if not is_dark else "#6E2E3E")

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
                    if v < 0:
                        item.setBackground(QColor("#3D1F28" if self._is_dark else "#FEF2F2"))
                        item.setForeground(QColor("#F38BA8" if self._is_dark else "#DC2626"))
                    else:
                        item.setBackground(QColor("#1C3B2B" if self._is_dark else "#ECFDF5"))
                        item.setForeground(QColor("#A6E3A1" if self._is_dark else "#059669"))
                else:
                    item.setForeground(QColor("#CDD6F4" if self._is_dark else "#0F172A"))
                self.table.setItem(i, j, item)

    def _steps_html(self, res):
        """Format the Routh calculation steps into visually clear, eye-comfortable cards."""
        fs = self._font_size
        dark = self._is_dark

        card_bg = "#181825" if dark else "#FFFFFF"
        card_border = "#313244" if dark else "#CBD5E1"
        accent = "#CBA6F7" if dark else "#6366F1"
        text_color = "#CDD6F4" if dark else "#0F172A"
        subtext = "#A6ADC8" if dark else "#64748B"
        code_bg = "#1E1E2E" if dark else "#F8FAFC"
        code_border = "#2B2B3D" if dark else "#E2E8F0"
        tag_bg = "#313244" if dark else "#E2E8F0"
        tag_fg = "#89DCEB" if dark else "#0284C7"
        formula_title = "#FFFFFF" if dark else "#0F172A"

        html = []
        html.append(f"""
        <div style="font-family:'Segoe UI',-apple-system,sans-serif; color:{text_color}; font-size:{fs}px; line-height:1.6;">
          <!-- Determinant Formula Banner -->
          <div style="background-color:{card_bg}; border:1px solid {card_border}; border-radius:12px; padding:12px 16px; margin-bottom:12px;">
            <div style="color:{accent}; font-weight:bold; font-size:{max(11, fs-1)}px; margin-bottom:6px;">
              ✦ Routh Array Determinant Formula
            </div>
            <div style="font-family:Consolas,monospace; font-size:{fs+1}px; font-weight:bold; color:{formula_title}; margin-bottom:6px;">
              cell = (lower[0] &middot; upper[j+1] &minus; upper[0] &middot; lower[j+1]) / lower[0]
            </div>
            <div style="color:{subtext}; font-size:{max(11, fs-2)}px;">
              &bull; <b>lower</b>: row directly above the new cell &nbsp;&bull;&nbsp; <b>upper</b>: row above lower
            </div>
          </div>
        """)

        # Categorize initial polynomial rows vs calculated rows
        initial_rows = []
        calc_rows = []
        for step in res.steps:
            if "row: coefficients" in step or "row:" in step:
                initial_rows.append(step)
            else:
                calc_rows.append(step)

        if initial_rows:
            html.append(f"""
            <div style="background-color:{card_bg}; border:1px solid {card_border}; border-radius:12px; padding:12px 16px; margin-bottom:12px;">
              <div style="color:{accent}; font-weight:bold; font-size:{max(11, fs-2)}px; text-transform:uppercase; margin-bottom:8px;">
                Initial Rows (From Characteristic Polynomial)
              </div>
            """)
            for s in initial_rows:
                parts = s.split(":", 1)
                label = parts[0].strip()
                val = parts[1].strip() if len(parts) > 1 else ""
                html.append(f"""
                <div style="font-family:Consolas,monospace; font-size:{fs}px; margin:6px 0;">
                  <span style="background:{tag_bg}; color:{accent}; font-weight:bold; padding:3px 10px; border-radius:6px;">{label}</span>
                  <span style="color:{text_color}; margin-left:10px;">{val}</span>
                </div>
                """)
            html.append("</div>")

        if calc_rows:
            html.append(f"""
            <div style="background-color:{card_bg}; border:1px solid {card_border}; border-radius:12px; padding:12px 16px; margin-bottom:12px;">
              <div style="color:{accent}; font-weight:bold; font-size:{max(11, fs-2)}px; text-transform:uppercase; margin-bottom:10px;">
                Step-by-Step Row Calculations
              </div>
            """)
            for s in calc_rows:
                if ":" in s:
                    label, math_part = s.split(":", 1)
                    eq_parts = math_part.split("=")
                    formula = eq_parts[0].strip() if len(eq_parts) > 1 else math_part
                    result = eq_parts[1].strip() if len(eq_parts) > 1 else ""

                    is_neg = result.startswith("-")
                    if dark:
                        res_bg = "#3D1F28" if is_neg else "#1C3B2B"
                        res_border = "#6E2E3E" if is_neg else "#2E6044"
                        res_color = "#F38BA8" if is_neg else "#A6E3A1"
                    else:
                        res_bg = "#FEF2F2" if is_neg else "#ECFDF5"
                        res_border = "#FCA5A5" if is_neg else "#6EE7B7"
                        res_color = "#DC2626" if is_neg else "#059669"

                    html.append(f"""
                    <div style="margin:7px 0; padding:8px 12px; background:{code_bg}; border-radius:8px; border:1px solid {code_border};">
                      <span style="background:{tag_bg}; color:{tag_fg}; font-weight:bold; padding:3px 8px; border-radius:6px; font-family:Consolas,monospace; font-size:{max(11, fs-2)}px;">{label.strip()}</span>
                      <span style="font-family:Consolas,monospace; color:{text_color}; margin-left:10px; font-size:{fs}px;">{formula} = </span>
                      <span style="background:{res_bg}; color:{res_color}; font-weight:bold; font-family:Consolas,monospace; padding:3px 10px; border-radius:6px; font-size:{fs}px; border:1px solid {res_border};">{result}</span>
                    </div>
                    """)
                else:
                    html.append(f"<div style='color:{subtext}; font-family:Consolas,monospace; font-size:{fs-1}px; margin:5px 0;'>{s}</div>")
            html.append("</div>")

        # First column and sign changes card
        if res.first_column:
            if dark:
                sign_bg = "#3D1F28" if res.sign_changes > 0 else "#1C3B2B"
                sign_border = "#6E2E3E" if res.sign_changes > 0 else "#2E6044"
                sign_color = "#F38BA8" if res.sign_changes > 0 else "#A6E3A1"
            else:
                sign_bg = "#FEF2F2" if res.sign_changes > 0 else "#ECFDF5"
                sign_border = "#FCA5A5" if res.sign_changes > 0 else "#6EE7B7"
                sign_color = "#DC2626" if res.sign_changes > 0 else "#059669"

            status_text = f"{res.sign_changes} sign change(s) &bull; UNSTABLE ({res.sign_changes} RHP poles)" if res.sign_changes > 0 else "0 sign changes &bull; STABLE (0 RHP poles)"

            col_pills = []
            for v in res.first_column:
                v_str = fmt_cell(v)
                neg = v < 0
                if dark:
                    pill_bg = "#3D1F28" if neg else "#1C3B2B"
                    pill_fg = "#F38BA8" if neg else "#A6E3A1"
                else:
                    pill_bg = "#FEF2F2" if neg else "#ECFDF5"
                    pill_fg = "#DC2626" if neg else "#059669"
                col_pills.append(f"<span style='background:{pill_bg}; color:{pill_fg}; font-weight:bold; padding:4px 10px; border-radius:8px; margin:3px; font-size:{fs}px;'>{v_str}</span>")

            html.append(f"""
            <div style="background-color:{card_bg}; border:1.5px solid {sign_border}; border-radius:12px; padding:14px 16px; margin-bottom:10px;">
              <div style="color:{accent}; font-weight:bold; font-size:{max(11, fs-2)}px; text-transform:uppercase; margin-bottom:8px;">
                First Column Sign Sequence
              </div>
              <div style="font-family:Consolas,monospace; margin:8px 0;">
                {" &rarr; ".join(col_pills)}
              </div>
              <div style="margin-top:10px;">
                <span style="background:{sign_bg}; color:{sign_color}; font-weight:bold; font-size:{fs-1}px; padding:6px 14px; border-radius:8px; border:1px solid {sign_border};">
                  {status_text}
                </span>
              </div>
            </div>
            """)

        html.append("</div>")
        return "".join(html)

    def _steps_text(self, res):
        lines = ["Rule: cell = (lower[0]·upper[j+1] − upper[0]·lower[j+1]) / lower[0]",
                 "(lower = row just above the new row, upper = row above lower)", ""]
        lines += res.steps
        if res.first_column:
            lines += ["", "First column: " + ", ".join(fmt_cell(v) for v in res.first_column),
                      f"Sign changes = {res.sign_changes}"]
        return "\n".join(lines)

    def _show_roots(self, rt):
        self._last_rt = rt
        self.roots.setRowCount(len(rt["roots"]))
        dark = self._is_dark
        for i, r in enumerate(rt["roots"]):
            rhp = r.real > rt["tol"]
            vals = [f"{r.real:.4f} {'+' if r.imag >= 0 else '-'} {abs(r.imag):.4f}j",
                    f"{r.real:.4f}", "RHP" if rhp else "LHP"]
            for j, t in enumerate(vals):
                item = QTableWidgetItem(t)
                item.setTextAlignment(Qt.AlignCenter)
                if rhp:
                    item.setBackground(QColor("#3D1F28" if dark else "#FEF2F2"))
                    item.setForeground(QColor("#F38BA8" if dark else "#DC2626"))
                else:
                    item.setBackground(QColor("#1C3B2B" if dark else "#ECFDF5"))
                    item.setForeground(QColor("#A6E3A1" if dark else "#059669"))
                self.roots.setItem(i, j, item)