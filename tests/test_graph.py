import json
from fractions import Fraction
from pathlib import Path

import pytest

from core.graph import Graph, Edge, parse_gain, fmt

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "example1.json"


def make_graph():
    g = Graph(source_node="R", sink_node="C")
    for n in ["R", "A", "B", "C"]:
        g.add_node(n)
    g.add_edge("R", "A", "1")
    g.add_edge("A", "B", "2")
    g.add_edge("B", "C", "3")
    return g


# ---------- parse_gain / fmt ----------

def test_parse_gain_integer():
    assert parse_gain("2") == Fraction(2)


def test_parse_gain_decimal():
    assert parse_gain("-0.5") == Fraction(-1, 2)


def test_parse_gain_fraction():
    assert parse_gain("3/4") == Fraction(3, 4)


def test_parse_gain_strips_spaces():
    assert parse_gain("  7 ") == Fraction(7)


@pytest.mark.parametrize("bad", ["abc", "", "1/0", "2x"])
def test_parse_gain_invalid(bad):
    with pytest.raises(ValueError):
        parse_gain(bad)


def test_fmt():
    assert fmt(Fraction(12)) == "12"
    assert fmt(Fraction(3, 4)) == "3/4"
    assert fmt(Fraction(-1, 2)) == "-1/2"


# ---------- nodes and edges ----------

def test_add_node_duplicate_fails():
    g = Graph()
    g.add_node("A")
    with pytest.raises(ValueError):
        g.add_node("A")


def test_add_node_empty_fails():
    g = Graph()
    with pytest.raises(ValueError):
        g.add_node("   ")


def test_add_edge_unknown_node_fails():
    g = Graph()
    g.add_node("A")
    with pytest.raises(ValueError):
        g.add_edge("A", "Z", "1")


def test_add_edge_stores_fraction():
    g = make_graph()
    assert g.edges[1] == Edge("A", "B", Fraction(2))


def test_remove_edge():
    g = make_graph()
    g.remove_edge(0)
    assert len(g.edges) == 2
    assert g.edges[0].source == "A"


def test_adjacency():
    g = make_graph()
    adj = g.adjacency()
    assert [e.target for e in adj["A"]] == ["B"]
    assert adj["C"] == []


def test_self_loop_allowed():
    g = make_graph()
    g.add_edge("B", "B", "-2")
    assert any(e.source == e.target == "B" for e in g.edges)


# ---------- validate ----------

def test_validate_ok():
    make_graph().validate()


def test_validate_no_nodes():
    with pytest.raises(ValueError):
        Graph().validate()


def test_validate_missing_source():
    g = make_graph()
    g.source_node = "X"
    with pytest.raises(ValueError):
        g.validate()


def test_validate_missing_sink():
    g = make_graph()
    g.sink_node = ""
    with pytest.raises(ValueError):
        g.validate()


def test_validate_source_equals_sink():
    g = make_graph()
    g.sink_node = "R"
    with pytest.raises(ValueError):
        g.validate()


def test_validate_zero_gain():
    g = make_graph()
    g.add_edge("C", "A", "0")
    with pytest.raises(ValueError):
        g.validate()


# ---------- JSON ----------

def test_round_trip():
    g = make_graph()
    g.add_edge("B", "A", "-0.5")
    assert Graph.from_dict(g.to_dict()) == g


def test_example_file_loads():
    with open(EXAMPLE, encoding="utf-8") as f:
        g = Graph.from_dict(json.load(f))
    g.validate()
    assert g.nodes == ["R", "A", "B", "C"]
    assert len(g.edges) == 5
    assert g.source_node == "R" and g.sink_node == "C"
