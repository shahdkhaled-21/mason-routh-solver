import sys
import types

import pytest

from core.graph import Graph
from core.pipeline import solve_graph, ModuleNotReady


def make_graph():
    g = Graph(source_node="R", sink_node="C")
    for n in ["R", "A", "C"]:
        g.add_node(n)
    g.add_edge("R", "A", "1")
    g.add_edge("A", "C", "2")
    return g


def test_invalid_graph_raises_value_error():
    g = make_graph()
    g.sink_node = "R"
    with pytest.raises(ValueError):
        solve_graph(g)


def test_missing_module_gives_friendly_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "core.paths_loops", None)   # simulate "not merged"
    with pytest.raises(ModuleNotReady):
        solve_graph(make_graph())


def test_pipeline_runs_with_fake_modules(monkeypatch):
    pl = types.ModuleType("core.paths_loops")
    pl.find_forward_paths = lambda g: ["P1"]
    pl.find_loops = lambda g: ["L1", "L2"]
    ms = types.ModuleType("core.mason")
    ms.non_touching_groups = lambda loops: ["G1"]
    ms.mason_report = lambda p, l, g: f"{len(p)} path, {len(l)} loops, {len(g)} group"
    monkeypatch.setitem(sys.modules, "core.paths_loops", pl)
    monkeypatch.setitem(sys.modules, "core.mason", ms)

    result = solve_graph(make_graph())
    assert result.paths == ["P1"]
    assert result.loops == ["L1", "L2"]
    assert result.groups == ["G1"]
    assert result.report == "1 path, 2 loops, 1 group"
