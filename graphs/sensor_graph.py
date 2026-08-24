"""
SensorGraphWidget — Real-time line graph for automotive sensor data.

Uses GTK4 DrawingArea + Cairo for native rendering (no matplotlib dependency).
Integrates with DashboardDataProcessor.get_history() for live sensor streaming.

Features:
- Multiple sensor overlay with distinct colors
- Mouse wheel zoom, click-drag pan
- Auto-scroll window (configurable: 30s/60s/120s/300s)
- Grid, axis labels, legend, dark light mode aware
- PNG export via Record button
"""

import math
import json
import os
import time
from typing import Dict, List, Optional, Tuple, Set

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf


# Sensor color palette (as specified in task)
SENSOR_COLORS = {
    'engine_rpm':         '#ff4444',  # red
    'vehicle_speed':      '#ffaa44',  # orange
    'throttle_position':  '#aa44ff',  # purple
    'coolant_temp':       '#44aaff',  # blue
    'intake_air_temp':    '#44ffff',  # cyan
    'maf_sensor':         '#ff44aa',  # pink
    'oxygen_sensor':      '#ffff44',  # yellow
    'battery_voltage':    '#44ff44',  # green
}

SENSOR_LABELS = {
    'engine_rpm':         'Engine RPM',
    'vehicle_speed':      'Vehicle Speed',
    'throttle_position':  'Throttle Position',
    'coolant_temp':       'Coolant Temp',
    'intake_air_temp':    'Intake Air Temp',
    'maf_sensor':         'MAF Sensor',
    'oxygen_sensor':      'O2 Sensor',
    'battery_voltage':    'Battery Voltage',
}

SENSOR_UNITS = {
    'engine_rpm':         'RPM',
    'vehicle_speed':      'km/h',
    'throttle_position':  '%',
    'coolant_temp':       '°C',
    'intake_air_temp':    '°C',
    'maf_sensor':         'g/s',
    'oxygen_sensor':      'V',
    'battery_voltage':    'V',
}


