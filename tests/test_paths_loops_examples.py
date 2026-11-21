"""Hand-verified results for the example graphs (checked against hand calculation)."""
import json
from fractions import Fraction
from pathlib import Path

from core.graph import Graph
from core.paths_loops import find_forward_paths, find_loops

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def load(name):
    with open(EXAMPLES / name, encoding="utf-8") as f:
        return Graph.from_dict(json.load(f))


def test_example1_paths_and_loops():
    g = load("example1.json")
    assert sorted(p.gain for p in find_forward_paths(g)) == [Fraction(4), Fraction(6)]
    assert [l.gain for l in find_loops(g)] == [Fraction(-2)]


def test_example2_paths_and_loops():
    g = load("example2.json")
    paths = find_forward_paths(g)
    loops = find_loops(g)
    assert [p.gain for p in paths] == [Fraction(30)]
    assert len(loops) == 3                     # triangle listed once, not three times
    assert sorted(l.gain for l in loops) == [Fraction(6), Fraction(7), Fraction(24)]
