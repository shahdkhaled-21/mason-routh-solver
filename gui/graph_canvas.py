"""Drawing canvas for the signal flow graph (PyQt5).

GraphCanvas is a QGraphicsView that shows:
  * nodes as circles (input node green, output node orange, others blue),
  * branches as arrows: straight for forward edges, curved for feedback edges,
    opposite-direction pairs and parallel edges, loops above the node for self-loops,
  * gain labels on a white background so they stay readable,
  * nodes that can be dragged with the mouse (edges follow them).

The canvas knows nothing about solving. gui/sfg_tab.py feeds it plain data
through set_graph_data() and asks it to highlight a path or a loop.
"""
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import (QBrush, QColor, QFont, QFontMetrics, QImage, QPainter,
                         QPainterPath, QPen, QPolygonF)
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsPathItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsSimpleTextItem,
                             QGraphicsView)

from core.graph import parse_gain
from gui.layout import (arrow_points, compute_layout, cubic_at, quad_at,
                        quad_points, route_edges, self_loop_points, unit_vector)

SOURCE_FILL = QColor("#81C784")      # input node
SINK_FILL = QColor("#FFB74D")        # output node
NODE_FILL = QColor("#90CAF9")        # every other node
NODE_BORDER = QColor("#263238")
EDGE_COLOR = QColor("#37474F")
HIGHLIGHT = QColor("#D32F2F")
LABEL_COLOR = QColor("#0D47A1")
LABEL_BORDER = QColor("#B0BEC5")


