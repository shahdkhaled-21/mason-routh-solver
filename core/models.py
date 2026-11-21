"""Result structures passed between modules.

Paths and loops come from core/paths_loops.py (member #3).
NonTouchingGroup comes from core/mason.py (member #4).
"""
from dataclasses import dataclass
from fractions import Fraction


@dataclass
class Path:
    label: str            # "P1"
    nodes: list           # ["R", "A", "B", "C"]
    edges: list           # list[Edge], in order
    gain: Fraction        # product of edge gains (this is M_i)
    gain_str: str         # "M1 = 2 x 3 x 2 = 12"
    node_set: frozenset   # used for touching checks


@dataclass
class Loop:
    label: str            # "L1"
    nodes: list           # canonical rotation, e.g. ["A", "B"] (no repeated end node)
    edges: list           # list[Edge]
    gain: Fraction
    gain_str: str         # "L1 = 2 x (-3) = -6"
    node_set: frozenset   # two loops touch if their node_sets intersect


@dataclass
class NonTouchingGroup:
    loops: list           # list[Loop], size 2, 3, ...
    gain: Fraction        # product of the loop gains
    gain_str: str         # "L1 L3 = (-6) x (4) = -24"
