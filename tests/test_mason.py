"""Tests for core/mason.py """

import json
import random
from fractions import Fraction
from pathlib import Path

import pytest

from core.graph import Graph
from core.paths_loops import find_forward_paths, find_loops
from core.mason import (non_touching_groups, compute_delta, compute_cofactor,
                        transfer_function, mason_report, transfer_by_node_equations)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def build(nodes, edges, source, sink):
    """Make a Graph from a node list and (from, to, gain) tuples."""
    g = Graph(source_node=source, sink_node=sink)
    for n in nodes:
        g.add_node(n)
    for a, b, gain in edges:
        g.add_edge(a, b, gain)
    return g


def load(name):
    with open(EXAMPLES / name, encoding="utf-8") as f:
        return Graph.from_dict(json.load(f))


def solve(g):
    """Run the whole Mason chain on a graph and return every intermediate result."""
    paths, loops = find_forward_paths(g), find_loops(g)
    groups = non_touching_groups(loops)
    delta = compute_delta(loops, groups)[0]
    cofactors = [compute_cofactor(p, loops, groups)[0] for p in paths]
    return paths, loops, groups, delta, cofactors, transfer_function(paths, loops, groups)


def check_with_node_equations(g):
    """Mason's answer must equal the answer from solving the node equations."""
    t = solve(g)[-1]
    assert float(t) == pytest.approx(transfer_by_node_equations(g))



def test_example1():
    # one loop 
    # both paths touch the loop
    g = load("example1.json")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert groups == []
    assert delta == 3
    assert cofactors == [1, 1]
    assert t == Fraction(10, 3)
    check_with_node_equations(g)


def test_example2():
    # loops: A->B->C->A = 24, B->B = 6, D->D = 7
    # non-touching pairs: (L1, L3) = 168 and (L2, L3) = 42
    # Δ = 1 - 37 + 210 = 174, Δ1 = 1, T = 30 / 174 = 5/29
    g = load("example2.json")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert sorted(gr.gain for gr in groups) == [42, 168]
    assert delta == 174
    assert cofactors == [1]
    assert t == Fraction(5, 29)
    check_with_node_equations(g)




def test_no_loops():
    # no loops, so Δ = 1 and T is just the path gain 2 x 3 = 6
    g = build(["R", "A", "C"], [("R", "A", 2), ("A", "C", 3)], "R", "C")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert loops == [] and groups == []
    assert delta == 1 and t == 6


def test_all_loops_touching():
    # loops A->B->A (-2) and B->C->B (-3) share node B: no pairs
    # Δ = 1 - (-2 - 3) = 6, T = 1 / 6
    g = build(["R", "A", "B", "C"],
              [("R", "A", 1), ("A", "B", 1), ("B", "A", -2), ("B", "C", 1), ("C", "B", -3)],
              "R", "C")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert len(loops) == 2 and groups == []
    assert delta == 6 and t == Fraction(1, 6)
    check_with_node_equations(g)


def test_three_non_touching_loops():
    # self-loops 1/2, 1/3, -1 on A, B, C: 3 pairs and 1 triple
    # Δ = (1 - 1/2)(1 - 1/3)(1 + 1) = 2/3, T = 6 / (2/3) = 9
    g = build(["R", "A", "B", "C", "Y"],
              [("R", "A", 1), ("A", "B", 2), ("B", "C", 3), ("C", "Y", 1),
               ("A", "A", "1/2"), ("B", "B", "1/3"), ("C", "C", -1)],
              "R", "Y")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert sorted(len(gr.loops) for gr in groups) == [2, 2, 2, 3]
    assert delta == Fraction(2, 3) and t == 9
    check_with_node_equations(g)


def test_cofactor_keeps_loops_not_touching_the_path():
    # P1 = R->A->C (2) does not touch loop B->B (-4): Δ1 = 1 + 4 = 5
    # P2 = R->B->C (3) does not touch loop A->A (-1): Δ2 = 1 + 1 = 2
    # Δ = 1 - (-1 - 4) + (4) = 10, T = (2x5 + 3x2) / 10 = 8/5
    g = build(["R", "A", "B", "C"],
              [("R", "A", 1), ("A", "C", 2), ("R", "B", 1), ("B", "C", 3),
               ("A", "A", -1), ("B", "B", -4)],
              "R", "C")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert cofactors == [5, 2]
    assert delta == 10 and t == Fraction(8, 5)
    check_with_node_equations(g)


def test_negative_and_fractional_gains():
    # loop A->B->A = 3/4 x (-2) = -3/2, Δ = 5/2
    # path = -1/2 x 3/4 x -1/2 = 3/16, T = (3/16) / (5/2) = 3/40
    g = build(["R", "A", "B", "C"],
              [("R", "A", "-1/2"), ("A", "B", "3/4"), ("B", "A", -2), ("B", "C", "-0.5")],
              "R", "C")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert delta == Fraction(5, 2) and t == Fraction(3, 40)
    check_with_node_equations(g)


def test_delta_zero():
    # self-loop of gain 1: Δ = 1 - 1 = 0, so T is undefined (no crash)
    g = build(["R", "A", "C"], [("R", "A", 1), ("A", "A", 1), ("A", "C", 1)], "R", "C")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert delta == 0 and t is None
    assert "undefined" in mason_report(paths, loops, groups)


def test_no_forward_path():
    g = build(["R", "A", "C"], [("R", "A", 1), ("C", "A", 1)], "R", "C")
    paths, loops, groups, delta, cofactors, t = solve(g)
    assert paths == [] and t == 0
    assert "no forward path" in mason_report(paths, loops, groups)


# report

def test_report_order_and_values():
    g = load("example2.json")
    paths, loops = find_forward_paths(g), find_loops(g)
    text = mason_report(paths, loops, non_touching_groups(loops))
    headings = ["1. FORWARD PATHS", "2. INDIVIDUAL LOOPS", "3. NON-TOUCHING",
                "4. DETERMINANT", "5. COFACTORS", "6. MASON"]
    positions = [text.index(h) for h in headings]
    assert positions == sorted(positions)
    assert "Δ = 1 - (24 + 6 + 7) + (168 + 42)" in text
    assert "174" in text and "5/29" in text and "excluded" in text


# many random graphs, two methods

def test_random_graphs_agree_with_node_equations():
    rng = random.Random(341)
    for _ in range(200):
        names = [f"N{i}" for i in range(rng.randint(3, 6))]
        edges = [(rng.choice(names), rng.choice(names),
                  Fraction(rng.choice([-3, -2, -1, 1, 2, 3]), rng.choice([1, 2, 3])))
                 for _ in range(rng.randint(3, 10))]
        g = build(names, edges, names[0], names[-1])
        if solve(g)[-1] is not None:         # skip the rare graphs with Δ = 0
            check_with_node_equations(g)
