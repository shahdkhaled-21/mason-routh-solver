"""Unit tests for core/paths_loops.py (member #3).

Every expected value below was worked out by hand. Run from the project root:
    python -m unittest tests.test_paths_loops -v
"""
import unittest
from fractions import Fraction

from core.graph import Graph
from core.paths_loops import find_forward_paths, find_loops


def make_graph(nodes, edges, source, sink):
    """Build a Graph from a node list and (from, to, gain) tuples."""
    g = Graph(source_node=source, sink_node=sink)
    for n in nodes:
        g.add_node(n)
    for a, b, gain in edges:
        g.add_edge(a, b, gain)
    return g


def node_sets(items):
    """Set of node sets, so results can be compared without caring about order."""
    return {frozenset(i.nodes) for i in items}


class TestExample1(unittest.TestCase):
    """examples/example1.json: R->A(1) A->B(2) B->C(3) B->A(-1) A->C(4)."""

    def setUp(self):
        self.g = make_graph(
            ["R", "A", "B", "C"],
            [("R", "A", "1"), ("A", "B", "2"), ("B", "C", "3"),
             ("B", "A", "-1"), ("A", "C", "4")],
            "R", "C")

    def test_forward_paths(self):
        paths = find_forward_paths(self.g)
        self.assertEqual(len(paths), 2)
        by_nodes = {tuple(p.nodes): p for p in paths}
        self.assertEqual(by_nodes[("R", "A", "B", "C")].gain, 6)
        self.assertEqual(by_nodes[("R", "A", "C")].gain, 4)

    def test_loops(self):
        loops = find_loops(self.g)
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].gain, -2)
        self.assertEqual(loops[0].node_set, frozenset({"A", "B"}))

    def test_gain_strings(self):
        paths = {tuple(p.nodes): p for p in find_forward_paths(self.g)}
        self.assertEqual(paths[("R", "A", "B", "C")].gain_str, "M1 = 1 x 2 x 3 = 6")
        self.assertEqual(find_loops(self.g)[0].gain_str, "L1 = 2 x (-1) = -2")


class TestChainWithThreeLoops(unittest.TestCase):
    """1->2->3->4->5 with a feedback branch over each of the last three links.

    Path: 1 x 2 x 3 x 4 = 24.
    Loops: 2<->3 = 2 x (-1) = -2, 3<->4 = 3 x (-2) = -6, 4<->5 = 4 x (-3) = -12.
    """

    def setUp(self):
        self.g = make_graph(
            ["1", "2", "3", "4", "5"],
            [("1", "2", "1"), ("2", "3", "2"), ("3", "4", "3"), ("4", "5", "4"),
             ("3", "2", "-1"), ("4", "3", "-2"), ("5", "4", "-3")],
            "1", "5")

    def test_single_path(self):
        paths = find_forward_paths(self.g)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].nodes, ["1", "2", "3", "4", "5"])
        self.assertEqual(paths[0].gain, 24)

    def test_three_loops(self):
        loops = find_loops(self.g)
        self.assertEqual(len(loops), 3)
        self.assertEqual(sorted(l.gain for l in loops), [-12, -6, -2])
        self.assertEqual(node_sets(loops),
                         {frozenset("23"), frozenset("34"), frozenset("45")})

    def test_non_touching_pair_is_detectable(self):
        """L(2,3) and L(4,5) share no node, L(2,3) and L(3,4) do."""
        loops = {frozenset(l.nodes): l for l in find_loops(self.g)}
        a, b, c = loops[frozenset("23")], loops[frozenset("34")], loops[frozenset("45")]
        self.assertFalse(a.node_set & c.node_set)
        self.assertTrue(a.node_set & b.node_set)


class TestLoopCanonicalRotation(unittest.TestCase):
    def test_three_node_cycle_appears_once(self):
        g = make_graph(["A", "B", "C"],
                       [("A", "B", "1"), ("B", "C", "2"), ("C", "A", "3")],
                       "A", "C")
        loops = find_loops(g)
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].gain, 6)
        self.assertEqual(loops[0].node_set, frozenset("ABC"))

    def test_start_node_is_not_repeated_in_nodes(self):
        g = make_graph(["A", "B", "C"],
                       [("A", "B", "1"), ("B", "C", "2"), ("C", "A", "3")],
                       "A", "C")
        self.assertEqual(len(find_loops(g)[0].nodes), 3)

    def test_same_cycle_regardless_of_node_order(self):
        g = make_graph(["C", "A", "B"],
                       [("A", "B", "1"), ("B", "C", "2"), ("C", "A", "3")],
                       "A", "C")
        loops = find_loops(g)
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].node_set, frozenset("ABC"))

    def test_two_loops_sharing_a_node(self):
        """A->B->A (2 x 5 = 10) and A->C->A (3 x 7 = 21) are different loops."""
        g = make_graph(["A", "B", "C"],
                       [("A", "B", "2"), ("B", "A", "5"),
                        ("A", "C", "3"), ("C", "A", "7")],
                       "A", "C")
        loops = find_loops(g)
        self.assertEqual(sorted(l.gain for l in loops), [10, 21])