class SensorGraphWidget(Gtk.Box):
    """Main container widget for the sensor graph with controls."""

    def __init__(self, data_processor=None, config_file=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.data_processor = data_processor
        self.config_file = config_file or os.path.join(
            os.path.expanduser("~/.config/opengonsult"), "config.json")
        self.dark_mode = self._load_theme()

        # --- Control toolbar ---
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar.set_margin_bottom(6)
        toolbar.set_hexpand(True)

        # Sensor checkboxes
        self.checkboxes: Dict[str, Gtk.CheckButton] = {}
        for key in SENSOR_COLORS:
            cb = Gtk.CheckButton(label=SENSOR_LABELS[key])
            cb.set_active(True)
            cb.connect("toggled", self._on_sensor_toggled, key)
            toolbar.append(cb)
            self.checkboxes[key] = cb

        toolbar.append(Gtk.Separator())

        # Record button
        record_btn = Gtk.Button.new_from_icon_name("document-save")
        record_btn.set_label(" Record")
        record_btn.connect("clicked", self._on_record_clicked)
        toolbar.append(record_btn)

        toolbar.append(Gtk.Separator())

        # Time window selector
        window_label = Gtk.Label(label="Time window:")
        toolbar.append(window_label)

        self.window_combo = Gtk.ComboBoxText.new()
        self.window_combo.append_text("30s")
        self.window_combo.append_text("60s")
        self.window_combo.append_text("120s")
        self.window_combo.append_text("300s")
        self.window_combo.set_active(2)  # default 120s
        self.window_combo.connect("changed", self._on_window_changed)
        toolbar.append(self.window_combo)

        toolbar.append(Gtk.Separator())

        # Auto-scroll toggle
        self.auto_scroll_switch = Gtk.Switch()
        self.auto_scroll_switch.set_active(True)
        self.auto_scroll_switch.set_tooltip_text("Auto-scroll to latest data")
        toolbar.append(Gtk.Label(label="Auto-scroll:"))
        toolbar.append(self.auto_scroll_switch)

        self.append(toolbar)

        # --- DrawingArea for the graph ---
        self.graph_area = Gtk.DrawingArea()
        self.graph_area.set_hexpand(True)
        self.graph_area.set_vexpand(True)
        self.graph_area.set_content_width(800)
        self.graph_area.set_content_height(500)
        self.graph_area.set_draw_func(self._on_draw)

        # Zoom / pan state
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.panning = False
        self.pan_start: Optional[Tuple[float, float]] = None

        # Time window in seconds
        self.time_window_seconds = 120.0
        self.last_mouse_time = 0.0

        # Connect events
        controller = Gtk.GestureClick()
        controller.connect("pressed", self._on_mouse_pressed)
        controller.connect("released", self._on_mouse_released)
        self.graph_area.add_controller(controller)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_mouse_motion)
        self.graph_area.add_controller(motion_controller)

        scroll_controller = Gtk.EventControllerScroll()
        scroll_controller.connect("scroll", self._on_scroll)
        self.graph_area.add_controller(scroll_controller)

        self.append(self.graph_area)

        # Live update timer
        self._timeout_id = GLib.timeout_add_seconds(1, self._on_timeout)

    def set_data_processor(self, processor):
        """Attach a DashboardDataProcessor to this graph."""
        self.data_processor = processor

    def _load_theme(self) -> bool:
        """Load dark mode preference from config."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("dark_mode", True)
        except (json.JSONDecodeError, IOError):
            pass
        return True

    def _on_timeout(self) -> bool:
        """Trigger a redraw of the graph area every second."""
        self.graph_area.queue_draw()
        return True

    def _on_sensor_toggled(self, check_button: Gtk.CheckButton, sensor_key: str):
        """Handle sensor checkbox toggle."""
        self.graph_area.queue_draw()

    def _on_window_changed(self, combo: Gtk.ComboBoxText):
        """Handle time window selection change."""
        text = combo.get_active_text()
        if text == "30s":
            self.time_window_seconds = 30.0
        elif text == "60s":
            self.time_window_seconds = 60.0
        elif text == "120s":
            self.time_window_seconds = 120.0
        elif text == "300s":
            self.time_window_seconds = 300.0
        self.graph_area.queue_draw()

    def _on_record_clicked(self, button: Gtk.Button):
        """Export the current graph to a PNG file."""
        import cairo

        # Render the graph draw function into an offscreen Cairo surface,
        # then convert it to a pixbuf via Gdk.MemoryTexture (GTK4 way).
        widget = self.graph_area
        width = max(1, widget.get_width())
        height = max(1, widget.get_height())

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)
        self._on_draw(widget, ctx, width, height)
        surface.flush()

        data = bytes(surface.get_data())
        texture = Gdk.MemoryTexture.new(
            width,
            height,
            Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
            GLib.Bytes.new(data),
            surface.get_stride(),
        )
        pixbuf = Gdk.pixbuf_get_from_texture(texture)
        if pixbuf is None:
            self._show_error("Could not capture graph image.")
            return

        timestamp = int(time.time())
        filename = f"opengonsult_graph_{timestamp}.png"
        try:
            pixbuf.savev(filename, "png", [], [])
            self._show_info(f"Graph saved to: {filename}")
        except Exception as e:
            self._show_error(f"Failed to save: {e}")

    def _show_error(self, message: str):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()

    def _show_info(self, message: str):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()

    def _on_mouse_pressed(self, controller, n_press, x, y):
        """Begin pan mode on left-click."""
        if self.auto_scroll_switch.get_active():
            return
        self.panning = True
        self.pan_start = (x, y)

    def _on_mouse_released(self, controller, n_press, x, y):
        """End pan mode."""
        self.panning = False
        self.pan_start = None

    def _on_mouse_motion(self, controller, x, y):
        """Handle mouse motion for pan."""
        if self.panning and self.pan_start:
            dx = x - self.pan_start[0]
            dy = y - self.pan_start[1]
            self.pan_offset_x += dx
            self.pan_offset_y += dy
            self.pan_start = (x, y)
            self.graph_area.queue_draw()

    def _on_scroll(self, controller, dx, dy, x, y):
        """Zoom with mouse wheel."""
        factor = 0.9
        if dy < 0:  # scroll up = zoom in
            self.zoom_level *= factor
        else:  # scroll down = zoom out
            self.zoom_level /= factor
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        self.graph_area.queue_draw()

    def _on_draw(self, area: Gtk.DrawingArea, cr, width: int, height: int):
        """Cairo draw function — renders the full graph."""
        # Colors based on theme
        if self.dark_mode:
            bg_color = (0.18, 0.18, 0.18, 1.0)     # #2d2d2d
            grid_color = (0.35, 0.35, 0.35, 0.6)   # lighter grid
            axis_color = (0.8, 0.8, 0.8, 1.0)      # near white
            text_color = (0.9, 0.9, 0.9, 1.0)
            legend_bg = (0.15, 0.15, 0.15, 0.9)
        else:
            bg_color = (1.0, 1.0, 1.0, 1.0)        # white
            grid_color = (0.7, 0.7, 0.7, 0.4)
            axis_color = (0.4, 0.4, 0.4, 1.0)
            text_color = (0.1, 0.1, 0.1, 1.0)
            legend_bg = (0.95, 0.95, 0.95, 0.9)

        # Fill background
        cr.set_source_rgba(*bg_color)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        if not self.data_processor:
            # No data — draw placeholder
            cr.set_source_rgba(*text_color)
            cr.select_font_face("sans-serif")
            cr.set_font_size(16)
            text = "No sensor data — connect to an ECU"
            text_width = cr.text_extents(text).width
            cr.move_to((width - text_width) / 2, height / 2)
            cr.show_text(text)
            return

        # Gather data for each visible sensor
        now = time.time()
        window_start = now - self.time_window_seconds
        if not self.auto_scroll_switch.get_active():
            # If not auto-scrolling, pan_offset_x shifts the window
            window_start -= self.pan_offset_x / 100.0  # rough pixels-to-seconds

        sensor_data: Dict[str, List[Tuple[float, float]]] = {}
        for key in SENSOR_COLORS:
            if not self.checkboxes[key].get_active():
                continue
            history = self.data_processor.get_history(key)
            # Filter to current time window
            points = [(t, v) for t, v in history if t >= window_start]
            if points:
                sensor_data[key] = points

        if not sensor_data:
            # No visible sensors with data — draw placeholder
            cr.set_source_rgba(*text_color)
            cr.select_font_face("sans-serif")
            cr.set_font_size(14)
            text = "No data for selected sensors"
            text_width = cr.text_extents(text).width
            cr.move_to((width - text_width) / 2, height / 2)
            cr.show_text(text)
            return

        # Compute global Y range across all visible sensors
        all_values = [v for pts in sensor_data.values() for _, v in pts]
        y_min = min(all_values)
        y_max = max(all_values)
        if y_min == y_max:
            y_min -= 1
            y_max += 1

        # Margins for labels
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 40

        plot_x0 = margin_left
        plot_y0 = margin_top
        plot_width = width - margin_left - margin_right
        plot_height = height - margin_top - margin_bottom

        # Auto-apply zoom
        if not self.auto_scroll_switch.get_active():
            plot_x0 += self.pan_offset_x
            plot_y0 += self.pan_offset_y

        # --- Draw grid ---
        cr.set_source_rgba(*grid_color)
        cr.set_line_width(0.5)
        num_grid_x = 10
        num_grid_y = 5
        for i in range(num_grid_x + 1):
            x = plot_x0 + (i / num_grid_x) * plot_width
            cr.move_to(x, plot_y0)
            cr.line_to(x, plot_y0 + plot_height)
            cr.stroke()
        for i in range(num_grid_y + 1):
            y = plot_y0 + (i / num_grid_y) * plot_height
            cr.move_to(plot_x0, y)
            cr.line_to(plot_x0 + plot_width, y)
            cr.stroke()

        # --- Draw axes ---
        cr.set_source_rgba(*axis_color)
        cr.set_line_width(1.5)
        cr.move_to(plot_x0, plot_y0)
        cr.line_to(plot_x0 + plot_width, plot_y0)
        cr.line_to(plot_x0 + plot_width, plot_y0 + plot_height)
        cr.line_to(plot_x0, plot_y0 + plot_height)
        cr.stroke()

        # --- Y-axis labels (min/max values) ---
        cr.set_source_rgba(*text_color)
        cr.select_font_face("sans-serif")
        cr.set_font_size(11)
        # Min label
        min_label = f"{y_min:.1f}"
        min_ext = cr.text_extents(min_label)
        cr.move_to(plot_x0 - 5 - min_ext.width, plot_y0 + plot_height + min_ext.height / 2)
        cr.show_text(min_label)
        # Max label
        max_label = f"{y_max:.1f}"
        max_ext = cr.text_extents(max_label)
        cr.move_to(plot_x0 - 5 - max_ext.width, plot_y0 + max_ext.height / 2)
        cr.show_text(max_label)

        # --- X-axis time labels ---
        mid_time = window_start + self.time_window_seconds / 2
        mid_label = f"-{self.time_window_seconds / 2:.0f}s"
        mid_ext = cr.text_extents(mid_label)
        cr.move_to(plot_x0 + plot_width / 2 - mid_ext.width / 2, plot_y0 + plot_height + 18)
        cr.show_text(mid_label)
        # Time window label
        window_label = f"Window: {self.time_window_seconds:.0f}s"
        w_ext = cr.text_extents(window_label)
        cr.move_to(plot_x0 + plot_width / 2 - w_ext.width / 2, plot_y0 + plot_height + 35)
        cr.show_text(window_label)

        # --- Draw sensor data lines ---
        for key, points in sensor_data.items():
            color_hex = SENSOR_COLORS[key]
            r = int(color_hex[1:3], 16) / 255.0
            g = int(color_hex[3:5], 16) / 255.0
            b = int(color_hex[5:7], 16) / 255.0

            cr.set_source_rgba(r, g, b, 0.9)
            cr.set_line_width(2.0 * self.zoom_level)

            for i, (t, v) in enumerate(points):
                # Map time to x
                x_frac = (t - window_start) / self.time_window_seconds
                x = plot_x0 + x_frac * plot_width
                # Map value to y (inverted — y is down in Cairo)
                y_frac = (v - y_min) / (y_max - y_min)
                y = plot_y0 + plot_height - y_frac * plot_height

                if i == 0:
                    cr.move_to(x, y)
                else:
                    cr.line_to(x, y)

            cr.stroke()

        # --- Draw legend ---
        legend_x = plot_x0 + plot_width - 120
        legend_y = plot_y0 + 10
        cr.set_source_rgba(*legend_bg)
        cr.rectangle(legend_x - 8, legend_y - 8, 128, 20 * len(sensor_data) + 4)
        cr.fill()

        cr.set_source_rgba(*text_color)
        cr.set_font_size(11)
        legend_y_current = legend_y
        for key in sensor_data:
            color_hex = SENSOR_COLORS[key]
            r = int(color_hex[1:3], 16) / 255.0
            g = int(color_hex[3:5], 16) / 255.0
            b = int(color_hex[5:7], 16) / 255.0
            cr.set_source_rgba(r, g, b, 0.9)
            cr.rectangle(legend_x, legend_y_current, 10, 12)
            cr.fill()
            cr.set_source_rgba(*text_color)
            label = SENSOR_LABELS[key]
            cr.move_to(legend_x + 16, legend_y_current + 10)
            cr.show_text(label)
            legend_y_current += 20

    def destroy(self):
        """Clean up the timeout when widget is destroyed."""
        if hasattr(self, '_timeout_id') and self._timeout_id:
            GLib.source_remove(self._timeout_id)
        super().destroy()
