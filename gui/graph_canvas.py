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
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QFont, QFontMetrics, QImage, QPainter,
                         QPainterPath, QPen, QPolygonF)
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsPathItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsSimpleTextItem,
                             QGraphicsView)

from core.graph import parse_gain
from gui.layout import (arrow_points, compute_layout, cubic_at, quad_at,
                        quad_points, route_edges, self_loop_points, unit_vector)

SOURCE_FILL = QColor("#A6E3A1")      # input node (mint)
SINK_FILL = QColor("#FAB387")        # output node (peach)
NODE_FILL = QColor("#89DCEB")        # every other node (sky)
NODE_BORDER = QColor("#1E1E2E")      # contrast ring
NODE_TEXT_COLOR = QColor("#11111B")  # dark text on pastel circles
EDGE_COLOR = QColor("#89DCEB")       # soft sky branches
HIGHLIGHT = QColor("#CBA6F7")        # pastel lavender highlight
LABEL_COLOR = QColor("#CDD6F4")      # soft light text
LABEL_BORDER = QColor("#45475A")
LABEL_BG_COLOR = QColor("#181825")   # velvet mantle
CANVAS_BG = QColor("#181825")
CANVAS_DOT = QColor("#2D2B3D")


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
        self.text.setBrush(QBrush(NODE_TEXT_COLOR))
        box = self.text.boundingRect()
        self.text.setPos(-box.width() / 2.0, -box.height() / 2.0)
        self.setPen(QPen(NODE_BORDER, 2))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.canvas.node_clicked.emit(self.name)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.canvas._node_moved(self)
        return super().itemChange(change, value)


class EdgeItem(QGraphicsPathItem):
    """One branch: a curve, an arrowhead and a gain label."""

    def __init__(self, src, dst, gain_text, canvas=None):
        super().__init__()
        self.src = src
        self.dst = dst
        self.gain_text = gain_text
        self.canvas = canvas
        self._is_highlighted = False
        self.setZValue(1)
        self.setCursor(Qt.PointingHandCursor)

        self.arrow = QGraphicsPathItem(self)
        self.label_bg = QGraphicsRectItem(self)
        self.label = QGraphicsSimpleTextItem(gain_text, self)
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self.label.setFont(font)
        self.label_bg.setBrush(QBrush(LABEL_BG_COLOR))
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
        self._is_highlighted = on
        color = HIGHLIGHT if on else EDGE_COLOR
        width = 3.5 if on else 1.8
        pen = QPen(color, width)
        if self.canvas and self.canvas.is_animating():
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([8.0, 5.0])
            pen.setDashOffset(self.canvas.anim_offset())
        else:
            pen.setStyle(Qt.SolidLine)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.NoBrush))
        self.arrow.setPen(QPen(color, 1))
        self.arrow.setBrush(QBrush(color))
        self.label.setBrush(QBrush(HIGHLIGHT if on else LABEL_COLOR))
        self.label_bg.setPen(QPen(HIGHLIGHT if on else LABEL_BORDER, 1.2 if on else 1))

    def update_dash_offset(self, offset):
        """Update dash offset for moving dashed line animation."""
        color = HIGHLIGHT if self._is_highlighted else EDGE_COLOR
        width = 3.5 if self._is_highlighted else 1.8
        pen = QPen(color, width)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([8.0, 5.0])
        pen.setDashOffset(offset)
        self.setPen(pen)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.canvas:
            self.canvas.edge_clicked.emit(self.src, self.dst, self.gain_text)


