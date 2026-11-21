# Report Section: Architecture, Shared Data Structures, and Integration

**Author:** Shahd (Team Lead)
**Covers:** `core/graph.py`, `core/models.py`, `core/pipeline.py`, `gui/main_window.py`, `main.py`, packaging, tests, version control.

> Draft. Read it once and edit anything that does not match your own understanding before submitting.

---

## 1. Overall Architecture

The program is split into three layers:

1. **Core layer (`core/`)**: all mathematics, with no GUI code. It can be tested without opening a window.
2. **GUI layer (`gui/`)**: PyQt5 widgets that collect input, display results, and draw the graph.
3. **Entry point (`main.py`)**: starts the application and opens the main window.

Part 1 runs as a pipeline. Each stage hands its result to the next:

```
Graph (user input)
  -> validate
  -> forward paths and loops          (core/paths_loops.py)
  -> non-touching loop groups          (core/mason.py)
  -> determinant, cofactors, Mason     (core/mason.py)
  -> formatted step-by-step report     (core/mason.py)
  -> shown in the GUI                  (gui/sfg_tab.py)
```

Part 2 (Routh) is independent of Part 1 and only shares the main window.

This separation allowed six people to work in parallel, because every module agrees on the same data structures defined at the start of the project.

---

## 2. Data Structures Used (shared contract)

All gains are stored as Python `fractions.Fraction`, so results such as 10/3 stay exact and never suffer floating-point rounding.

| Structure | File | Purpose |
|---|---|---|
| `Edge` | `core/graph.py` | One directed branch: `source`, `target`, `gain`. It is immutable (a frozen dataclass), so it can be safely stored in sets and shared. |
| `Graph` | `core/graph.py` | The whole signal flow graph: a list of node names, a list of `Edge` objects, the input (`source_node`) and output (`sink_node`). |
| `Path` | `core/models.py` | One forward path: label (`P1`), node list, edge list, gain (`M_i`), the gain as a readable product string, and a `node_set`. |
| `Loop` | `core/models.py` | One individual loop: label (`L1`), nodes in canonical rotation, edges, gain, product string, and a `node_set`. |
| `NonTouchingGroup` | `core/models.py` | A group of 2 or more mutually non-touching loops, with their combined gain and product string. |
| `SolveResult` | `core/pipeline.py` | The full Part 1 result: paths, loops, groups, and the formatted report. |

**Why `node_set` is a `frozenset`:** two loops (or a loop and a path) touch exactly when they share a node, so the touching test is a set intersection.

**Why a graph is stored as a node list plus an edge list:** it is the simplest form to validate, save to JSON, and edit from a table in the GUI. The `adjacency()` method builds a lookup of outgoing edges per node when the path and loop search needs it.

---

## 3. Main Modules and Code Explanation (lead's modules)

### 3.1 `core/graph.py`

| Function / method | Role |
|---|---|
| `parse_gain(text)` | Converts text such as `"2"`, `"-0.5"`, or `"3/4"` to a `Fraction`. Raises a `ValueError` with a clear message for invalid input (letters, empty text, division by zero). |
| `fmt(x)` | Formats a `Fraction` for display: `12` stays `12`, and `3/4` stays `3/4`. Used everywhere results are printed, so the whole program shows numbers the same way. |
| `Graph.add_node(name)` | Adds a node. Rejects empty and duplicate names. |
| `Graph.add_edge(src, dst, gain)` | Adds a branch. Rejects unknown nodes and invalid gains. Self-loops (`src == dst`) are allowed. |
| `Graph.remove_edge(index)` | Removes a branch by position. |
| `Graph.adjacency()` | Returns a dictionary from each node to its outgoing edges. Used by the paths and loops search. |
| `Graph.validate()` | Checks that the graph can be solved: it has nodes, the input and output nodes exist and differ, and no branch has zero gain. Raises a `ValueError` with a friendly message otherwise. |
| `Graph.to_dict()` / `from_dict()` | Convert to and from a plain dictionary, used for saving and loading JSON files. |

### 3.2 `core/models.py`

Contains only the dataclasses `Path`, `Loop`, and `NonTouchingGroup`. Having them in one agreed file meant the paths and loops engine, the Mason module, and the GUI could be written at the same time without waiting for each other.

### 3.3 `core/pipeline.py`

| Function | Role |
|---|---|
| `solve_graph(graph)` | The single entry point for Part 1. Validates the graph, then calls the path and loop finder, the non-touching group finder, and the report builder in order, and returns a `SolveResult`. The GUI calls only this function. |
| `_load(module, function)` | Looks up a teammate's function by name at run time. If the module has not been merged yet, it raises `ModuleNotReady` with a clear message instead of crashing. This let integration start before every module was finished. |

### 3.4 `gui/main_window.py` and `main.py`

`MainWindow` is a `QMainWindow` with two tabs (Signal Flow Graph and Routh Stability) and a File menu to load and save graphs as JSON. `main.py` creates the `QApplication`, shows the window, and starts the event loop.

### 3.5 Tests (`tests/`)

Automated tests (pytest) cover gain parsing, graph validation, the JSON round trip, the pipeline wiring, the paths and loops results, and end-to-end answers. Two hand-solved example graphs are used as reference cases:

| Graph | Forward paths | Loops | Determinant | Result |
|---|---|---|---|---|
| `example1.json` | M1 = 6, M2 = 4 | L1 = -2 | 3 | T = 10/3 |
| `example2.json` | M1 = 30 | L1 = 24, L2 = 6, L3 = 7 | 174 | T = 5/29 |

---

## 4. Algorithms Used (lead's part)

- **Gain parsing:** text is converted to an exact rational number through `Fraction`, which accepts integers, decimals, and fractions.
- **Graph validation:** a sequence of checks, each with its own error message, so the user learns exactly what to fix.
- **Pipeline orchestration:** a fixed order of stages in which each stage consumes the previous stage's output.
- **Touching test (used by the engine and Mason module):** two loops touch if their node sets intersect.

---

## 5. Version Control and Packaging

- **Git workflow:** the `main` branch holds working code only. Every member works on a `feature/...` branch and opens a pull request, which the lead reviews, runs locally, and merges.
- **Executable:** built with PyInstaller using

  ```
  pyinstaller --onefile --windowed --name MasonRouthSolver --collect-submodules core --collect-submodules gui main.py
  ```

  The two `--collect-submodules` options are needed because the pipeline loads teammates' modules by name at run time, which PyInstaller cannot detect on its own.

---

## 6. Setup and Run (for the user guide)

```bash
git clone https://github.com/shahdkhaled-21/mason-routh-solver.git
cd mason-routh-solver
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash). Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

To run the tests: `pytest`. To use the executable without Python: double-click `MasonRouthSolver.exe`.
