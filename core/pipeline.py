"""Connects the whole Part 1 flow.

    validate -> forward paths -> loops -> non-touching groups -> report

Expected functions from teammates:
    core/paths_loops.py (Mai):    find_forward_paths(graph) -> list[Path]
                                  find_loops(graph)         -> list[Loop]
    core/mason.py (Mariem):       non_touching_groups(loops) -> list[NonTouchingGroup]
                                  mason_report(paths, loops, groups) -> str
Until those exist, solve_graph raises ModuleNotReady with a friendly message.
"""
import importlib
from dataclasses import dataclass


class ModuleNotReady(Exception):
    """A teammate's module or function has not been merged yet."""


@dataclass
class SolveResult:
    paths: list
    loops: list
    groups: list
    report: str


def _load(module_name: str, func_name: str):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:      # a different import inside the module failed
            raise
        raise ModuleNotReady(f"{module_name} is not available yet.")
    try:
        return getattr(module, func_name)
    except AttributeError:
        raise ModuleNotReady(f"{module_name} has no function '{func_name}' yet.")


def solve_graph(graph) -> SolveResult:
    """Run the full Part 1 pipeline on a Graph. Raises ValueError on invalid input."""
    graph.validate()

    find_forward_paths = _load("core.paths_loops", "find_forward_paths")
    find_loops = _load("core.paths_loops", "find_loops")
    non_touching_groups = _load("core.mason", "non_touching_groups")
    mason_report = _load("core.mason", "mason_report")

    paths = find_forward_paths(graph)
    loops = find_loops(graph)
    groups = non_touching_groups(loops)
    report = mason_report(paths, loops, groups)
    return SolveResult(paths, loops, groups, report)
