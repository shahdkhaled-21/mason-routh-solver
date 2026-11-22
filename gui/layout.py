"""Pure-Python layout and curve geometry for the signal flow graph drawing.

Nothing in this file imports Qt, so it can be unit-tested without opening a
window. The Qt drawing code lives in gui/graph_canvas.py and only turns the
numbers computed here into shapes.

Coordinates are scene coordinates: x grows to the right, y grows downward.
"""
import math
from collections import deque

H_SPACING = 170.0        # distance between node columns
V_SPACING = 110.0        # distance between nodes in the same column

OPPOSITE_BEND = 45.0     # bend for an edge that has an edge going the other way
FEEDBACK_BEND = 55.0     # base bend for a feedback (right-to-left) edge
PARALLEL_STEP = 55.0     # extra bend between parallel edges (same from and to)


# --------------------------------------------------------------------------
# Node placement
# --------------------------------------------------------------------------

def compute_layout(nodes, edges, source, sink):
    """Place nodes in columns by depth from the source node.

    nodes  : list of node names (order is kept inside a column)
    edges  : list of (from, to) pairs
    source : input node name (column 0, far left)
    sink   : output node name (always the last column, far right)

    Depth is the number of branches on the shortest path from the source
    (breadth-first search). Nodes that cannot be reached from the source go in
    column 1. Returns {node: (x, y)}.
    """
    adj = {n: [] for n in nodes}
    for s, d in edges:
        if s in adj and d in adj:
            adj[s].append(d)

    depth = {}
    if source in adj:
        depth[source] = 0
        queue = deque([source])
        while queue:
            n = queue.popleft()
            for m in adj[n]:
                if m not in depth:
                    depth[m] = depth[n] + 1
                    queue.append(m)

    fallback = 1 if source in adj else 0
    for n in nodes:
        depth.setdefault(n, fallback)

    if sink in adj and sink != source:
        others = [depth[n] for n in nodes if n != sink]
        depth[sink] = max(others, default=0) + 1

    columns = {}
    for n in nodes:
        columns.setdefault(depth[n], []).append(n)

    pos = {}
    for col, members in columns.items():
        count = len(members)
        for row, n in enumerate(members):
            pos[n] = (col * H_SPACING, (row - (count - 1) / 2.0) * V_SPACING)
    return pos


# --------------------------------------------------------------------------
# Edge shapes
# --------------------------------------------------------------------------

def edge_curve_params(edges, pos):
    """Decide how each edge is drawn.

    edges : list of (from, to) pairs
    pos   : {node: (x, y)}
    Returns one tuple per edge, (kind, offset, k):
      kind "self"  : self-loop; k is the index among self-loops on that node
      kind "curve" : quadratic curve; offset is how far (in pixels) the
                     control point is pushed sideways. 0 means a straight line.
    Rules: an edge with an opposite partner bends so the pair separates,
    a feedback edge (pointing left) bends over the top, and parallel edges
    fan out around the straight line.
    """
    groups = {}
    for i, (s, d) in enumerate(edges):
        groups.setdefault((s, d), []).append(i)

    self_count = {}
    params = [None] * len(edges)
    for i, (s, d) in enumerate(edges):
        if s == d:
            k = self_count.get(s, 0)
            self_count[s] = k + 1
            params[i] = ("self", 0.0, k)
            continue

        group = groups[(s, d)]
        idx = group.index(i)
        m = len(group)
        x0, y0 = pos[s]
        x1, y1 = pos[d]
        length = math.hypot(x1 - x0, y1 - y0)

        if (d, s) in groups:
            base = OPPOSITE_BEND
        elif x1 < x0 - 1:
            base = FEEDBACK_BEND + 0.15 * length
        else:
            base = 0.0

        offset = base + (idx - (m - 1) / 2.0) * PARALLEL_STEP if m > 1 else base
        params[i] = ("curve", offset, 0)
    return params


def unit_vector(dx, dy):
    """Unit vector of (dx, dy); (1, 0) if the length is zero."""
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return (1.0, 0.0)
    return (dx / length, dy / length)


