import math
import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class GaugeWidget(Gtk.DrawingArea):
    """Circular arc gauge rendered with Cairo, theme-aware for dark mode.

    Draws a 270 degree arc with tick marks, needle and a centered numeric
    readout. Colors derive from the widget style context so the gauge adapts
    to light and dark themes automatically.
    """

    SWEEP_START = 0.75 * math.pi
    SWEEP_ANGLE = 1.5 * math.pi
    WARN_FRACTION = 0.85
    ACCENT = (0.208, 0.518, 0.894)
    DANGER = (0.878, 0.106, 0.141)

    def __init__(self, title, unit, minimum, maximum, digits=0):
        super().__init__()
        self.gauge_title = title
        self.gauge_unit = unit
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.digits = int(digits)
        self.value = None
        self.set_content_width(240)
        self.set_content_height(205)
        self.set_hexpand(True)
        self.set_draw_func(self.on_draw)

    def set_value(self, value):
        self.value = None if value is None else float(value)
        self.queue_draw()

    def fraction(self):
        if self.value is None:
            return 0.0
        span = self.maximum - self.minimum
        if span <= 0:
            return 0.0
        return max(0.0, min(1.0, (self.value - self.minimum) / span))

    def on_draw(self, area, ctx, width, height):
        ctx.new_path()
        color = self.get_color()
        text = (color.red, color.green, color.blue, color.alpha)
        dim = (color.red, color.green, color.blue, 0.35)
        track = (color.red, color.green, color.blue, 0.16)

        cx = width / 2.0
        cy = height * 0.53
        radius = min(width * 0.36, height * 0.48)
        frac = self.fraction()

        ctx.set_line_cap(cairo.LineCap.ROUND)
        ctx.set_source_rgba(*track)
        ctx.set_line_width(radius * 0.16)
        ctx.arc(cx, cy, radius, self.SWEEP_START, self.SWEEP_START + self.SWEEP_ANGLE)
        ctx.stroke()

        if frac > 0.0:
            rgb = self.DANGER if frac >= self.WARN_FRACTION else self.ACCENT
            ctx.set_source_rgba(rgb[0], rgb[1], rgb[2], 1.0)
            ctx.arc(
                cx,
                cy,
                radius,
                self.SWEEP_START,
                self.SWEEP_START + self.SWEEP_ANGLE * frac,
            )
            ctx.stroke()

        ctx.set_line_cap(cairo.LineCap.BUTT)
        ctx.set_line_width(1.5)
        ctx.set_source_rgba(*dim)
        for index in range(7):
            angle = self.SWEEP_START + self.SWEEP_ANGLE * index / 6.0
            ctx.move_to(
                cx + math.cos(angle) * radius * 1.10,
                cy + math.sin(angle) * radius * 1.10,
            )
            ctx.line_to(
                cx + math.cos(angle) * radius * 1.18,
                cy + math.sin(angle) * radius * 1.18,
            )
            ctx.stroke()

        angle = self.SWEEP_START + self.SWEEP_ANGLE * frac
        ctx.set_source_rgba(text[0], text[1], text[2], 0.85)
        ctx.set_line_width(2.0)
        ctx.move_to(cx, cy)
        ctx.line_to(
            cx + math.cos(angle) * radius * 0.58,
            cy + math.sin(angle) * radius * 0.58,
        )
        ctx.stroke()
        ctx.arc(cx, cy, 4.0, 0.0, 2.0 * math.pi)
        ctx.set_source_rgba(text[0], text[1], text[2], 0.9)
        ctx.fill()

        ctx.set_source_rgba(*text)
        ctx.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        if self.value is None:
            value_text = "--"
        else:
            value_text = "{0:.{1}f}".format(self.value, self.digits)
        ctx.set_font_size(radius * 0.34)
        extents = ctx.text_extents(value_text)
        ctx.move_to(cx - extents.width / 2.0, cy + radius * 0.62)
        ctx.show_text(value_text)

        ctx.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.NORMAL)
        ctx.set_source_rgba(*dim)
        ctx.set_font_size(radius * 0.16)
        extents = ctx.text_extents(self.gauge_unit)
        ctx.move_to(cx - extents.width / 2.0, cy + radius * 0.62 + radius * 0.20)
        ctx.show_text(self.gauge_unit)

        ctx.set_font_size(radius * 0.15)
        for angle, number in (
            (self.SWEEP_START, self.minimum),
            (self.SWEEP_START + self.SWEEP_ANGLE, self.maximum),
        ):
            scale_text = "{0:g}".format(number)
            extents = ctx.text_extents(scale_text)
            scale_x = cx + math.cos(angle) * radius * 1.24 - extents.width / 2.0
            scale_y = cy + math.sin(angle) * radius * 1.24 + extents.height / 2.0
            scale_x = max(1.0, min(width - extents.width - 1.0, scale_x))
            scale_y = min(height - 1.0, scale_y)
            ctx.move_to(scale_x, scale_y)
            ctx.show_text(scale_text)

        ctx.set_font_size(radius * 0.20)
        extents = ctx.text_extents(self.gauge_title)
        ctx.move_to(cx - extents.width / 2.0, height - 6.0)
        ctx.show_text(self.gauge_title)
