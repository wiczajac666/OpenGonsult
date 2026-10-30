"""
SensorGraphWidget — Real-time line graph for automotive sensor data.

Uses GTK4 DrawingArea + Cairo for native rendering (no matplotlib dependency).
Integrates with DashboardDataProcessor.get_history() for live sensor streaming.

Features:
- Multiple sensor overlay with distinct colors
- Mouse wheel zoom, click-drag pan
- Auto-scroll window (configurable: 30s/60s/120s/300s)
- Grid, axis labels, legend, dark/light mode aware
- PNG export, CSV export of the visible window
- Session recording (CSV/SQLite/JSON) and playback via the sessionrec module
"""

import json
import os
import time
import csv
from typing import Dict, List, Optional, Tuple

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

try:
    from sessionrec.session_logger import SessionLogger
    from sessionrec.replay import SessionReplayer
    SESSION_REC_AVAILABLE = True
except Exception:
    SessionLogger = None
    SessionReplayer = None
    SESSION_REC_AVAILABLE = False


# Sensor color palette (as specified in task)
SENSOR_COLORS = {
    'engine_rpm':         '#ff4444',  # red
    'vehicle_speed':      '#ffaa44',  # orange
    'throttle_position':  '#aa44ff',  # purple
    'coolant_temp':       '#44aaff',  # blue
    'intake_air_temp':    '#44ffff',  # cyan
    'maf_sensor':         '#ff44aa',  # pink
    'oxygen_sensor':      '#ffff44',  # yellow
    'oxygen_sensor_left': '#ffff88',  # light yellow
    'oxygen_sensor_right':'#ffff00',  # bright yellow
    'battery_voltage':    '#44ff44',  # green
    'ignition_timing':    '#ff8844',  # amber
    'iacv_aacv':          '#88ff44',  # lime
    'af_alpha':           '#44ff88',  # mint
    'injector_pulse':     '#8844ff',  # violet
    'injector_duty':      '#cc44ff',  # magenta
    'maf_voltage':        '#ff4488',  # rose
}

SENSOR_LABELS = {
    'engine_rpm':         'Engine RPM',
    'vehicle_speed':      'Vehicle Speed',
    'throttle_position':  'Throttle Position',
    'coolant_temp':       'Coolant Temp',
    'intake_air_temp':    'Intake Air Temp',
    'maf_sensor':         'MAF Sensor',
    'oxygen_sensor':      'O2 Sensor',
    'oxygen_sensor_left': 'O2 Sensor (L)',
    'oxygen_sensor_right':'O2 Sensor (R)',
    'battery_voltage':    'Battery Voltage',
    'ignition_timing':    'Ignition Timing',
    'iacv_aacv':          'IACV-AAC/V',
    'af_alpha':           'A/F Alpha',
    'injector_pulse':     'Injector Pulse',
    'injector_duty':      'Injector Duty',
    'maf_voltage':        'MAF Voltage',
}

SENSOR_UNITS = {
    'engine_rpm':         'RPM',
    'vehicle_speed':      'km/h',
    'throttle_position':  '%',
    'coolant_temp':       '°C',
    'intake_air_temp':    '°C',
    'maf_sensor':         'g/s',
    'oxygen_sensor':      'V',
    'oxygen_sensor_left': 'V',
    'oxygen_sensor_right':'V',
    'battery_voltage':    'V',
    'ignition_timing':    'BTDC',
    'iacv_aacv':          '%',
    'af_alpha':           '%',
    'injector_pulse':     'ms',
    'injector_duty':      '%',
    'maf_voltage':        'V',
}