class NodeItem(QGraphicsEllipseItem):
    """A draggable circle with the node name in the middle."""

    def __init__(self, name, canvas):
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        width = QFontMetrics(font).boundingRect(name).width()
        radius = max(24.0, width / 2.0 + 10.0)

        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.name = name
        self.radius = radius
        self.canvas = canvas
        self.setZValue(2)
        self.setFlags(QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.OpenHandCursor)

        self.text = QGraphicsSimpleTextItem(name, self)
        self.text.setFont(font)
        self.text.setBrush(QBrush(NODE_BORDER))
        box = self.text.boundingRect()
        self.text.setPos(-box.width() / 2.0, -box.height() / 2.0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.canvas._node_moved(self)
        return super().itemChange(change, value)


class EdgeItem(QGraphicsPathItem):
    """One branch: a curve, an arrowhead and a gain label."""

    def __init__(self, src, dst, gain_text):
        super().__init__()
        self.src = src
        self.dst = dst
        self.gain_text = gain_text
        self.setZValue(1)

        self.arrow = QGraphicsPathItem(self)
        self.label_bg = QGraphicsRectItem(self)
        self.label = QGraphicsSimpleTextItem(gain_text, self)
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.label.setFont(font)
        self.label_bg.setBrush(QBrush(Qt.white))
        self.label_bg.setPen(QPen(LABEL_BORDER, 1))
        self.label_bg.setZValue(0)
        self.label.setZValue(1)
        self.set_highlight(False)

    def set_geometry(self, path, arrow_polygon, label_center):
        self.setPath(path)
        arrow_path = QPainterPath()
        arrow_path.addPolygon(arrow_polygon)
        arrow_path.closeSubpath()
        self.arrow.setPath(arrow_path)

        box = self.label.boundingRect()
        x = label_center.x() - box.width() / 2.0
        y = label_center.y() - box.height() / 2.0
        self.label.setPos(x, y)
        self.label_bg.setRect(x - 3, y - 1, box.width() + 6, box.height() + 2)

    def set_highlight(self, on):
        color = HIGHLIGHT if on else EDGE_COLOR
        self.setPen(QPen(color, 3.2 if on else 1.7))
        self.setBrush(QBrush(Qt.NoBrush))
        self.arrow.setPen(QPen(color, 1))
        self.arrow.setBrush(QBrush(color))
        self.label.setBrush(QBrush(HIGHLIGHT if on else LABEL_COLOR))


class GraphCanvas(QGraphicsView):
    """The drawing area. Scroll wheel zooms, empty space can be dragged to pan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(Qt.white))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMinimumHeight(260)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._nodes = []              # node names
        self._edges = []              # (from, to, gain_text)
        self._source = ""
        self._sink = ""
        self._auto = {}               # automatic layout positions
        self._manual = {}             # positions the user dragged to
        self._node_items = {}
        self._edge_items = []
        self._highlight = ([], [])    # (edges, node names)
        self._building = False
        self._draw_hint()

    # ------------------------------------------------------------------ data

    def set_graph_data(self, nodes, edges, source, sink, fit=False):
        """Show a graph.

        nodes  : list of node names
        edges  : list of (from, to, gain_text)
        source : input node name ("" if not chosen)
        sink   : output node name ("" if not chosen)
        Nodes the user dragged keep their position between updates.
        """
        old_nodes = set(self._node_items)
        self._nodes = list(nodes)
        self._edges = list(edges)
        self._source = source
        self._sink = sink
        self._manual = {n: p for n, p in self._manual.items() if n in self._nodes}
        self._auto = compute_layout(self._nodes, [(s, d) for s, d, _ in self._edges],
                                    source, sink)
        self._rebuild()
        if fit or set(self._nodes) != old_nodes:
            self.fit()

    def clear(self):
        """Remove everything, including dragged positions."""
        self._manual = {}
        self._highlight = ([], [])
        self.set_graph_data([], [], "", "", fit=True)

    def reset_positions(self):
        """Forget dragged positions (the next update uses the automatic layout)."""
        self._manual = {}

    def auto_layout(self):
        """Forget dragged positions and place nodes automatically again."""
        self._manual = {}
        self._rebuild()
        self.fit()

    # ------------------------------------------------------------- highlight

    def set_highlight(self, edges, nodes):
        """Highlight a path or loop.

        edges : objects with .source, .target and .gain (core.models Path/Loop .edges)
        nodes : node names to outline
        """
        self._highlight = (list(edges), list(nodes))
        self._apply_highlight()

    def clear_highlight(self):
        self.set_highlight([], [])

    def _apply_highlight(self):
        hl_edges, hl_nodes = self._highlight
        for item in self._edge_items:
            item.set_highlight(False)
        for name, item in self._node_items.items():
            on = name in hl_nodes
            item.setPen(QPen(HIGHLIGHT if on else NODE_BORDER, 4 if on else 2))

        used = set()
        for e in hl_edges:
            for i, item in enumerate(self._edge_items):
                if i in used or item.src != e.source or item.dst != e.target:
                    continue
                try:
                    same_gain = parse_gain(item.gain_text) == e.gain
                except ValueError:
                    same_gain = False
                if same_gain:
                    item.set_highlight(True)
                    used.add(i)
                    break

    # --------------------------------------------------------------- drawing

    def _draw_hint(self):
        self._scene.clear()
        hint = self._scene.addText("Add branches in the table to draw the graph")
        hint.setDefaultTextColor(QColor("#90A4AE"))

    def _rebuild(self):
        self._building = True
        self._scene.clear()
        self._node_items = {}
        self._edge_items = []

        if not self._nodes:
            self._building = False
            self._draw_hint()
            return

        for name in self._nodes:
            item = NodeItem(name, self)
            x, y = self._manual.get(name) or self._auto.get(name, (0.0, 0.0))
            item.setPos(x, y)
            if name == self._source:
                item.setBrush(QBrush(SOURCE_FILL))
            elif name == self._sink:
                item.setBrush(QBrush(SINK_FILL))
            else:
                item.setBrush(QBrush(NODE_FILL))
            self._scene.addItem(item)
            self._node_items[name] = item

        for src, dst, gain in self._edges:
            if src in self._node_items and dst in self._node_items:
                edge = EdgeItem(src, dst, gain)
                self._scene.addItem(edge)
                self._edge_items.append(edge)

        self._building = False
        self._update_edges()
        self._apply_highlight()
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))

    def _node_moved(self, item):
        if self._building:
            return
        self._manual[item.name] = (item.pos().x(), item.pos().y())
        self._update_edges()

    def _update_edges(self):
        """Recompute every edge shape from the current node positions."""
        if self._building or not self._edge_items:
            return
        pos = {n: (it.pos().x(), it.pos().y()) for n, it in self._node_items.items()}
        radius = {n: it.radius for n, it in self._node_items.items()}
        params = route_edges([(e.src, e.dst) for e in self._edge_items], pos, radius)

        for edge, (kind, offset, k, t) in zip(self._edge_items, params):
            if kind == "self":
                p0, c1, c2, p3 = self_loop_points(pos[edge.src], radius[edge.src], k, offset)
                path = QPainterPath(QPointF(*p0))
                path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*p3))
                tip = p3
                direction = unit_vector(p3[0] - c2[0], p3[1] - c2[1])
                label = cubic_at(p0, c1, c2, p3, t)
            else:
                a, b = pos[edge.src], pos[edge.dst]
                ra, rb = radius[edge.src], radius[edge.dst]
                start, ctrl, end = quad_points(a, ra, b, rb, offset)
                path = QPainterPath(QPointF(*start))
                path.quadTo(QPointF(*ctrl), QPointF(*end))
                tip = end
                direction = unit_vector(end[0] - ctrl[0], end[1] - ctrl[1])
                label = quad_at(start, ctrl, end, t)

            arrow = QPolygonF([QPointF(*p) for p in arrow_points(tip, direction)])
            edge.set_geometry(path, arrow, QPointF(*label))

    # ------------------------------------------------------------ view tools

    def fit(self):
        """Zoom so the whole graph is visible (never zoom in beyond 120%)."""
        if not self._node_items:
            self.resetTransform()
            return
        rect = self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        self.fitInView(rect, Qt.KeepAspectRatio)
        if self.transform().m11() > 1.2:
            self.resetTransform()
            self.scale(1.2, 1.2)
            self.centerOn(rect.center())

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._node_items:
            self.fit()

    def export_image(self, path, scale=2.0):
        """Save the drawing as an image (PNG recommended). Returns True on success."""
        if not self._node_items:
            raise ValueError("There is no graph to export yet.")
        rect = self._scene.itemsBoundingRect().adjusted(-30, -30, 30, 30)
        image = QImage(int(rect.width() * scale), int(rect.height() * scale),
                       QImage.Format_RGB32)
        image.fill(Qt.white)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        self._scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
        return image.save(path)