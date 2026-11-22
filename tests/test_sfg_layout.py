"""Tests for the SFG drawing code (gui/layout.py) and the SFG tab (gui/sfg_tab.py).

The layout tests are pure Python. The tab tests run Qt without a screen and are
skipped automatically if PyQt5 is not installed.
"""
import json
import math
import os
from pathlib import Path

import pytest

from gui.layout import (choose_offset, compute_layout, edge_curve_params,
                        is_clear, quad_at, quad_points, route_edges,
                        self_loop_points, cubic_at)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


# ------------------------------------------------------------------ layout

def test_source_left_sink_right():
    nodes = ["R", "A", "B", "C"]
    edges = [("R", "A"), ("A", "B"), ("B", "C"), ("B", "A"), ("A", "C")]
    pos = compute_layout(nodes, edges, "R", "C")
    assert pos["R"][0] == min(x for x, _ in pos.values())
    assert pos["C"][0] == max(x for x, _ in pos.values())
    assert pos["R"][0] < pos["A"][0] < pos["B"][0] < pos["C"][0]


def test_sink_is_last_column_even_with_outgoing_edge():
    nodes = ["R", "C", "A"]
    edges = [("R", "C"), ("C", "A")]          # sink C reaches A
    pos = compute_layout(nodes, edges, "R", "C")
    assert pos["C"][0] > pos["A"][0]


def test_same_column_nodes_do_not_overlap():
    nodes = ["R", "A", "B", "C"]
    edges = [("R", "A"), ("R", "B"), ("A", "C"), ("B", "C")]
    pos = compute_layout(nodes, edges, "R", "C")
    assert pos["A"][0] == pos["B"][0]
    assert pos["A"][1] != pos["B"][1]


def test_unreachable_node_is_placed():
    pos = compute_layout(["R", "X", "C"], [("R", "C")], "R", "C")
    assert set(pos) == {"R", "X", "C"}


def test_no_source_chosen_does_not_crash():
    pos = compute_layout(["A", "B"], [("A", "B")], "", "")
    assert set(pos) == {"A", "B"}


# ------------------------------------------------------------ edge shapes

def test_edge_kinds():
    pos = {"R": (0, 0), "A": (170, 0), "B": (340, 0)}
    edges = [("R", "A"), ("A", "B"), ("B", "R"), ("A", "A")]
    params = edge_curve_params(edges, pos)
    assert params[0] == ("curve", 0.0, 0)          # plain forward edge: straight
    assert params[1] == ("curve", 0.0, 0)
    assert params[2][0] == "curve" and params[2][1] > 0   # feedback edge bends
    assert params[3] == ("self", 0.0, 0)


def test_opposite_pair_bends_both():
    pos = {"A": (0, 0), "B": (170, 0)}
    params = edge_curve_params([("A", "B"), ("B", "A")], pos)
    assert params[0][1] > 0 and params[1][1] > 0


def test_parallel_edges_get_different_offsets():
    pos = {"A": (0, 0), "B": (170, 0)}
    params = edge_curve_params([("A", "B"), ("A", "B")], pos)
    assert params[0][1] != params[1][1]


def test_second_self_loop_is_bigger():
    pos = {"A": (0, 0)}
    params = edge_curve_params([("A", "A"), ("A", "A")], pos)
    assert [p[2] for p in params] == [0, 1]
    small = self_loop_points((0, 0), 24, 0)
    big = self_loop_points((0, 0), 24, 1)
    assert big[1][1] < small[1][1]                 # control point is higher


def test_quad_points_end_on_circle_edges():
    start, ctrl, end = quad_points((0, 0), 24, (170, 0), 30, 40)
    assert math.hypot(*start) == pytest.approx(24)
    assert math.hypot(end[0] - 170, end[1]) == pytest.approx(30)


def test_edge_avoids_node_in_the_way():
    a, b, blocker = (0, 0), (340, 0), (170, 0, 24)
    assert not is_clear(*quad_points(a, 24, b, 24, 0), [blocker])
    offset = choose_offset(a, 24, b, 24, 0.0, [blocker])
    assert offset != 0
    assert is_clear(*quad_points(a, 24, b, 24, offset), [blocker])