def quad_points(p0, r0, p1, r1, offset):
    """Quadratic curve between two circles.

    p0, p1 are the node centres, r0, r1 the node radii. The control point is
    the chord midpoint pushed sideways by `offset` (0 gives a straight line).
    Returns (start, control, end), with start and end on the circle edges.
    """
    mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
    ux, uy = unit_vector(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -uy, ux
    ctrl = (mx + nx * offset, my + ny * offset)
    sx, sy = unit_vector(ctrl[0] - p0[0], ctrl[1] - p0[1])
    ex, ey = unit_vector(ctrl[0] - p1[0], ctrl[1] - p1[1])
    start = (p0[0] + sx * r0, p0[1] + sy * r0)
    end = (p1[0] + ex * r1, p1[1] + ey * r1)
    return start, ctrl, end


def quad_at(start, ctrl, end, t):
    """Point on a quadratic Bezier curve at parameter t in [0, 1]."""
    a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
    return (a * start[0] + b * ctrl[0] + c * end[0],
            a * start[1] + b * ctrl[1] + c * end[1])


def cubic_at(p0, p1, p2, p3, t):
    """Point on a cubic Bezier curve at parameter t in [0, 1]."""
    a, b = (1 - t) ** 3, 3 * (1 - t) ** 2 * t
    c, d = 3 * (1 - t) * t * t, t ** 3
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def is_clear(start, ctrl, end, others, margin=10.0, samples=16):
    """True if the curve stays away from every other node.

    others is a list of (x, y, radius) for the nodes the edge must avoid.
    """
    for i in range(1, samples):
        x, y = quad_at(start, ctrl, end, i / samples)
        for ox, oy, r in others:
            if math.hypot(x - ox, y - oy) < r + margin:
                return False
    return True


def choose_offset(p0, r0, p1, r1, offset, others, step=35.0, max_tries=8,
                  min_dodge=110.0):
    """Increase the bend until the edge no longer runs through another node.

    The first time an edge is blocked it jumps straight to a wide bend
    (min_dodge) so it does not end up lying on top of the other curved edges
    that leave the same node.
    """
    sign = 1.0 if offset >= 0 else -1.0
    current = offset
    for attempt in range(max_tries + 1):
        start, ctrl, end = quad_points(p0, r0, p1, r1, current)
        if is_clear(start, ctrl, end, others):
            return current
        if attempt == 0:
            current = sign * max(abs(current) + step, min_dodge)
        else:
            current += sign * step
    return current


SAMPLE_SPACING = 9.0     # one sample point roughly every 9 pixels along a curve
GRID_CELL = 14.0         # cell size of the lookup grid (must be >= the biggest distance tested)


def _count_for(length):
    return int(min(90, max(14, length / SAMPLE_SPACING)))


def _sample_quad(start, ctrl, end, count=None):
    """Points along a quadratic curve (ends excluded), about one every 9 px."""
    if count is None:
        count = _count_for(math.hypot(ctrl[0] - start[0], ctrl[1] - start[1]) +
                           math.hypot(end[0] - ctrl[0], end[1] - ctrl[1]))
    return [quad_at(start, ctrl, end, i / (count + 1)) for i in range(1, count + 1)]


def _grid(points):
    """Hash points into cells so 'is anything within 14 px?' is a quick lookup."""
    cells = {}
    for x, y in points:
        cells.setdefault((int(x // GRID_CELL), int(y // GRID_CELL)), []).append((x, y))
    return cells


def _count_near(cells, x, y, dist):
    """Number of grid points closer than `dist` (dist must be <= GRID_CELL)."""
    cx, cy = int(x // GRID_CELL), int(y // GRID_CELL)
    found = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for qx, qy in cells.get((cx + dx, cy + dy), ()):
                if math.hypot(x - qx, y - qy) < dist:
                    found += 1
    return found


def _overlap_cost(src, dst, points, label, placed, pos, radius, gap=12.0):
    """How badly a candidate curve overlaps the edges that are already placed.

    Points close to a node the two edges share are ignored, because edges that
    leave the same node always start together. Labels sitting on top of each
    other or on another curve are penalised too.
    """
    cost = 0
    for src2, dst2, points2, label2, cells2 in placed:
        shared = {src, dst} & {src2, dst2}
        zones = [(pos[n][0], pos[n][1], radius[n] + 30.0) for n in shared]
        for px, py in points:
            if any(math.hypot(px - zx, py - zy) < zr for zx, zy, zr in zones):
                continue
            cost += _count_near(cells2, px, py, gap)
        if math.hypot(label[0] - label2[0], label[1] - label2[1]) < 36.0:
            cost += 5
        cost += 3 * _count_near(cells2, label[0], label[1], 14.0)
        for px, py in points:
            if math.hypot(label2[0] - px, label2[1] - py) < 14.0:
                cost += 3
    return cost


LOOP_ROTATIONS = (0.0, 180.0, 45.0, -45.0, 135.0, -135.0, 90.0, -90.0)


def _sample_cubic(p0, c1, c2, p3, count=None):
    """Points along a cubic curve (ends excluded), about one every 9 px."""
    if count is None:
        length = (math.hypot(c1[0] - p0[0], c1[1] - p0[1]) +
                  math.hypot(c2[0] - c1[0], c2[1] - c1[1]) +
                  math.hypot(p3[0] - c2[0], p3[1] - c2[1]))
        count = _count_for(length)
    return [cubic_at(p0, c1, c2, p3, i / (count + 1)) for i in range(1, count + 1)]


LABEL_POSITIONS = (0.5, 0.4, 0.6, 0.3, 0.7)


def _shape_point(shape, t):
    kind, geo = shape
    return quad_at(*geo, t) if kind == "quad" else cubic_at(*geo, t)


def _shape_samples(shape):
    kind, geo = shape
    return _sample_quad(*geo) if kind == "quad" else _sample_cubic(*geo)


def _choose_label_positions(shapes, pos, radius):
    """Slide each gain label along its edge until it sits on nothing else.

    A label must not sit on a node, on another edge, or on another label.
    The middle of the edge is preferred.
    """
    n = len(shapes)
    cells = [None if sh is None else _grid(_shape_samples(sh)) for sh in shapes]
    chosen = [0.5] * n
    labels = [None if sh is None else _shape_point(sh, 0.5) for sh in shapes]
    for i, sh in enumerate(shapes):
        if sh is None:
            continue
        best = None
        for t in LABEL_POSITIONS:
            lab = _shape_point(sh, t)
            cost = 0
            for node, (nx, ny) in pos.items():
                if math.hypot(lab[0] - nx, lab[1] - ny) < radius[node] + 14.0:
                    cost += 20
            for j in range(n):
                if j == i or shapes[j] is None:
                    continue
                if math.hypot(lab[0] - labels[j][0], lab[1] - labels[j][1]) < 36.0:
                    cost += 5
                cost += 3 * _count_near(cells[j], lab[0], lab[1], 14.0)
            key = (cost, abs(t - 0.5))
            if best is None or key < best[0]:
                best = (key, t, lab)
            if cost == 0:
                break
        chosen[i] = best[1]
        labels[i] = best[2]
    return chosen


def route_edges(edges, pos, radius, step=35.0, max_steps=8):
    """Choose the shape of every edge so nothing runs through a node or lies
    on top of another edge or label.

    edges  : list of (from, to) pairs
    pos    : {node: (x, y)}
    radius : {node: radius}
    Returns one (kind, value, k, t) tuple per edge:
      ("curve", offset, 0, t)   offset = sideways bend in pixels (0 = straight)
      ("self", rotation, k, t)  rotation = degrees clockwise from "above the node"
    t in [0, 1] is where the gain label sits along the edge (0.5 = middle).

    Normal edges are placed first, one after another. For each one the
    preferred bend from edge_curve_params() is tried first, then bends pushed
    further to either side. The first bend that clears every node and does not
    overlap an already placed edge is used, otherwise the least bad one.
    Self-loops are placed last and pick the free direction (above, below or
    diagonal) where they overlap nothing.
    """
    params = edge_curve_params(edges, pos)
    placed = []
    shapes = [None] * len(edges)          # ("quad", geometry) or ("cubic", points)
    result = [None] * len(edges)

    for i, ((src, dst), (kind, base, k)) in enumerate(zip(edges, params)):
        if kind == "self":
            continue

        others = [(x, y, radius[n]) for n, (x, y) in pos.items() if n not in (src, dst)]
        candidates = [base]
        for j in range(1, max_steps + 1):
            candidates += [base + j * step, base - j * step]

        best = None
        for cand in candidates:
            geo = quad_points(pos[src], radius[src], pos[dst], radius[dst], cand)
            if not is_clear(*geo, others):
                continue
            points = _sample_quad(*geo)
            label = quad_at(*geo, 0.5)
            cost = _overlap_cost(src, dst, points, label, placed, pos, radius)
            if best is None or (cost, abs(cand - base)) < best[0]:
                best = ((cost, abs(cand - base)), cand, points, label)
            if cost == 0:
                break

        if best is None:        # no bend clears the nodes: fall back to the old rule
            cand = choose_offset(pos[src], radius[src], pos[dst], radius[dst], base, others)
            geo = quad_points(pos[src], radius[src], pos[dst], radius[dst], cand)
            best = (None, cand, _sample_quad(*geo), quad_at(*geo, 0.5))

        _, cand, points, label = best
        placed.append((src, dst, points, label, _grid(points)))
        shapes[i] = ("quad", quad_points(pos[src], radius[src], pos[dst], radius[dst], cand))
        result[i] = ("curve", cand, 0)

    for i, ((src, dst), (kind, _base, k)) in enumerate(zip(edges, params)):
        if kind != "self":
            continue
        others = [(x, y, radius[n]) for n, (x, y) in pos.items() if n != src]
        best = None
        for order, rot in enumerate(LOOP_ROTATIONS):
            p0, c1, c2, p3 = self_loop_points(pos[src], radius[src], k, rot)
            points = _sample_cubic(p0, c1, c2, p3)
            label = cubic_at(p0, c1, c2, p3, 0.5)
            hits = sum(1 for px, py in points + [label] for ox, oy, r in others
                       if math.hypot(px - ox, py - oy) < r + 10)
            cost = 20 * hits + _overlap_cost(src, src, points, label, placed, pos, radius)
            if best is None or (cost, order) < best[0]:
                best = ((cost, order), rot, points, label)
            if cost == 0:
                break
        _, rot, points, label = best
        placed.append((src, src, points, label, _grid(points)))
        shapes[i] = ("cubic", self_loop_points(pos[src], radius[src], k, rot))
        result[i] = ("self", rot, k)

    label_t = _choose_label_positions(shapes, pos, radius)
    return [(kind, value, k, t) for (kind, value, k), t in zip(result, label_t)]


def self_loop_points(center, radius, k=0, rotation=0.0):
    """Cubic curve for a self-loop attached to a node.

    k        : index of the loop on that node (extra loops are drawn bigger)
    rotation : degrees clockwise from "straight above the node"
               (0 = above, 180 = below, 90 = right side, -90 = left side)
    Returns (p0, c1, c2, p3).
    """
    cx, cy = center
    scale = 1 + 0.6 * k
    height = 2.2 * radius * scale
    width = 1.3 * radius * scale
    pts = [(cx - 0.5 * radius, cy - 0.866 * radius),
           (cx - width, cy - radius - height),
           (cx + width, cy - radius - height),
           (cx + 0.5 * radius, cy - 0.866 * radius)]
    if rotation:
        ang = math.radians(rotation)
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        pts = [(cx + (x - cx) * cos_a - (y - cy) * sin_a,
                cy + (x - cx) * sin_a + (y - cy) * cos_a) for x, y in pts]
    return tuple(pts)


def arrow_points(tip, direction, size=12.0):
    """Three corner points of an arrowhead whose tip touches `tip`.

    direction is the unit vector the arrow points along.
    """
    dx, dy = direction
    bx, by = tip[0] - dx * size, tip[1] - dy * size
    px, py = -dy, dx
    half = size * 0.4
    return [tip, (bx + px * half, by + py * half), (bx - px * half, by - py * half)]