class TestSelfLoop(unittest.TestCase):
    def setUp(self):
        self.g = make_graph(["X", "Y", "Z"],
                            [("X", "Y", "1"), ("Y", "Y", "4"), ("Y", "Z", "2")],
                            "X", "Z")

    def test_self_loop_is_a_loop(self):
        loops = find_loops(self.g)
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].nodes, ["Y"])
        self.assertEqual(loops[0].gain, 4)
        self.assertEqual(loops[0].node_set, frozenset({"Y"}))
        self.assertEqual(loops[0].gain_str, "L1 = 4")

    def test_self_loop_does_not_break_forward_path(self):
        paths = find_forward_paths(self.g)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].nodes, ["X", "Y", "Z"])
        self.assertEqual(paths[0].gain, 2)


class TestParallelEdges(unittest.TestCase):
    def setUp(self):
        self.g = make_graph(["A", "B"],
                            [("A", "B", "2"), ("A", "B", "3"), ("B", "A", "1")],
                            "A", "B")

    def test_each_parallel_edge_is_its_own_path(self):
        paths = find_forward_paths(self.g)
        self.assertEqual(sorted(p.gain for p in paths), [2, 3])

    def test_each_parallel_edge_is_its_own_loop(self):
        loops = find_loops(self.g)
        self.assertEqual(sorted(l.gain for l in loops), [2, 3])


class TestNoLoopsAndNoPath(unittest.TestCase):
    def test_no_loops_returns_empty_list(self):
        g = make_graph(["A", "B", "C"],
                       [("A", "B", "2"), ("B", "C", "3")], "A", "C")
        self.assertEqual(find_loops(g), [])
        self.assertEqual(len(find_forward_paths(g)), 1)

    def test_no_forward_path_returns_empty_list(self):
        g = make_graph(["A", "B"], [("A", "B", "2")], "B", "A")
        self.assertEqual(find_forward_paths(g), [])

    def test_disconnected_sink(self):
        g = make_graph(["A", "B", "C"], [("A", "B", "1")], "A", "C")
        self.assertEqual(find_forward_paths(g), [])

    def test_graph_without_edges(self):
        g = make_graph(["A", "B"], [], "A", "B")
        self.assertEqual(find_forward_paths(g), [])
        self.assertEqual(find_loops(g), [])


class TestNegativeAndFractionalGains(unittest.TestCase):
    def setUp(self):
        self.g = make_graph(["A", "B", "C"],
                            [("A", "B", "3/4"), ("B", "C", "-2"), ("B", "A", "-1/2")],
                            "A", "C")

    def test_path_gain_is_exact_fraction(self):
        p = find_forward_paths(self.g)[0]
        self.assertEqual(p.gain, Fraction(-3, 2))
        self.assertIsInstance(p.gain, Fraction)

    def test_path_string(self):
        self.assertEqual(find_forward_paths(self.g)[0].gain_str,
                         "M1 = 3/4 x (-2) = -3/2")

    def test_loop_gain_and_string(self):
        l = find_loops(self.g)[0]
        self.assertEqual(l.gain, Fraction(-3, 8))
        self.assertEqual(l.gain_str, "L1 = 3/4 x (-1/2) = -3/8")


class TestStructure(unittest.TestCase):
    """Properties every result must satisfy (what Mariem relies on)."""

    def setUp(self):
        self.g = make_graph(
            ["1", "2", "3", "4"],
            [("1", "2", "1"), ("2", "3", "2"), ("3", "4", "3"), ("2", "4", "5"),
             ("3", "2", "-1"), ("3", "3", "4"), ("4", "1", "-2")],
            "1", "4")

    def test_paths_never_repeat_a_node(self):
        for p in find_forward_paths(self.g):
            self.assertEqual(len(p.nodes), len(set(p.nodes)))
            self.assertEqual(p.nodes[0], "1")
            self.assertEqual(p.nodes[-1], "4")

    def test_loops_never_repeat_a_node(self):
        for l in find_loops(self.g):
            self.assertEqual(len(l.nodes), len(set(l.nodes)))
            self.assertEqual(len(l.edges), len(l.nodes))

    def test_no_duplicate_loops(self):
        keys = [(frozenset(l.nodes), tuple(sorted((e.source, e.target) for e in l.edges)))
                for l in find_loops(self.g)]
        self.assertEqual(len(keys), len(set(keys)))

    def test_node_set_matches_nodes(self):
        for item in find_forward_paths(self.g) + find_loops(self.g):
            self.assertEqual(item.node_set, frozenset(item.nodes))

    def test_gain_equals_product_of_edge_gains(self):
        for item in find_forward_paths(self.g) + find_loops(self.g):
            product = Fraction(1)
            for e in item.edges:
                product *= e.gain
            self.assertEqual(item.gain, product)

    def test_labels_are_sequential(self):
        self.assertEqual([p.label for p in find_forward_paths(self.g)],
                         [f"P{i}" for i in range(1, 3)])
        loops = find_loops(self.g)
        self.assertEqual([l.label for l in loops],
                         [f"L{i}" for i in range(1, len(loops) + 1)])

    def test_expected_loops_by_hand(self):
        """Hand solution: 1-2-3-4-1 (-12), 1-2-4-1 (-10), 2-3-2 (-2), 3-3 (4)."""
        loops = find_loops(self.g)
        self.assertEqual(sorted(l.gain for l in loops), [-12, -10, -2, 4])


if __name__ == "__main__":
    unittest.main()