def _curve_points(pos, radius, edge, offset, n=40):
    a, b = pos[edge[0]], pos[edge[1]]
    geo = quad_points(a, radius[edge[0]], b, radius[edge[1]], offset)
    return [quad_at(*geo, i / n) for i in range(1, n)]


def _min_gap_away_from(p_nodes, pts1, pts2, pos, radius, shared):
    zones = [(pos[n], radius[n] + 30) for n in shared]
    best = 1e9
    for p in pts1:
        if any(math.hypot(p[0] - z[0][0], p[1] - z[0][1]) < z[1] for z in zones):
            continue
        for q in pts2:
            best = min(best, math.hypot(p[0] - q[0], p[1] - q[1]))
    return best


def test_route_edges_separates_skip_edge_from_bent_pair():
    # example1: A->B has a partner B->A, and A->C must dodge node B.
    pos = {"R": (0, 0), "A": (170, 0), "B": (340, 0), "C": (510, 0)}
    radius = {n: 24.0 for n in pos}
    edges = [("R", "A"), ("A", "B"), ("B", "C"), ("B", "A"), ("A", "C")]
    routed = route_edges(edges, pos, radius)
    ab = _curve_points(pos, radius, edges[1], routed[1][1])
    ac = _curve_points(pos, radius, edges[4], routed[4][1])
    assert _min_gap_away_from(None, ab, ac, pos, radius, {"A"}) >= 12


def test_route_edges_no_edge_crosses_a_node():
    pos = {"R": (0, 0), "A": (170, 0), "B": (340, 0), "C": (510, 0), "D": (680, 0)}
    radius = {n: 24.0 for n in pos}
    edges = [("R", "A"), ("A", "B"), ("B", "C"), ("C", "D"),
             ("R", "C"), ("A", "D"), ("R", "D"), ("D", "A")]
    routed = route_edges(edges, pos, radius)
    for (s, d), (kind, offset, _k, _t) in zip(edges, routed):
        others = [(pos[n][0], pos[n][1], radius[n]) for n in pos if n not in (s, d)]
        assert is_clear(*quad_points(pos[s], 24, pos[d], 24, offset), others)


def test_route_edges_leaves_plain_edges_straight():
    pos = {"R": (0, 0), "A": (170, 0)}
    radius = {"R": 24.0, "A": 24.0}
    assert route_edges([("R", "A")], pos, radius) == [("curve", 0.0, 0, 0.5)]


def test_self_loop_moves_away_from_feedback_edge():
    # R A B C D in a row; B has a self-loop and C->A arcs over the top of B.
    pos = {"R": (0, 0), "A": (170, 0), "B": (340, 0), "C": (510, 0), "D": (680, 0)}
    radius = {n: 24.0 for n in pos}
    edges = [("R", "A"), ("A", "B"), ("B", "C"), ("C", "A"), ("B", "B"),
             ("C", "D"), ("D", "D")]
    routed = route_edges(edges, pos, radius)

    kind, rotation, k, _t = routed[4]
    assert kind == "self" and rotation != 0          # not drawn on top of C->A
    loop = self_loop_points(pos["B"], 24.0, k, rotation)
    loop_label = cubic_at(*loop, routed[4][3])

    feedback = quad_points(pos["C"], 24.0, pos["A"], 24.0, routed[3][1])
    fb_label = quad_at(*feedback, routed[3][3])
    fb_points = [quad_at(*feedback, i / 40) for i in range(1, 40)]

    assert math.hypot(loop_label[0] - fb_label[0], loop_label[1] - fb_label[1]) > 36
    assert all(math.hypot(loop_label[0] - x, loop_label[1] - y) > 14 for x, y in fb_points)


def test_self_loop_stays_above_when_nothing_is_in_the_way():
    pos = {"R": (0, 0), "A": (170, 0)}
    radius = {n: 24.0 for n in pos}
    routed = route_edges([("R", "A"), ("A", "A")], pos, radius)
    assert routed[1][:3] == ("self", 0.0, 0)


