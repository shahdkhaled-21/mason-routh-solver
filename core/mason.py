from fractions import Fraction
from itertools import combinations
import numpy as np
from core.graph import fmt
from core.models import NonTouchingGroup


"""Write a number for a substitution line. Negatives get brackets: -6 -> '(-6)'."""
def num(x):
    return f"({fmt(x)})" if x < 0 else fmt(x)

"""Multiply a list of numbers together."""
def product(values):
    
    result = Fraction(1)
    for v in values:
        result *= v
    return result


"""Return every group of 2, 3, ... loops in which no two loops share a node."""
def non_touching_groups(loops):
    groups = []
    for k in range(2, len(loops) + 1):
        found_any = False
        for combo in combinations(loops, k):
            if all(a.node_set.isdisjoint(b.node_set) for a, b in combinations(combo, 2)):
                found_any = True
                names = " ".join(lp.label for lp in combo)
                gain = product(lp.gain for lp in combo)
                factors = " x ".join(num(lp.gain) for lp in combo)
                groups.append(NonTouchingGroup(list(combo), gain, f"{names} = {factors} = {fmt(gain)}"))
        if not found_any:
            break
    return groups


"""Compute Δ for a set of loops and their non-touching groups."""

def compute_delta(loops, groups):
    # Put the single loops and the groups into one list of "terms" by size.
    terms = {1: [(lp.label, lp.gain) for lp in loops]}
    for g in groups:
        name = " ".join(lp.label for lp in g.loops)
        terms.setdefault(len(g.loops), []).append((name, g.gain))

    value = Fraction(1)
    formula = "1"
    numbers = "1"
    for size in sorted(terms):
        items = terms[size]
        if not items:
            continue
        sign = " - " if size % 2 == 1 else " + "
        total = sum(gain for _, gain in items)
        value = value - total if sign == " - " else value + total
        names = " + ".join(name for name, _ in items)
        gains = " + ".join(num(gain) for _, gain in items)
        if len(items) > 1:                 # brackets only around a sum of several terms
            names, gains = f"({names})", f"({gains})"
        formula += sign + names
        numbers += sign + gains
    return value, formula, numbers

"""Compute Δi for one forward path: Δ using only the loops that do not touch it."""
def compute_cofactor(path, loops, groups):
    kept = [lp for lp in loops if lp.node_set.isdisjoint(path.node_set)]
    removed = [lp for lp in loops if lp not in kept]
    kept_groups = [g for g in groups if all(lp in kept for lp in g.loops)]
    value, formula, numbers = compute_delta(kept, kept_groups)
    return value, formula, numbers, kept, removed

"""Return T from Mason's formula, or None if Δ = 0 (T is undefined)."""
def transfer_function(paths, loops, groups):
    delta = compute_delta(loops, groups)[0]
    if delta == 0:
        return None
    total = sum((p.gain * compute_cofactor(p, loops, groups)[0] for p in paths), Fraction(0))
    return total / delta


"""Build the full solution text"""
def mason_report(paths, loops, groups):
    lines = []
    add = lines.append

    # 1. Forward paths
    add(f"1. FORWARD PATHS ({len(paths)})")
    add("  Definition: Mi = product of the branch gains along forward path i (input to output, no node twice).")
    if not paths:
        add("  There is no forward path from the input node to the output node.")
    for p in paths:
        add(f"  {p.label}: {' -> '.join(p.nodes)}")
        add(f"      {p.gain_str}")

    # 2. Individual loops
    add("")
    add(f"2. INDIVIDUAL LOOPS ({len(loops)})")
    add("  Definition: loop gain = product of the branch gains around a closed path (no node twice).")
    if not loops:
        add("  The graph has no loops.")
    for lp in loops:
        add(f"  {lp.label}: {' -> '.join(lp.nodes + [lp.nodes[0]])}")
        add(f"      {lp.gain_str}")

    # 3. Non-touching groups
    add("")
    add("3. NON-TOUCHING LOOPS ")
    add("  Definition: loops are non-touching if they share no node; a group's gain is the product of its loop gains.")
    if not groups:
        add("  None.")
    size_names = {2: "pairs", 3: "triples", 4: "groups of 4"}
    for size in sorted({len(g.loops) for g in groups}):
        add(f"  {size} non-touching loops ({size_names.get(size, f'groups of {size}')}):")
        for g in groups:
            if len(g.loops) == size:
                add(f"      {g.gain_str}")

    # 4. Determinant Δ
    delta, formula, numbers = compute_delta(loops, groups)
    add("")
    add("4. DETERMINANT Δ")
    add("  Definition: Δ = 1 - Σ(loop gains) + Σ(2 non-touching-loop products) - Σ(3-loop products) + ...")
    add(f"  Δ = {formula}")
    add(f"  Δ = {numbers}")
    add(f"  Δ = {fmt(delta)}")

    # 5. Cofactors Δi
    add("")
    add("5. COFACTORS Δi")
    add("  Definition: Δi = Δ evaluated using only the loops that do not touch forward path i.")
    if not paths:
        add("  No forward paths, so there are no cofactors.")
    cofactors = []
    for i, p in enumerate(paths, start=1):
        value, formula, numbers, kept, removed = compute_cofactor(p, loops, groups)
        cofactors.append(value)
        add(f"  Δ{i} (for {p.label}):")
        for lp in removed:
            shared = ", ".join(sorted(lp.node_set & p.node_set))
            add(f"      {lp.label} excluded: it touches {p.label} at node(s) {shared}")
        if not kept:
            add(f"      No loops are left, so Δ{i} = 1")
        else:
            add(f"      Loops kept: {', '.join(lp.label for lp in kept)}")
            add(f"      Δ{i} = {formula}")
            add(f"      Δ{i} = {numbers}")
            add(f"      Δ{i} = {fmt(value)}")

    # 6. Mason's gain formula
    add("")
    add("6. MASON'S GAIN FORMULA")
    add("  Formula: T = C/R = (M1 Δ1 + M2 Δ2 + ... + Mm Δm) / Δ,  m = number of forward paths")
    add(f"  Here m = {len(paths)}.")
    products = []
    for i, (p, d) in enumerate(zip(paths, cofactors), start=1):
        products.append(p.gain * d)
        add(f"  M{i} Δ{i} = {num(p.gain)} x {num(d)} = {fmt(p.gain * d)}")
    numerator = sum(products, Fraction(0))
    if len(paths) > 1:
        add(f"  T = ({' + '.join(num(x) for x in products)}) / {num(delta)}")
    add(f"  T = {fmt(numerator)} / {num(delta)}")
    add("")
    if delta == 0:
        add("  Δ = 0, so the transfer function is undefined.")
    else:
        t = numerator / delta
        answer = f"  RESULT: T = C/R = {fmt(t)}"
        if t.denominator != 1:
            answer += f"  ≈ {float(t):.4f}"
        add(answer)
    return "\n".join(lines)

"""Find T without Mason's formula, to check the answer."""
def transfer_by_node_equations(graph):
    index = {name: i for i, name in enumerate(graph.nodes)}
    n = len(graph.nodes)

    A = np.zeros((n, n))
    for e in graph.edges:
        A[index[e.target], index[e.source]] += float(e.gain)
    b = np.zeros(n)
    b[index[graph.source_node]] = 1

    try:
        x = np.linalg.solve(np.eye(n) - A, b)
    except np.linalg.LinAlgError:
        return None
    return x[index[graph.sink_node]]
