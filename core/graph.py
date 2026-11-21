"""Core graph data structure shared by every module.

All gains are stored as fractions.Fraction so results stay exact.
"""
from dataclasses import dataclass, field
from fractions import Fraction


def parse_gain(text) -> Fraction:
    """Convert '2', '-0.5' or '3/4' to a Fraction. Raises ValueError if invalid."""
    try:
        return Fraction(str(text).strip())
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"Invalid gain: '{text}'")


def fmt(x: Fraction) -> str:
    """Display helper: 12 -> '12', Fraction(3, 4) -> '3/4'."""
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    gain: Fraction


@dataclass
class Graph:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    source_node: str = ""
    sink_node: str = ""

    def add_node(self, name: str):
        name = name.strip()
        if not name:
            raise ValueError("Node name cannot be empty.")
        if name in self.nodes:
            raise ValueError(f"Node '{name}' already exists.")
        self.nodes.append(name)

    def add_edge(self, src: str, dst: str, gain):
        if src not in self.nodes or dst not in self.nodes:
            raise ValueError(f"Unknown node in branch {src} -> {dst}.")
        self.edges.append(Edge(src, dst, parse_gain(gain)))

    def remove_edge(self, index: int):
        del self.edges[index]

    def adjacency(self) -> dict:
        """node -> list of outgoing Edge objects (used by the paths/loops engine)."""
        adj = {n: [] for n in self.nodes}
        for e in self.edges:
            adj[e.source].append(e)
        return adj

    def validate(self):
        """Raise ValueError with a friendly message if the graph is not solvable."""
        if not self.nodes:
            raise ValueError("Graph has no nodes.")
        if self.source_node not in self.nodes:
            raise ValueError("Input (source) node is not set or does not exist.")
        if self.sink_node not in self.nodes:
            raise ValueError("Output (sink) node is not set or does not exist.")
        if self.source_node == self.sink_node:
            raise ValueError("Input and output nodes must be different.")
        for e in self.edges:
            if e.gain == 0:
                raise ValueError(f"Branch {e.source}->{e.target} has zero gain.")

    # ---- JSON save / load ----
    def to_dict(self) -> dict:
        return {
            "nodes": list(self.nodes),
            "edges": [{"from": e.source, "to": e.target, "gain": fmt(e.gain)}
                      for e in self.edges],
            "source": self.source_node,
            "sink": self.sink_node,
        }

    @staticmethod
    def from_dict(d: dict) -> "Graph":
        g = Graph(source_node=d["source"], sink_node=d["sink"])
        for n in d["nodes"]:
            g.add_node(n)
        for e in d["edges"]:
            g.add_edge(e["from"], e["to"], e["gain"])
        return g