def test_self_loop_never_hits_another_node():
    pos = {"A": (0, 0), "B": (60, 0)}                 # nodes very close together
    radius = {n: 24.0 for n in pos}
    kind, rotation, k, _t = route_edges([("A", "A")], pos, radius)[0]
    loop = self_loop_points(pos["A"], 24.0, k, rotation)
    for i in range(1, 16):
        x, y = cubic_at(*loop, i / 16)
        assert math.hypot(x - 60, y) >= 24 + 10 - 1e-6


# ------------------------------------------------------------------ the tab

@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tab(qapp):
    from gui.sfg_tab import SFGTab
    return SFGTab()


def fill(tab, rows):
    """Type rows into the table the way a user would."""
    tab.clear()
    for i, (src, dst, gain) in enumerate(rows):
        for c, text in enumerate((src, dst, gain)):
            tab.table.item(i, c).setText(text)


@pytest.mark.parametrize("name", ["example1.json", "example2.json"])
def test_set_graph_then_get_graph_round_trip(tab, name):
    from core.graph import Graph
    with open(EXAMPLES / name, encoding="utf-8") as f:
        graph = Graph.from_dict(json.load(f))
    tab.set_graph(graph)
    assert tab.get_graph() == graph


def test_typed_rows_become_a_graph(tab):
    fill(tab, [("R", "A", "1"), ("A", "C", "3/4")])
    g = tab.get_graph()
    assert g.nodes == ["R", "A", "C"]
    assert g.source_node == "R" and g.sink_node == "C"
    assert [str(e.gain) for e in g.edges] == ["1", "3/4"]


def test_empty_table_gives_friendly_error(tab):
    with pytest.raises(ValueError, match="at least one branch"):
        tab.get_graph()


def test_bad_gain_gives_friendly_error(tab):
    fill(tab, [("R", "A", "abc")])
    with pytest.raises(ValueError, match="not a number"):
        tab.get_graph()


def test_empty_field_gives_friendly_error(tab):
    fill(tab, [("R", "", "2")])
    with pytest.raises(ValueError, match="'To' is empty"):
        tab.get_graph()


def test_zero_gain_gives_friendly_error(tab):
    fill(tab, [("R", "A", "0")])
    with pytest.raises(ValueError, match="gain of 0"):
        tab.get_graph()


def test_missing_sink_gives_friendly_error(tab):
    fill(tab, [("R", "R", "2")])                 # only one node, so no output node to pick
    with pytest.raises(ValueError, match="output"):
        tab.get_graph()


def test_drawing_has_every_node_and_edge(tab):
    with open(EXAMPLES / "example2.json", encoding="utf-8") as f:
        from core.graph import Graph
        tab.set_graph(Graph.from_dict(json.load(f)))
    assert set(tab.canvas._node_items) == {"R", "A", "B", "C", "D"}
    assert len(tab.canvas._edge_items) == 7        # includes two self-loops


def test_export_image_writes_png(tab, tmp_path):
    from core.graph import Graph
    with open(EXAMPLES / "example1.json", encoding="utf-8") as f:
        tab.set_graph(Graph.from_dict(json.load(f)))
    out = tmp_path / "graph.png"
    assert tab.canvas.export_image(str(out))
    assert out.stat().st_size > 0


def test_export_empty_canvas_raises(tab):
    with pytest.raises(ValueError):
        tab.canvas.export_image("nothing.png")


def test_labels_do_not_sit_on_other_edges_or_nodes():
    pos = {"R": (0, 0), "A": (170, 0), "B": (340, 0), "C": (170, 110), "D": (510, 0)}
    radius = {n: 24.0 for n in pos}
    edges = [("R", "A"), ("A", "B"), ("B", "D"), ("R", "C"), ("C", "D"), ("C", "B")]
    routed = route_edges(edges, pos, radius)
    assert all(0.0 < r[3] < 1.0 for r in routed)
    for (s, d), (kind, offset, _k, t) in zip(edges, routed):
        label = quad_at(*quad_points(pos[s], 24.0, pos[d], 24.0, offset), t)
        for n, (nx, ny) in pos.items():
            assert math.hypot(label[0] - nx, label[1] - ny) > 24.0