class GraphCanvas(QGraphicsView):
    """The drawing area. Scroll wheel zooms, empty space can be dragged to pan."""

    node_clicked = pyqtSignal(str)
    edge_clicked = pyqtSignal(str, str, str)
    animation_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(CANVAS_BG))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMinimumHeight(170)   # small enough for short laptop screens; grows to fill space
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

        # Moving dashed line animation
        self._is_dark = True
        self._animating = False
        self._update_colors()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(30)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_offset = 0.0

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self._update_colors()
        self.setBackgroundBrush(QBrush(self.col_bg))
        self._rebuild()

    def _update_colors(self):
        if self._is_dark:
            self.col_bg = QColor("#181825")
            self.col_dot = QColor("#2D2B3D")
        else:
            self.col_bg = QColor("#F8FAFC")
            self.col_dot = QColor("#CBD5E1")

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
        has_highlight = bool(hl_edges or hl_nodes)

        # 1. Match edges in the highlight set
        highlighted_indices = set()
        if has_highlight:
            for e in hl_edges:
                for i, item in enumerate(self._edge_items):
                    if i in highlighted_indices or item.src != e.source or item.dst != e.target:
                        continue
                    try:
                        same_gain = parse_gain(item.gain_text) == e.gain
                    except ValueError:
                        same_gain = False
                    if same_gain:
                        highlighted_indices.add(i)
                        break

        # 2. Style edges (highlight active, dim non-active)
        for i, item in enumerate(self._edge_items):
            is_active = i in highlighted_indices
            item.set_highlight(is_active)
            if has_highlight:
                if is_active:
                    item.setOpacity(1.0)
                    item.setZValue(5)
                else:
                    item.setOpacity(0.18)  # Dim all other branches
                    item.setZValue(1)
            else:
                item.setOpacity(1.0)
                item.setZValue(1)

        # 3. Style nodes (highlight active, dim non-active)
        for name, item in self._node_items.items():
            is_active = name in hl_nodes
            item.setPen(QPen(HIGHLIGHT if is_active else NODE_BORDER, 4.0 if is_active else 2.0))
            if has_highlight:
                if is_active:
                    item.setOpacity(1.0)
                    item.setZValue(6)
                else:
                    item.setOpacity(0.25)  # Dim all other nodes
                    item.setZValue(2)
            else:
                item.setOpacity(1.0)
                item.setZValue(2)

    # --------------------------------------------------------------- drawing

    def _draw_hint(self):
        self._scene.clear()
        hint = self._scene.addText("Add branches in the table to draw the graph")
        hint.setDefaultTextColor(QColor("#A6ADC8"))

    def drawBackground(self, painter, rect):
        bg = self.col_bg if hasattr(self, 'col_bg') else CANVAS_BG
        dot = self.col_dot if hasattr(self, 'col_dot') else CANVAS_DOT
        painter.fillRect(rect, bg)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(QPen(dot, 1.5))
        grid_size = 24
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(x, y)
                y += grid_size
            x += grid_size
        painter.restore()

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
                edge = EdgeItem(src, dst, gain, self)
                self._scene.addItem(edge)
                self._edge_items.append(edge)

        self._building = False
        self._update_edges()
        self._apply_highlight()
        if self._animating:
            for edge in self._edge_items:
                edge.update_dash_offset(self._anim_offset)
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))

    # ----------------------------------------------------------- animation
    def toggle_animation(self) -> bool:
        """Toggle live signal flow moving dashed line animation."""
        if self._animating:
            self.stop_animation()
        else:
            self.start_animation()
        return self._animating

    def start_animation(self):
        self._animating = True
        self._anim_timer.start()
        for edge in self._edge_items:
            edge.update_dash_offset(self._anim_offset)
        self.animation_toggled.emit(True)

    def stop_animation(self):
        self._animating = False
        self._anim_timer.stop()
        for edge in self._edge_items:
            edge.set_highlight(edge._is_highlighted)
        self.animation_toggled.emit(False)

    def anim_offset(self) -> float:
        return self._anim_offset

    def is_animating(self) -> bool:
        return self._animating

    def _on_anim_tick(self):
        if not self._animating or not self._edge_items:
            return
        # Negative offset moves dashes forward along the branch direction
        self._anim_offset -= 1.0
        for edge in self._edge_items:
            edge.update_dash_offset(self._anim_offset)

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