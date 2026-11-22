"""Signal Flow Graph tab (member #2): input, drawing and results.

SFGTab is what MainWindow puts in its first tab. Public interface:

    get_graph() -> core.graph.Graph    read the table and dropdowns
                                       (raises ValueError with a friendly message)
    set_graph(g)                       fill the table, dropdowns and drawing from a Graph

Layout: the branch table and buttons on the left; the drawing on top and the
results panel below on the right. The drawing updates live while you type.
"""
import json
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFontDatabase
from PyQt5.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QMenu, QMessageBox, QPushButton,
                             QSplitter, QTableWidget, QTableWidgetItem,
                             QTextEdit, QVBoxLayout, QWidget)

from core.graph import Graph, fmt, parse_gain
from core.pipeline import ModuleNotReady, solve_graph
from gui.graph_canvas import GraphCanvas

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

# Used when the examples folder is not available (for example inside the .exe).
BUILTIN_EXAMPLE = {
    "nodes": ["R", "A", "B", "C"],
    "edges": [
        {"from": "R", "to": "A", "gain": "1"},
        {"from": "A", "to": "B", "gain": "2"},
        {"from": "B", "to": "C", "gain": "3"},
        {"from": "B", "to": "A", "gain": "-1"},
        {"from": "A", "to": "C", "gain": "4"},
    ],
    "source": "R",
    "sink": "C",
}

BAD_CELL = QColor("#4A202A")


class SFGTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False             # True while the table is filled by code
        self._source_chosen = False       # True once the user picked the input node
        self._sink_chosen = False         # True once the user picked the output node

        self._timer = QTimer(self)        # redraw shortly after the last keystroke
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._live_update)

        self._build_ui()
        self._reset_table()
        self._live_update()

    def load_builtin_example(self):
        """Populate the table and canvas with the built-in example and solve."""
        self.set_graph(Graph.from_dict(BUILTIN_EXAMPLE))
        self.solve()

    # ================================================================== UI

    def _build_ui(self):


        # ---- left: input ----
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["From", "To", "Gain"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemChanged.connect(self._on_item_changed)

        add_btn = QPushButton("Add branch")
        add_btn.clicked.connect(self._add_branch)
        del_btn = QPushButton("Delete selected")
        del_btn.clicked.connect(self._delete_selected)
        row_buttons = QHBoxLayout()
        row_buttons.addWidget(add_btn)
        row_buttons.addWidget(del_btn)

        self.source_combo = QComboBox()
        self.sink_combo = QComboBox()
        self.source_combo.activated.connect(self._source_picked)
        self.sink_combo.activated.connect(self._sink_picked)
        self.source_combo.currentTextChanged.connect(lambda _t: self._timer.start())
        self.sink_combo.currentTextChanged.connect(lambda _t: self._timer.start())
        nodes_row = QHBoxLayout()
        nodes_row.addWidget(QLabel("Input node:"))
        nodes_row.addWidget(self.source_combo, 1)
        nodes_row.addWidget(QLabel("Output node:"))
        nodes_row.addWidget(self.sink_combo, 1)

        self.problem_label = QLabel("")
        self.problem_label.setWordWrap(True)
        self.problem_label.setStyleSheet("color: #F38BA8; font-weight: 500;")

        self.solve_btn = QPushButton("Solve")
        self.solve_btn.setObjectName("solveButton")
        self.solve_btn.clicked.connect(self.solve)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        self.example_btn = QPushButton("Load example")
        self.example_btn.clicked.connect(self._load_example)
        save_btn = QPushButton("Save graph")
        save_btn.clicked.connect(self._save_graph)
        export_btn = QPushButton("Export image")
        export_btn.clicked.connect(self._export_image)
        layout_btn = QPushButton("Auto layout")
        layout_btn.setToolTip("Put the nodes back in their automatic positions")
        layout_btn.clicked.connect(lambda: self.canvas.auto_layout())
        self.anim_btn = QPushButton("▶ Animate flow")
        self.anim_btn.setToolTip("Toggle animated signal pulse packets flowing along the branches")
        self.anim_btn.clicked.connect(self._toggle_animation)

        button_grid = QVBoxLayout()
        first = QHBoxLayout()
        first.addWidget(self.solve_btn, 2)
        first.addWidget(clear_btn, 1)
        second = QHBoxLayout()
        second.addWidget(self.example_btn)
        second.addWidget(save_btn)
        third = QHBoxLayout()
        third.addWidget(export_btn)
        third.addWidget(layout_btn)
        fourth = QHBoxLayout()
        fourth.addWidget(self.anim_btn)
        button_grid.addLayout(first)
        button_grid.addLayout(second)
        button_grid.addLayout(third)
        button_grid.addLayout(fourth)

        input_box = QGroupBox("Branches")
        input_layout = QVBoxLayout(input_box)
        input_layout.addWidget(self.table, 1)
        input_layout.addLayout(row_buttons)
        input_layout.addLayout(nodes_row)
        input_layout.addWidget(self.problem_label)
        input_layout.addLayout(button_grid)

        # ---- right: drawing and results ----
        self.canvas = GraphCanvas()
        self.canvas.edge_clicked.connect(self._on_canvas_edge_clicked)
        self.canvas.node_clicked.connect(self._on_canvas_node_clicked)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        legend = QLabel('<span style="color:#A6E3A1; font-size:14px;">&#9679;</span> input node &nbsp;&nbsp;'
                        '<span style="color:#FAB387; font-size:14px;">&#9679;</span> output node &nbsp;&nbsp;'
                        '<span style="color:#89DCEB; font-size:14px;">&#9679;</span> other node &nbsp;&nbsp;'
                        '<span style="color:#A6ADC8;">(drag nodes to move them, scroll to zoom)</span>')
        draw_box = QGroupBox("Signal flow graph")
        draw_layout = QVBoxLayout(draw_box)
        draw_layout.addWidget(self.canvas, 1)
        draw_layout.addWidget(legend)

        self.highlight_combo = QComboBox()
        self.highlight_combo.currentIndexChanged.connect(self._on_highlight_changed)
        highlight_row = QHBoxLayout()
        highlight_row.addWidget(QLabel("Highlight on graph:"))
        highlight_row.addWidget(self.highlight_combo, 1)

        # Font zoom controls for Mason calculation steps
        self._font_size = 14
        self._is_dark = True
        self._last_report = ""

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

        highlight_row.addWidget(font_tag)
        highlight_row.addWidget(btn_dec)
        highlight_row.addWidget(self.font_size_label)
        highlight_row.addWidget(btn_inc)

        self.results = QTextEdit()
        self.results.setReadOnly(True)
        self.results.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.results.setPlaceholderText("Press Solve to see the step-by-step solution here.")
        results_box = QGroupBox("Results")
        results_layout = QVBoxLayout(results_box)
        results_layout.addLayout(highlight_row)
        results_layout.addWidget(self.results, 1)

        right = QSplitter(Qt.Vertical)
        right.addWidget(draw_box)
        right.addWidget(results_box)
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 2)
        right.setSizes([450, 350])

        main = QSplitter(Qt.Horizontal)
        main.addWidget(input_box)
        main.addWidget(right)
        main.setStretchFactor(0, 2)
        main.setStretchFactor(1, 3)
        main.setSizes([440, 760])

        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.addWidget(main)

        self._reset_highlight_choices()

    # ============================================================ public API

    def get_graph(self) -> Graph:
        """Build a Graph from the table and the two dropdowns.

        Raises ValueError with a friendly message if the input is not valid.
        """
        if self._timer.isActive():
            self._timer.stop()
            self._live_update()

        rows, problems = self._read_rows()
        if problems:
            raise ValueError(problems[0][2])
        if not rows:
            raise ValueError("Add at least one branch (From, To and Gain) to the table.")

        source = self.source_combo.currentText().strip()
        sink = self.sink_combo.currentText().strip()
        if not source:
            raise ValueError("Choose the input (source) node.")
        if not sink:
            raise ValueError("Choose the output (sink) node.")

        graph = Graph(source_node=source, sink_node=sink)
        for name in self._nodes_from_rows(rows):
            graph.add_node(name)
        for _r, src, dst, gain in rows:
            graph.add_edge(src, dst, gain)
        return graph

    def set_graph(self, g: Graph):
        """Show a Graph in the table, the dropdowns and the drawing."""
        self._loading = True
        self.table.setRowCount(0)
        for e in g.edges:
            self._append_row(e.source, e.target, fmt(e.gain))
        self._append_row("", "", "")
        self._loading = False

        self._source_chosen = bool(g.source_node)
        self._sink_chosen = bool(g.sink_node)
        self.canvas.reset_positions()
        self._live_update(prefer_source=g.source_node, prefer_sink=g.sink_node, fit=True)
        self.results.clear()

    def clear(self):
        """Empty the table, the drawing and the results."""
        self._source_chosen = False
        self._sink_chosen = False
        self._reset_table()
        self.canvas.clear()
        self.results.clear()
        self._live_update(fit=True)

    def _toggle_animation(self):
        is_on = self.canvas.toggle_animation()
        self.anim_btn.setText("⏸ Pause flow" if is_on else "▶ Animate flow")

    def _on_table_selection_changed(self):
        if self._loading:
            return
        selected_rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not selected_rows:
            return
        r = selected_rows[0]
        src = self._cell(r, 0)
        dst = self._cell(r, 1)
        gain = self._cell(r, 2)
        if src and dst:
            from core.models import Edge
            val = parse_gain(gain) if gain else 1.0
            dummy_edge = Edge(src, dst, val)
            self.canvas.set_highlight([dummy_edge], [src, dst])

    def _on_canvas_edge_clicked(self, src, dst, gain):
        for r in range(self.table.rowCount()):
            if self._cell(r, 0) == src and self._cell(r, 1) == dst:
                self.table.selectRow(r)
                break

    def _on_canvas_node_clicked(self, node):
        if not self.source_combo.currentText().strip():
            idx = self.source_combo.findText(node)
            if idx >= 0:
                self.source_combo.setCurrentIndex(idx)
        elif not self.sink_combo.currentText().strip() and node != self.source_combo.currentText().strip():
            idx = self.sink_combo.findText(node)
            if idx >= 0:
                self.sink_combo.setCurrentIndex(idx)

    def solve(self):
        """Run the Part 1 pipeline and show the report."""
        try:
            graph = self.get_graph()
        except ValueError as e:
            self._warn(str(e))
            return

        try:
            result = solve_graph(graph)
        except ValueError as e:
            self._warn(str(e))
            return
        except ModuleNotReady as e:
            self._show_partial(graph, str(e))
            return
        except Exception as e:                      # keep the app alive on any bug
            QMessageBox.critical(self, "Unexpected error", f"{type(e).__name__}: {e}")
            return

        self._last_report = result.report
        self.results.setHtml(self._format_mason_report_html(result.report))
        self._fill_highlight_choices(result.paths, result.loops)

    def _inc_font(self):
        if self._font_size < 26:
            self._font_size += 1
            self.font_size_label.setText(f"{self._font_size}px")
            if self._last_report:
                self.results.setHtml(self._format_mason_report_html(self._last_report))

    def _dec_font(self):
        if self._font_size > 10:
            self._font_size -= 1
            self.font_size_label.setText(f"{self._font_size}px")
            if self._last_report:
                self.results.setHtml(self._format_mason_report_html(self._last_report))

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self.canvas.set_theme(is_dark)
        if hasattr(self, 'font_size_label'):
            accent = "#CBA6F7" if is_dark else "#6366F1"
            self.font_size_label.setStyleSheet(f"color:{accent}; font-weight:bold; font-size:12px; min-width:32px;")
        if self._last_report:
            self.results.setHtml(self._format_mason_report_html(self._last_report))

    def _format_mason_report_html(self, report_text):
        if not report_text.strip():
            return f"<div style='color:#6C7086; font-style:italic; font-size:{self._font_size}px; padding:8px;'>Press Solve to see the step-by-step solution here.</div>"

        # Theme sensitive colors
        if self._is_dark:
            col_text = "#CDD6F4"
            col_card_bg = "#181825"
            col_card_border = "#313244"
            col_accent = "#CBA6F7"
            col_res_bg = "#1C3B2B"
            col_res_border = "#2E6044"
            col_res_text = "#A6E3A1"
            col_path = "#89DCEB"
            col_loop = "#FAB387"
        else:
            col_text = "#0F172A"
            col_card_bg = "#FFFFFF"
            col_card_border = "#CBD5E1"
            col_accent = "#6366F1"
            col_res_bg = "#ECFDF5"
            col_res_border = "#6EE7B7"
            col_res_text = "#065F46"
            col_path = "#0284C7"
            col_loop = "#D97706"

        fs = self._font_size
        lines = report_text.splitlines()
        html = [f"<div style=\"font-family:'Segoe UI',-apple-system,sans-serif; color:{col_text}; font-size:{fs}px; line-height:1.6;\">"]

        for line in lines:
            line_str = line.strip()
            if not line_str:
                html.append("<div style='height:8px;'></div>")
            elif any(line_str.startswith(f"{i}.") for i in range(1, 10)):
                html.append(f"<div style='background-color:{col_card_bg}; border:1px solid {col_card_border}; color:{col_accent}; font-weight:bold; font-size:{fs}px; padding:8px 14px; border-radius:10px; margin-top:12px; margin-bottom:6px;'>✦ {line_str}</div>")
            elif "RESULT:" in line_str:
                html.append(f"<div style='background-color:{col_res_bg}; border:1.5px solid {col_res_border}; color:{col_res_text}; font-weight:bold; font-size:{fs+1}px; font-family:Consolas,monospace; padding:12px 16px; border-radius:10px; margin:12px 0;'>{line_str}</div>")
            elif line_str.startswith("P") and ":" in line_str:
                html.append(f"<div style='color:{col_path}; font-weight:bold; font-size:{fs}px; font-family:Consolas,monospace; margin-top:5px; padding-left:8px;'>{line}</div>")
            elif line_str.startswith("L") and ":" in line_str:
                html.append(f"<div style='color:{col_loop}; font-weight:bold; font-size:{fs}px; font-family:Consolas,monospace; margin-top:5px; padding-left:8px;'>{line}</div>")
            elif ("M" in line_str or "Δ" in line_str or "T =" in line_str) and "=" in line_str:
                html.append(f"<div style='color:{col_accent}; font-size:{fs}px; font-family:Consolas,monospace; padding-left:12px; margin-top:3px;'>{line}</div>")
            else:
                html.append(f"<div style='color:{col_text}; font-size:{fs}px; font-family:Consolas,monospace; padding-left:8px;'>{line}</div>")

        html.append("</div>")
        return "".join(html)

    # ============================================================ table input

    def _reset_table(self):
        self._loading = True
        self.table.setRowCount(0)
        self._append_row("", "", "")
        self._loading = False

    def _append_row(self, src="", dst="", gain=""):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, text in enumerate((src, dst, gain)):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, c, item)

    def _add_branch(self):
        self._loading = True
        self._append_row()
        self._loading = False
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        self.table.editItem(self.table.item(self.table.rowCount() - 1, 0))

    def _delete_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows and self.table.currentRow() >= 0:
            rows = [self.table.currentRow()]
        self._loading = True
        for r in rows:
            self.table.removeRow(r)
        if self.table.rowCount() == 0:
            self._append_row()
        self._loading = False
        self._live_update()

    def _on_item_changed(self, item):
        if self._loading:
            return
        last = self.table.rowCount() - 1
        if item.row() == last and all(self._cell(last, c) for c in range(3)):
            self._loading = True          # a spare empty row appears automatically
            self._append_row()
            self._loading = False
        self._timer.start()

    def _cell(self, row, col):
        item = self.table.item(row, col)
        return item.text().strip() if item else ""

    def _read_rows(self):
        """Read the table.

        Returns (rows, problems):
          rows     : [(row_index, from, to, gain_text)] for every valid row
          problems : [(row_index, column, message)] for rows that are not valid
        Completely empty rows are ignored.
        """
        rows, problems = [], []
        for r in range(self.table.rowCount()):
            cells = [self._cell(r, c) for c in range(3)]
            if not any(cells):
                continue
            src, dst, gain = cells

            missing = False
            for col, (name, value) in enumerate(zip(("From", "To", "Gain"), cells)):
                if not value:
                    problems.append((r, col, f"Row {r + 1}: '{name}' is empty."))
                    missing = True
            if missing:
                continue

            try:
                value = parse_gain(gain)
            except ValueError:
                problems.append((r, 2, f"Row {r + 1}: the gain '{gain}' is not a number. "
                                       f"Use a form like 2, -0.5 or 3/4."))
                continue
            if value == 0:
                problems.append((r, 2, f"Row {r + 1}: a gain of 0 means there is no branch. "
                                       f"Delete the row or use a non-zero gain."))
                continue
            rows.append((r, src, dst, gain))
        return rows, problems

    @staticmethod
    def _nodes_from_rows(rows):
        """Node names in order of first appearance."""
        nodes = []
        for _r, src, dst, _g in rows:
            for name in (src, dst):
                if name not in nodes:
                    nodes.append(name)
        return nodes

    def _mark_problems(self, problems):
        """Tint the cells that need fixing and show the first problem below the table."""
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            for c in range(3):
                item = self.table.item(r, c)
                if item:
                    item.setBackground(QBrush())
                    item.setToolTip("")
        for r, c, message in problems:
            item = self.table.item(r, c)
            if item:
                item.setBackground(BAD_CELL)
                item.setToolTip(message)
        self.table.blockSignals(False)

        if not problems:
            self.problem_label.setText("")
        else:
            extra = f"  (+{len(problems) - 1} more)" if len(problems) > 1 else ""
            self.problem_label.setText(problems[0][2] + extra)

    # ================================================== dropdowns and drawing

    def _source_picked(self, _index):
        self._source_chosen = True

    def _sink_picked(self, _index):
        self._sink_chosen = True

    def _refresh_combos(self, nodes, prefer_source=None, prefer_sink=None):
        """Fill the input/output dropdowns, keeping the user's choice when possible."""
        specs = (
            (self.source_combo, prefer_source, self._source_chosen, 0),
            (self.sink_combo, prefer_sink, self._sink_chosen, -1),
        )
        for combo, prefer, chosen, default_index in specs:
            current = prefer or (combo.currentText() if chosen else "")
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(nodes)
            if current in nodes:
                combo.setCurrentText(current)
            elif nodes and (default_index == 0 or len(nodes) > 1):
                combo.setCurrentIndex(default_index % len(nodes))
            else:
                combo.setCurrentIndex(-1)
            combo.blockSignals(False)

    def _live_update(self, prefer_source=None, prefer_sink=None, fit=False):
        """Redraw from the table. Rows with mistakes are skipped and marked."""
        rows, problems = self._read_rows()
        nodes = self._nodes_from_rows(rows)
        self._refresh_combos(nodes, prefer_source, prefer_sink)
        self._mark_problems(problems)

        edges = [(src, dst, gain) for _r, src, dst, gain in rows]
        self.canvas.set_graph_data(nodes, edges,
                                   self.source_combo.currentText(),
                                   self.sink_combo.currentText(), fit=fit)
        self._reset_highlight_choices()

    # ============================================================== results

    def _reset_highlight_choices(self):
        self.highlight_combo.blockSignals(True)
        self.highlight_combo.clear()
        self.highlight_combo.addItem("None", None)
        self.highlight_combo.blockSignals(False)
        self.canvas.clear_highlight()

    def _fill_highlight_choices(self, paths, loops):
        self.highlight_combo.blockSignals(True)
        self.highlight_combo.clear()
        self.highlight_combo.addItem("None", None)
        for p in paths:
            nodes = getattr(p, "nodes", None)
            if nodes:
                self.highlight_combo.addItem(f"{p.label}:  " + " \u2192 ".join(nodes), p)
        for lp in loops:
            nodes = getattr(lp, "nodes", None)
            if nodes:
                self.highlight_combo.addItem(f"{lp.label}:  " + " \u2192 ".join(list(nodes) + [nodes[0]]), lp)
        self.highlight_combo.blockSignals(False)
        self.canvas.clear_highlight()

    def _on_highlight_changed(self, index):
        obj = self.highlight_combo.itemData(index)
        if obj is None:
            self.canvas.clear_highlight()
        else:
            self.canvas.set_highlight(getattr(obj, "edges", []), getattr(obj, "nodes", []))

    def _show_partial(self, graph, message):
        """A teammate's module is not merged yet: show what is already available."""
        lines = [f"{message}", "The full Mason report will appear here once it is merged.", ""]
        paths, loops = [], []
        try:
            from core.paths_loops import find_forward_paths, find_loops
            paths = find_forward_paths(graph)
            loops = find_loops(graph)
        except ImportError:
            pass
        except Exception as e:
            lines.append(f"(Could not list paths and loops: {e})")

        if paths or loops:
            lines.append("Forward paths:")
            lines += [f"  {p.gain_str}" for p in paths] or ["  none"]
            lines.append("")
            lines.append("Individual loops:")
            lines += [f"  {lp.gain_str}" for lp in loops] or ["  none"]
        self.results.setHtml(self._format_mason_report_html("\n".join(lines)))
        self._fill_highlight_choices(paths, loops)

    # ================================================================ files

    def _warn(self, message):
        QMessageBox.warning(self, "Please check your input", message)

    def _load_example(self):
        files = sorted(EXAMPLES_DIR.glob("*.json")) if EXAMPLES_DIR.is_dir() else []
        if not files:
            self.set_graph(Graph.from_dict(BUILTIN_EXAMPLE))
            return
        menu = QMenu(self)
        for f in files:
            menu.addAction(f.stem).setData(str(f))
        chosen = menu.exec_(self.example_btn.mapToGlobal(self.example_btn.rect().bottomLeft()))
        if chosen is not None:
            self._load_file(chosen.data())

    def _load_file(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                self.set_graph(Graph.from_dict(json.load(f)))
        except Exception as e:
            QMessageBox.critical(self, "Could not load the graph", str(e))

    def _save_graph(self):
        try:
            graph = self.get_graph()
        except ValueError as e:
            self._warn(str(e))
            return
        start = str(EXAMPLES_DIR / "my_graph.json") if EXAMPLES_DIR.is_dir() else "my_graph.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save graph", start, "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(graph.to_dict(), f, indent=2)
        except OSError as e:
            QMessageBox.critical(self, "Could not save the graph", str(e))

    def _export_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export image", "signal_flow_graph.png",
                                              "PNG image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            if not self.canvas.export_image(path):
                raise OSError("The image could not be written.")
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Could not export the image", str(e))
