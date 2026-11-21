"""End-to-end check of the Part 1 pipeline against hand-verified answers.

Skipped automatically until core/mason.py (Mariem) is merged.
"""
import json
from pathlib import Path

import pytest

from core.graph import Graph
from core.pipeline import solve_graph, ModuleNotReady

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def solve(name):
    with open(EXAMPLES / name, encoding="utf-8") as f:
        graph = Graph.from_dict(json.load(f))
    try:
        return solve_graph(graph)
    except ModuleNotReady as e:
        pytest.skip(str(e))


def test_example1_final_answer():
    result = solve("example1.json")
    assert len(result.paths) == 2
    assert len(result.loops) == 1
    assert len(result.groups) == 0
    assert "10/3" in result.report            # T = (6*1 + 4*1) / 3


def test_example2_final_answer():
    result = solve("example2.json")
    assert len(result.paths) == 1
    assert len(result.loops) == 3
    assert len(result.groups) == 2            # L1*L3 and L2*L3
    assert "174" in result.report             # delta
    assert "5/29" in result.report            # T = 30 / 174


def test_report_is_a_string():
    result = solve("example1.json")
    assert isinstance(result.report, str) and len(result.report) > 0
