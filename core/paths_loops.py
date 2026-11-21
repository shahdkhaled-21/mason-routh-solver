"""Forward-paths and loops engine (member #3).

Public API:
    find_forward_paths(graph) -> list[Path]
    find_loops(graph)         -> list[Loop]

Both functions return the structures defined in core/models.py. Every gain is
a fractions.Fraction and every result has its node_set filled in so that the
Mason module can test whether two items touch.
"""
from fractions import Fraction

from core.graph import Graph, fmt
from core.models import Path, Loop


def _product_string(label: str, edges: list) -> tuple:
    """Build the gain product and its display string.

    Example: label "M1", edge gains 2, 3, 2 -> (Fraction(12), "M1 = 2 x 3 x 2 = 12").
    Negative factors are wrapped in brackets: "L1 = 2 x (-3) = -6".
    A single-edge item is shown as "L1 = 3" (no redundant "= 3").
    """
    total = Fraction(1)
    parts = []
    for e in edges:
        total *= e.gain
        text = fmt(e.gain)
        parts.append(f"({text})" if e.gain < 0 and len(edges) > 1 else text)
    if len(edges) == 1:
        return total, f"{label} = {fmt(total)}"
    return total, f"{label} = {' x '.join(parts)} = {fmt(total)}"


def find_forward_paths(graph: Graph) -> list:
    """Return every forward path from the source node to the sink node.

    Uses a depth-first search. A node is never visited twice on one path, and
    the search stops as soon as the sink is reached. Parallel edges give
    separate paths. If there is no forward path, an empty list is returned.
    """
    adj = graph.adjacency()
    sink = graph.sink_node
    found = []  # each item: (node list, edge list)

    def dfs(node, nodes, edges, visited):
        if node == sink:
            found.append((list(nodes), list(edges)))
            return
        for e in adj.get(node, []):
            if e.target in visited:
                continue
            visited.add(e.target)
            nodes.append(e.target)
            edges.append(e)
            dfs(e.target, nodes, edges, visited)
            edges.pop()
            nodes.pop()
            visited.remove(e.target)

    start = graph.source_node
    if start in adj:
        dfs(start, [start], [], {start})

    paths = []
    for i, (nodes, edges) in enumerate(found, start=1):
        gain, gain_str = _product_string(f"M{i}", edges)
        paths.append(Path(
            label=f"P{i}",
            nodes=nodes,
            edges=edges,
            gain=gain,
            gain_str=gain_str,
            node_set=frozenset(nodes),
        ))
    return paths


def find_loops(graph: Graph) -> list:
    """Return every individual loop (closed path, no repeated node except the start).

    Duplicates are avoided by canonical rotation: each loop is searched only
    from its lowest-indexed node (by the order in graph.nodes), and the search
    never enters a node with a lower index. So A->B->C->A and B->C->A->B are
    the same loop and appear once. Self-loops count, and parallel edges give
    separate loops. If there are no loops, an empty list is returned.
    """
    adj = graph.adjacency()
    index = {n: i for i, n in enumerate(graph.nodes)}
    found = []  # each item: (node list, edge list)

    def dfs(start, node, nodes, edges, visited):
        for e in adj.get(node, []):
            if e.target == start:
                found.append((list(nodes), edges + [e]))
            elif index[e.target] > index[start] and e.target not in visited:
                visited.add(e.target)
                nodes.append(e.target)
                edges.append(e)
                dfs(start, e.target, nodes, edges, visited)
                edges.pop()
                nodes.pop()
                visited.remove(e.target)

    for start in graph.nodes:
        dfs(start, start, [start], [], {start})

    loops = []
    for i, (nodes, edges) in enumerate(found, start=1):
        gain, gain_str = _product_string(f"L{i}", edges)
        loops.append(Loop(
            label=f"L{i}",
            nodes=nodes,
            edges=edges,
            gain=gain,
            gain_str=gain_str,
            node_set=frozenset(nodes),
        ))
    return loops
