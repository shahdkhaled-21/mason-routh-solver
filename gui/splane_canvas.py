"""Interactive complex s-plane widget for Routh-Hurwitz stability analysis.

Plots poles (s = sigma + j*omega) on a 2D complex plane with:
- Left Half-Plane (LHP) in soft velvet mint (Stable)
- Right Half-Plane (RHP) in soft velvet coral (Unstable)
- Imaginary axis (j*omega) boundary
- Interactive mouse hover for pole coordinates
- Selection highlighting synchronized with the roots table
"""
import math
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QToolTip, QWidget

BG_COLOR = QColor("#181825")
SURFACE_BORDER = QColor("#313244")
AXIS_COLOR = QColor("#45475A")
JW_AXIS_COLOR = QColor("#CBA6F7")
LHP_BG = QColor("#1A2B22")
RHP_BG = QColor("#351E24")
STABLE_POLE = QColor("#A6E3A1")
UNSTABLE_POLE = QColor("#F38BA8")
HIGHLIGHT_POLE = QColor("#CBA6F7")
TEXT_MUTED = QColor("#A6ADC8")


class SPlaneCanvas(QWidget):
    """Interactive S-Plane Pole-Zero Plotter."""

    pole_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMinimumWidth(260)
        self.setMouseTracking(True)
        self._roots = []              # list of complex numbers
        self._tol = 1e-7
        self._selected_index = -1
        self._hovered_index = -1
        self._is_dark = True
        self._update_colors()

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self._update_colors()
        self.update()

    def _update_colors(self):
        if self._is_dark:
            self.col_bg = QColor("#181825")
            self.col_border = QColor("#313244")
            self.col_axis = QColor("#45475A")
            self.col_jw = QColor("#CBA6F7")
            self.col_lhp = QColor("#1A2B22")
            self.col_rhp = QColor("#351E24")
            self.col_stable = QColor("#A6E3A1")
            self.col_unstable = QColor("#F38BA8")
            self.col_highlight = QColor("#CBA6F7")
            self.col_text_muted = QColor("#A6ADC8")
            self.col_lhp_label = QColor("#4E7A5A")
            self.col_rhp_label = QColor("#8C4E5E")
        else:
            self.col_bg = QColor("#F8FAFC")
            self.col_border = QColor("#CBD5E1")
            self.col_axis = QColor("#CBD5E1")
            self.col_jw = QColor("#6366F1")
            self.col_lhp = QColor("#ECFDF5")
            self.col_rhp = QColor("#FEF2F2")
            self.col_stable = QColor("#059669")
            self.col_unstable = QColor("#DC2626")
            self.col_highlight = QColor("#6366F1")
            self.col_text_muted = QColor("#64748B")
            self.col_lhp_label = QColor("#059669")
            self.col_rhp_label = QColor("#DC2626")

    def set_roots(self, roots, tol=1e-7):
        """Update roots list and redraw."""
        self._roots = list(roots)
        self._tol = tol
        self._selected_index = -1
        self._hovered_index = -1
        self.update()

    def select_root(self, index):
        """Highlight a root by its index in the table."""
        if 0 <= index < len(self._roots):
            self._selected_index = index
        else:
            self._selected_index = -1
        self.update()

    def clear(self):
        self._roots = []
        self._selected_index = -1
        self._hovered_index = -1
        self.update()

    # ------------------------------------------------------------- coordinate mapping
    def _get_bounds(self):
        """Calculate plot bounds (min_sigma, max_sigma, max_omega)."""
        if not self._roots:
            return -5.0, 5.0, 5.0

        sigmas = [r.real for r in self._roots]
        omegas = [abs(r.imag) for r in self._roots]

        min_sig = min(sigmas)
        max_sig = max(sigmas)
        max_om = max(omegas) if omegas else 1.0

        # Expand symmetric margin
        span_sig = max(abs(min_sig), abs(max_sig), 2.0) * 1.3
        span_om = max(max_om, 2.0) * 1.3

        return -span_sig, span_sig, span_om

    def _to_screen(self, sigma, omega, w, h, span_sig, span_om):
        """Map (sigma, omega) to widget pixel coordinates (x, y)."""
        cx = w / 2.0
        cy = h / 2.0
        sx = cx + (sigma / span_sig) * (w / 2.0 - 24)
        sy = cy - (omega / span_om) * (h / 2.0 - 24)
        return sx, sy

    def _find_root_near(self, pos):
        """Find index of root near the mouse cursor position."""
        if not self._roots:
            return -1
        w, h = self.width(), self.height()
        _, span_sig, span_om = self._get_bounds()

        for idx, r in enumerate(self._roots):
            sx, sy = self._to_screen(r.real, r.imag, w, h, span_sig, span_om)
            dx = pos.x() - sx
            dy = pos.y() - sy
            if math.hypot(dx, dy) <= 12:
                return idx
        return -1

    # ------------------------------------------------------------- mouse events
    def mouseMoveEvent(self, event):
        idx = self._find_root_near(event.pos())
        if idx != self._hovered_index:
            self._hovered_index = idx
            self.update()

        if idx >= 0:
            r = self._roots[idx]
            rhp = r.real > self._tol
            plane_str = "RHP (Unstable)" if rhp else "LHP (Stable)"
            sign_str = "+" if r.imag >= 0 else "-"
            val_str = f"s = {r.real:.4f} {sign_str} {abs(r.imag):.4f}j  [{plane_str}]"
            QToolTip.showText(event.globalPos(), val_str, self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        idx = self._find_root_near(event.pos())
        if idx >= 0:
            self._selected_index = idx
            self.pole_clicked.emit(idx)
            self.update()
        super().mousePressEvent(event)

    # ------------------------------------------------------------- painting
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        rect = QRectF(0, 0, w, h)

        # 1. Base background
        painter.fillRect(rect, self.col_bg)

        # Bounds
        _, span_sig, span_om = self._get_bounds()
        cx = w / 2.0
        cy = h / 2.0

        # 2. Shaded Half-Planes
        # LHP (left of cx)
        lhp_rect = QRectF(0, 0, cx, h)
        painter.fillRect(lhp_rect, self.col_lhp)

        # RHP (right of cx)
        rhp_rect = QRectF(cx, 0, w - cx, h)
        painter.fillRect(rhp_rect, self.col_rhp)

        # Border
        painter.setPen(QPen(self.col_border, 1))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)

        # 3. Half-plane region watermark labels
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.col_lhp_label)
        painter.drawText(12, 22, "LHP (STABLE)")

        painter.setPen(self.col_rhp_label)
        painter.drawText(int(w - 110), 22, "RHP (UNSTABLE)")

        # 4. Axes
        # Real axis (horizontal)
        painter.setPen(QPen(self.col_axis, 1.5))
        painter.drawLine(10, int(cy), int(w - 10), int(cy))
        font_axis = QFont("Consolas", 9)
        painter.setFont(font_axis)
        painter.setPen(self.col_text_muted)
        painter.drawText(int(w - 20), int(cy - 6), "\u03C3")

        # Imaginary axis (vertical jw)
        dash_pen = QPen(self.col_jw, 1.8)
        dash_pen.setStyle(Qt.DashLine)
        painter.setPen(dash_pen)
        painter.drawLine(int(cx), 10, int(cx), int(h - 10))
        painter.drawText(int(cx + 6), 18, "j\u03C9")

        # 5. Draw Poles
        if not self._roots:
            font_empty = QFont("Segoe UI", 10)
            painter.setFont(font_empty)
            painter.setPen(self.col_text_muted)
            painter.drawText(rect, Qt.AlignCenter, "Calculate characteristic equation to plot poles here")
            return

        for idx, r in enumerate(self._roots):
            sx, sy = self._to_screen(r.real, r.imag, w, h, span_sig, span_om)
            rhp = r.real > self._tol
            is_selected = (idx == self._selected_index)
            is_hovered = (idx == self._hovered_index)

            # Outer ring if selected or hovered
            if is_selected or is_hovered:
                ring_color = self.col_highlight if is_selected else (QColor("#11111B") if not self._is_dark else QColor("#FFFFFF"))
                painter.setPen(QPen(ring_color, 2, Qt.DotLine))
                painter.setBrush(QBrush(QColor(ring_color.red(), ring_color.green(), ring_color.blue(), 40)))
                painter.drawEllipse(QPointF(sx, sy), 13, 13)

            # Draw 'X' pole symbol
            pole_color = self.col_unstable if rhp else self.col_stable
            painter.setPen(QPen(pole_color, 2.8, Qt.SolidLine, Qt.RoundCap))
            sz = 6.0
            painter.drawLine(QPointF(sx - sz, sy - sz), QPointF(sx + sz, sy + sz))
            painter.drawLine(QPointF(sx - sz, sy + sz), QPointF(sx + sz, sy - sz))

            # Small label next to pole
            if len(self._roots) <= 8 or is_selected or is_hovered:
                painter.setFont(QFont("Consolas", 8))
                painter.setPen(pole_color)
                sign_str = "+" if r.imag >= 0 else "-"
                lbl = f"{r.real:.2f}{sign_str}{abs(r.imag):.2f}j" if abs(r.imag) > 1e-4 else f"{r.real:.2f}"
                painter.drawText(int(sx + 8), int(sy - 4), lbl)
