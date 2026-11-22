# Mason-Routh Solver

CSE 341: Fundamentals of Control Systems, Programming Assignment (Level 3).
Alexandria University, Faculty of Engineering, Computer and Systems Engineering Department.

A desktop application with two tools:

- **Part 1: Signal Flow Graphs.** Enter nodes, branches and numeric gains. The program draws the graph,
  lists forward paths and loops, finds non-touching loop combinations, computes the graph determinant
  and path cofactors, and applies Mason's gain formula, showing every step.
- **Part 2: Routh Stability Criterion.** Enter a characteristic polynomial. The program builds the Routh
  table with calculation steps, classifies stability, counts right-half-plane poles, and verifies the
  count against numerically computed roots.

## Requirements

- Python 3.10 or newer
- Git

## Run from source

```bash
git clone https://github.com/shahdkhaled-21/mason-routh-solver.git
cd mason-routh-solver
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash). Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Run the executable

Double-click `MasonRouthSolver.exe`. No Python installation is needed.

## Run the tests

```bash
pytest
```

## Project structure

```
main.py                 entry point
core/
  graph.py              Graph and Edge data structures, gain parsing, JSON save/load
  models.py             Path, Loop, NonTouchingGroup result structures
  paths_loops.py        forward paths and loops
  mason.py              non-touching loops, determinant, cofactors, Mason's formula
  pipeline.py           connects the Part 1 steps
  routh.py              Routh table, stability, root verification
gui/
  main_window.py        main window with two tabs
  sfg_tab.py            Part 1 input, drawing and results
  routh_tab.py          Part 2 input and results
examples/               sample graphs (JSON)
tests/                  unit tests
docs/                   report and screenshots
```

## How to use

### Part 1: Signal Flow Graph
1. Enter the nodes, branches (from, to, gain), the input node and the output node.
2. Click **Solve**.
3. Read the results: forward paths, loops, non-touching loops, the determinant and each cofactor,
   and the final transfer function from Mason's formula.

### Part 2: Routh Stability
1. Enter the characteristic polynomial.
2. Click **Solve**.
3. Read the Routh table, the calculation steps, the stability verdict and the numerical root check.

(Detailed screenshots are added in the final report.)