def plot_xy(
    t: float,
    v: float,
    window_start: float,
    window_seconds: float,
    y_min: float,
    y_max: float,
    plot_x0: float,
    plot_y0: float,
    plot_width: float,
    plot_height: float,
) -> Tuple[float, float]:
    """Map a time/value sample to Cairo pixel coordinates (y inverted).

    Pure function, no GTK/cairo dependency, so the plotting math can be
    unit-tested in isolation.
    """
    span = y_max - y_min
    if span <= 0:
        span = 1.0
    if window_seconds <= 0:
        window_seconds = 1.0

    x_frac = (t - window_start) / window_seconds
    y_frac = (v - y_min) / span
    x = plot_x0 + x_frac * plot_width
    # Cairo y grows downward, so invert.
    y = plot_y0 + plot_height - y_frac * plot_height
    # Clamp to the plot rectangle.
    x = max(plot_x0, min(plot_x0 + plot_width, x))
    y = max(plot_y0, min(plot_y0 + plot_height, y))
    return x, y


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

        # Sensor visibility checkboxes (shown in the separate Sources window)
        self.checkboxes: Dict[str, Gtk.CheckButton] = {}
        for key in SENSOR_COLORS:
            cb = Gtk.CheckButton(label=SENSOR_LABELS[key])
            cb.set_active(True)
            cb.connect("toggled", self._on_sensor_toggled, key)
            self.checkboxes[key] = cb

        # Sources button opens a separate window for source selection
        sources_btn = Gtk.Button(label="Sources")
        sources_btn.set_tooltip_text("Select graphed sensor sources")
        sources_btn.connect("clicked", self._on_sources_clicked)
        toolbar.append(sources_btn)

        toolbar.append(Gtk.Separator())

        # PNG export button
        record_btn = Gtk.Button.new_from_icon_name("document-save")
        record_btn.set_label(" PNG")
        record_btn.set_tooltip_text("Export the current graph to a PNG image")
        record_btn.connect("clicked", self._on_record_clicked)
        toolbar.append(record_btn)

        # CSV export button
        csv_btn = Gtk.Button.new_from_icon_name("document-save-as")
        csv_btn.set_label(" CSV")
        csv_btn.set_tooltip_text("Export the selected sensor data to a CSV file")
        csv_btn.connect("clicked", self._on_export_csv)
        toolbar.append(csv_btn)

        toolbar.append(Gtk.Separator())

        # Session recording controls
        if SESSION_REC_AVAILABLE and data_processor is not None:
            self.session_logger = SessionLogger(data_processor)
            self._last_saved_path = ""
        else:
            self.session_logger = None
            self._last_saved_path = ""

        self.record_btn = Gtk.Button.new_from_icon_name("media-record")
        self.record_btn.set_label(" Record")
        self.record_btn.set_tooltip_text("Start/stop recording a diagnostic session")
        self.record_btn.connect("clicked", self._on_record_session)
        toolbar.append(self.record_btn)

        self.rec_format_combo = Gtk.ComboBoxText.new()
        self.rec_format_combo.append_text("CSV")
        self.rec_format_combo.append_text("SQLite")
        self.rec_format_combo.append_text("JSON")
        self.rec_format_combo.set_active(0)
        self.rec_format_combo.set_tooltip_text("Recorded session output format")
        toolbar.append(self.rec_format_combo)

        self.rec_status = Gtk.Label(label="Not recording")
        toolbar.append(self.rec_status)

        toolbar.append(Gtk.Separator())

        # Session playback controls
        if SESSION_REC_AVAILABLE and data_processor is not None:
            self.replayer = SessionReplayer(data_processor)
        else:
            self.replayer = None

        play_btn = Gtk.Button.new_from_icon_name("media-playback-start")
        play_btn.set_label(" Play")
        play_btn.set_tooltip_text("Open and play a recorded session")
        play_btn.connect("clicked", self._on_open_session)
        toolbar.append(play_btn)

        self.play_pause_btn = Gtk.Button.new_from_icon_name("media-playback-pause")
        self.play_pause_btn.set_label(" Pause")
        self.play_pause_btn.set_tooltip_text("Play/pause playback")
        self.play_pause_btn.set_sensitive(False)
        self.play_pause_btn.connect("clicked", self._on_play_pause)
        toolbar.append(self.play_pause_btn)

        self.replay_stop_btn = Gtk.Button.new_from_icon_name("media-playback-stop")
        self.replay_stop_btn.set_label(" Stop")
        self.replay_stop_btn.set_tooltip_text("Stop playback")
        self.replay_stop_btn.set_sensitive(False)
        self.replay_stop_btn.connect("clicked", self._on_replay_stop)
        toolbar.append(self.replay_stop_btn)

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
        """Advance replay playback, refresh recording status, redraw."""
        if self.replayer is not None and self.replayer.is_loaded and self.replayer.is_playing:
            self.replayer.pump()
            if not self.replayer.is_playing:
                self._update_replay_state()
        self._update_recording_status()
        self.graph_area.queue_draw()
        return True

    def _on_sensor_toggled(self, check_button: Gtk.CheckButton, sensor_key: str):
        """Handle sensor checkbox toggle."""
        self.graph_area.queue_draw()

    def _on_sources_clicked(self, button: Gtk.Button):
        """Open a separate window for selecting graphed sources."""
        window = getattr(self, "_sources_window", None)
        if window is None or not window.get_visible():
            window = Gtk.Window(title="Sources")
            window.set_default_size(260, 360)
            try:
                root = self.get_root()
                if root is not None:
                    window.set_transient_for(root)
            except Exception:
                pass
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(8)
            box.set_margin_end(8)
            title = Gtk.Label(label="Graph sources")
            title.add_css_class("heading")
            box.append(title)
            for key in SENSOR_COLORS:
                cb = self.checkboxes[key]
                try:
                    if cb.get_parent() is not None:
                        cb.unparent()
                except Exception:
                    pass
                box.append(cb)
            window.set_child(box)
            window.connect("close-request", self._on_sources_close)
            self._sources_window = window
        window.present()

    def _on_sources_close(self, window):
        self._sources_window = None
        return False

    def set_sensor_active(self, sensor_key: str, active: bool):
        """Programmatically enable/disable a sensor for graphing.

        Used by the external Sources dialog to control visibility.
        """
        if sensor_key in self.checkboxes:
            self.checkboxes[sensor_key].set_active(active)
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

    def _on_export_csv(self, button: Gtk.Button):
        """Export the currently visible sensor data to a CSV file.

        One column per enabled sensor; rows are aligned by timestamp.
        Only sensors with data in the current time window are exported.
        """
        if not self.data_processor:
            self._show_error("No sensor data available to export.")
            return

        now = time.time()
        window_start = now - self.time_window_seconds

        # Gather enabled sensors and their in-window history points.
        series: Dict[str, List[Tuple[float, float]]] = {}
        for key in SENSOR_COLORS:
            if not self.checkboxes[key].get_active():
                continue
            history = self.data_processor.get_history(key)
            points = [(t, v) for t, v in history if t >= window_start]
            if points:
                series[key] = points

        if not series:
            self._show_error("No data for the selected sensors in this window.")
            return

        filename = f"opengonsult_data_{int(time.time())}.csv"
        try:
            self._write_csv(filename, series)
            self._show_info(f"Data exported to: {filename}")
        except Exception as e:
            self._show_error(f"Failed to export CSV: {e}")

    def _write_csv(self, filename: str, series: Dict[str, List[Tuple[float, float]]]):
        """Write sensor time-series data to a CSV file.

        Columns: timestamp followed by one column per sensor. Rows with
        no value for a sensor are left blank so all series share the same
        time column while keeping their own sampling instants.
        """
        headers = ["timestamp"] + [SENSOR_LABELS[key] for key in series.keys()]
        keys = list(series.keys())

        # Union of all timestamps across enabled sensors, ascending.
        all_times = sorted({t for pts in series.values() for t, _ in pts})
        lookup = {}
        for key in keys:
            lookup[key] = {t: v for t, v in series[key]}

        with open(filename, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            for t in all_times:
                row = [f"{t:.3f}"]
                for key in keys:
                    value = lookup[key].get(t)
                    row.append("" if value is None else f"{value:.6g}")
                writer.writerow(row)

    # ---- session recording / playback handlers --------------------------

    def _on_record_session(self, button: Gtk.Button):
        """Start recording immediately, or stop and save the session."""
        if self.session_logger is None:
            self._show_error("Session recording module not available.")
            return

        if not self.session_logger.is_recording:
            fmt_map = {"CSV": ".csv", "SQLite": ".sqlite", "JSON": ".json"}
            ext = fmt_map.get(self.rec_format_combo.get_active_text(), ".csv")
            path = f"opengonsult_session_{int(time.time())}{ext}"
            self._last_saved_path = path
            self.session_logger.start()
            self.rec_status.set_markup("<span foreground='red'>● Recording...</span>")
            self.record_btn.set_label(" Stop")
            self.rec_format_combo.set_sensitive(False)
        else:
            self.session_logger.stop()
            self._last_saved_path = self.session_logger.save(self._last_saved_path)
            self.rec_status.set_text("Not recording")
            self.record_btn.set_label(" Record")
            self.rec_format_combo.set_sensitive(True)
            self._show_info(f"Session saved: {self._last_saved_path}")

    def _update_recording_status(self):
        """Keep the recording UI in sync (used by the timeout tick)."""
        if self.session_logger is not None and self.session_logger.is_recording:
            self.record_btn.set_label(" Stop")
            self.rec_status.set_markup("<span foreground='red'>● Recording...</span>")
            self.rec_format_combo.set_sensitive(False)
        else:
            self.record_btn.set_label(" Record")
            self.rec_status.set_text("Not recording")
            self.rec_format_combo.set_sensitive(True)

    def _on_open_session(self, button: Gtk.Button):
        """Open a session file for playback."""
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Open Diagnostic Session")
        dialog.accept(self, self._on_session_loaded, None)
        dialog.present(self.get_root())

    def _on_session_loaded(self, dialog, result, _):
        try:
            file = dialog.get_future_file(self, result)
            if file:
                path = file.get_path()
                self.replayer.load(path)
                self._update_replay_state()
                self._show_info(f"Loaded: {path}")
        except Exception as e:
            self._show_error(f"Failed to load session: {e}")

    def _on_play_pause(self, button: Gtk.Button):
        if self.replayer.is_playing:
            self.replayer.pause()
        else:
            self.replayer.play()
        self._update_replay_state()

    def _on_replay_stop(self, button: Gtk.Button):
        if self.replayer:
            self.replayer.stop()
        self._update_replay_state()

    def _update_replay_state(self):
        if self.replayer is None:
            return

        is_loaded = self.replayer.is_loaded
        is_playing = self.replayer.is_playing

        self.play_pause_btn.set_sensitive(is_loaded)
        self.replay_stop_btn.set_sensitive(is_loaded)

        if is_playing:
            self.play_pause_btn.set_icon_name("media-playback-pause")
        else:
            self.play_pause_btn.set_icon_name("media-playback-start")

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
        cr.set_source_rgba(*text_color)
        cr.select_font_face("sans-serif")
        cr.set_font_size(11)

        # Draw time ticks and labels
        num_ticks = 5
        for i in range(num_ticks + 1):
            tick_time = window_start + (i / num_ticks) * self.time_window_seconds
            tick_x = plot_x0 + (i / num_ticks) * plot_width

            # Draw tick line
            cr.move_to(tick_x, plot_y0 + plot_height)
            cr.line_to(tick_x, plot_y0 + plot_height + 5)
            cr.stroke()

            # Draw label (e.g., "-60s", "-30s", "0s", etc.)
            # Using a relative offset from 'now' for better UX
            rel_time = tick_time - time.time()
            label = f"{rel_time:+.0f}s" if abs(rel_time) > 1 else "now"

            label_width = cr.text_extents(label).width
            cr.move_to(tick_x - label_width / 2, plot_y0 + plot_height + 20)
            cr.show_text(label)

        # --- Draw sensor data lines ---
        for key, points in sensor_data.items():
            color_hex = SENSOR_COLORS[key]
            r = int(color_hex[1:3], 16) / 255.0
            g = int(color_hex[3:5], 16) / 255.0
            b = int(color_hex[5:7], 16) / 255.0

            cr.set_source_rgba(r, g, b, 0.9)
            cr.set_line_width(2.0 * self.zoom_level)

            for i, (t, v) in enumerate(points):
                x, y = plot_xy(
                    t,
                    v,
                    window_start,
                    self.time_window_seconds,
                    y_min,
                    y_max,
                    plot_x0,
                    plot_y0,
                    plot_width,
                    plot_height,
                )

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
            cr.set_line_width(2.5)
            cr.move_to(legend_x, legend_y_current + 6)
            cr.line_to(legend_x + 16, legend_y_current + 6)
            cr.stroke()
            cr.set_source_rgba(*text_color)
            label = SENSOR_LABELS[key]
            cr.move_to(legend_x + 22, legend_y_current + 10)
            cr.show_text(label)
            legend_y_current += 20

    def destroy(self):
        """Clean up the timeout when widget is destroyed."""
        if hasattr(self, '_timeout_id') and self._timeout_id:
            GLib.source_remove(self._timeout_id)
        super().destroy()
