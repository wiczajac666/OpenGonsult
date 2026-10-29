"""
OpenGonsult - GTK4 main window.

Nissan CONSULT-I diagnostic suite for Linux (14-pin connector).

Single-file GUI with a GNOME-settings style left navigation panel and five
pages: Dashboard, Graphing, Error Codes, Settings and About. Configuration is
persisted to ~/.config/opengonsult/config.json.

Integration points:
    ecu/sensors.py       DashboardDataProcessor / SensorType / SensorReading
    ecu/ecu_db.py        ECUDatabase sensor scaling + DTC translations
    ecu/dtc.py           CONSULT-I single-byte DTC decoder + fault-code index
    serial/adapter.py    SerialAdapter (asyncio) serial transport
    protocol/consult.py  CONSULT-I packet framing and checksums
"""

import asyncio
import concurrent.futures
import json
import math
import os
import queue as thread_queue
import threading
import time

import cairo
import gi
gi.require_version('Gdk', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, Gio, Gtk, GLib, Pango

from dashboard.simulator import SimulationEngine

try:
    from ecu.ecu_db import ECUDatabase
except ImportError:
    ECUDatabase = None

try:
    from ecu.sensors import DashboardDataProcessor, SensorReading, SensorType
except ImportError:
    DashboardDataProcessor = None
    SensorReading = None
    SensorType = None

try:
    from ecu import dtc as dtc_module
    _DECODE_DTC_CODES = dtc_module.decode_dtc_codes
    _DTC_DESCRIBE = dtc_module.describe
except ImportError:
    dtc_module = None
    _DECODE_DTC_CODES = None
    _DTC_DESCRIBE = None

try:
    from serial.adapter import SerialAdapter, SerialConfig
except ImportError:
    SerialAdapter = None
    SerialConfig = None

try:
    from protocol.consult import RequestPacket, ResponsePacket
except ImportError:
    RequestPacket = None
    ResponsePacket = None

try:
    from graphs.sensor_graph import SensorGraphWidget
except ImportError:
    SensorGraphWidget = None


APP_ID = "org.opengonsult.OpenGonsult"
APP_NAME = "OpenGonsult"
from gui import __version__ as APP_VERSION
APP_DESCRIPTION = (
    "Open-source diagnostic suite for Nissan vehicles equipped with the "
    "CONSULT-I (14-pin) diagnostic interface. Reads live engine sensors, "
    "records data graphs and manages diagnostic trouble codes."
)
CONFIG_DIR = os.path.expanduser("~/.config/opengonsult")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400]
POLL_INTERVAL_MS = 500
GAUGE_INTERVAL_MS = 500
SIM_INTERVAL_MS = 200
GRAPH_HISTORY_SECONDS = 300

GAUGE_DEFS = [
    ("engine_rpm", "Engine RPM", "RPM", 0.0, 8000.0),
    ("coolant_temp", "Coolant Temp", "deg C", -40.0, 150.0),
    ("battery_voltage", "Battery Voltage", "V", 8.0, 16.0),
    ("vehicle_speed", "Vehicle Speed", "km/h", 0.0, 250.0),
    ("throttle_position", "Throttle Position", "%", 0.0, 100.0),
    ("oxygen_sensor", "O2 Sensor", "V", 0.0, 1.5),
]

SENSOR_UNITS = {key: unit for key, _label, unit, _lo, _hi in GAUGE_DEFS}
GAUGE_RANGES = {key: (lo, hi) for key, _label, _unit, lo, hi in GAUGE_DEFS}
GAUGE_DIGITS = {
    "engine_rpm": 0,
    "coolant_temp": 1,
    "battery_voltage": 2,
    "vehicle_speed": 0,
    "throttle_position": 0,
    "oxygen_sensor": 2,
}

CONSULT_ECU_ID = 1
CONSULT_MODE_LIVE_DATA = 0x01
CONSULT_CMD_DTC_READ = 0xD1
CONSULT_CMD_DTC_CLEAR = 0xC1
SENSOR_COMMANDS = {
    "engine_rpm": 0x09,
    "coolant_temp": 0x0B,
    "battery_voltage": 0x14,
    "vehicle_speed": 0x08,
    "throttle_position": 0x11,
    "oxygen_sensor": 0x13,
    "oxygen_sensor_left": 0x13,
    "oxygen_sensor_right": 0x15,
    "intake_air_temp": 0x0C,
    "maf_sensor": 0x04,
    "maf_voltage": 0x04,
    "ignition_timing": 0x1C,
    "iacv_aacv": 0x10,
    "af_alpha": 0x12,
    "injector_pulse": 0x16,
    "injector_duty": 0x17,
}

SEVERITY_CSS = {"critical": "error", "warning": "warning", "info": "success"}

THEME_NAMES = ("System", "Dark", "Light")
_THEMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes")


def load_config():
    config = {
        "theme": "system",
        "dark_mode": True,
        "serial_port": "/dev/ttyUSB0",
        "baud_rate": 9600,
        "simulation": False,
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
            for key in list(config.keys()):
                if key in stored:
                    config[key] = stored[key]
        if "theme" not in config and "dark_mode" in stored:
            config["theme"] = "dark" if stored["dark_mode"] else "light"
        if config["theme"] not in ("system", "dark", "light"):
            config["theme"] = "system"
    except (OSError, ValueError):
        pass
    return config


def save_config(config):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp_path = CONFIG_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2)
        os.replace(tmp_path, CONFIG_FILE)
    except OSError:
        pass


class ConnectionWorker(threading.Thread):
    """Background thread owning the asyncio loop that drives SerialAdapter.

    The UI thread posts actions through submit() and receives results via
    concurrent futures, marshalling back into the GTK main loop with
    GLib.idle_add on the caller side.
    """

    def __init__(self, port, baud_rate):
        super().__init__(daemon=True)
        self.port = port
        self.baud_rate = baud_rate
        self._commands = thread_queue.Queue()
        self._loop = None
        self._adapter = None
        self._db = ECUDatabase() if ECUDatabase is not None else None
        self._stop_requested = False

    def submit(self, action, data=None):
        future = concurrent.futures.Future()
        self._commands.put((action, data, future))
        return future

    def request_stop(self):
        self._stop_requested = True

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        while not self._stop_requested:
            try:
                action, data, future = self._commands.get(timeout=0.1)
            except thread_queue.Empty:
                continue
            if self._stop_requested:
                break
            handler = getattr(self, "_do_" + action)
            try:
                future.set_result(self._loop.run_until_complete(handler(data)))
            except Exception as exc:
                future.set_exception(exc)
        self._shutdown()

    def _shutdown(self):
        if self._adapter is not None:
            try:
                self._loop.run_until_complete(self._adapter.disconnect())
            except Exception:
                pass
            self._adapter = None
        try:
            self._loop.close()
        except Exception:
            pass

    async def _ensure_adapter(self):
        if self._adapter is None:
            self._adapter = SerialAdapter()
        return self._adapter

    async def _do_connect(self, _data):
        adapter = await self._ensure_adapter()
        await adapter.disconnect()
        if SerialConfig is None:
            raise ConnectionError("Serial backend unavailable")
        config = SerialConfig(
            port=self.port,
            baud_rate=int(self.baud_rate),
            timeout=1.0,
            auto_reconnect=False,
            heartbeat_interval_s=0.0,
        )
        await adapter.connect(config)
        return True

    async def _do_disconnect(self, _data):
        if self._adapter is not None:
            await self._adapter.disconnect()
        return True

    async def _do_poll(self, _data):
        adapter = await self._ensure_adapter()
        readings = []
        for key, command_id in SENSOR_COMMANDS.items():
            request = RequestPacket(mode=CONSULT_MODE_LIVE_DATA)
            frame = request.encode(command_id)
            raw = await adapter.transaction(frame)
            value = self._decode_live_value(key, raw)
            if value is not None:
                readings.append((key, value))
        return readings

    async def _do_read_dtc(self, _data):
        adapter = await self._ensure_adapter()
        request = RequestPacket(mode=CONSULT_CMD_DTC_READ)
        frame = request.encode(0x00)
        raw = await adapter.transaction(frame)
        return self._decode_dtc_list(raw)

    async def _do_clear_dtc(self, _data):
        adapter = await self._ensure_adapter()
        request = RequestPacket(mode=CONSULT_CMD_DTC_CLEAR)
        frame = request.encode(0x00)
        await adapter.transaction(frame)
        return True

    async def _do_activate(self, data):
        adapter = await self._ensure_adapter()
        command = (data or {}).get("command")
        if command is None:
            return False
        await adapter.transaction(command)
        return True

    def _decode_live_value(self, key, raw_bytes):
        if not raw_bytes or ResponsePacket is None:
            return None
        raw = bytes(raw_bytes)
        if len(raw) >= 2:
            payload = raw[-2:]
        else:
            payload = b"\x00" + raw
        try:
            response = ResponsePacket(payload=payload)
            _sub, values = response.decode()
        except Exception:
            return None
        if not values:
            return None
        physical = float(values[0])
        if self._db is not None:
            definition = self._db.get_sensor_definition(CONSULT_ECU_ID, key)
            if definition is not None:
                physical = definition.decode(int(values[0]))
        if key in GAUGE_RANGES:
            low, high = GAUGE_RANGES[key]
            physical = max(low, min(high, physical))
        return physical

    def _decode_dtc_list(self, raw_bytes):
        """Decode raw Consult DTC response bytes into display code strings.

        Uses the real single-byte Consult format from ecu/dtc.py. Returns an
        empty list when the decoder is unavailable or the payload is empty.
        """
        if _DECODE_DTC_CODES is None:
            return []
        try:
            return _DECODE_DTC_CODES(raw_bytes or b"")
        except Exception:
            return []


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


class MainWindow(Gtk.ApplicationWindow):
    """Main application window with left navigation panel."""

    NAV_ITEMS = [
        ("dashboard", "view-grid-symbolic", "Dashboard"),
        ("graphing", "utilities-system-monitor-symbolic", "Graphing"),
        ("diagnostics", "dialog-warning-symbolic", "Diagnostics"),
        ("active_tests", "system-run-symbolic", "Active Tests"),
        ("settings", "preferences-system-symbolic", "Settings"),
        ("about", "help-about-symbolic", "About"),
    ]

    def __init__(self, application):
        super().__init__(application=application)
        self.set_title(APP_NAME + " " + APP_VERSION)
        self.set_default_size(1120, 720)

        self.config = load_config()
        self.processor = (
            DashboardDataProcessor(graph_history_seconds=GRAPH_HISTORY_SECONDS)
            if DashboardDataProcessor is not None
            else None
        )
        self.db = ECUDatabase() if ECUDatabase is not None else None
        self.worker = None
        self.connected = False
        self.simulating = bool(self.config.get("simulation"))
        self.sim_start_time = None
        self.dtc_codes = []

        self.gauges = {}
        self.timer_ids = []
        self.loading_ui = True

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.connect_button = Gtk.Button(label="Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.connect("clicked", self.on_connect_clicked)
        header.pack_start(self.connect_button)
        self.disconnect_button = Gtk.Button(label="Disconnect")
        self.disconnect_button.set_sensitive(False)
        self.disconnect_button.connect("clicked", self.on_disconnect_clicked)
        header.pack_start(self.disconnect_button)
        sim_label = Gtk.Label(label="Simulation")
        self.sim_switch = Gtk.Switch()
        self.sim_switch.set_active(self.simulating)
        self.sim_switch.set_valign(Gtk.Align.CENTER)
        self.sim_switch.connect("state-set", self.on_sim_toggled)
        sim_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sim_box.append(sim_label)
        sim_box.append(self.sim_switch)
        header.pack_end(sim_box)
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content.set_vexpand(True)
        root.append(content)

        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        nav_scroll.set_size_request(190, -1)
        content.append(nav_scroll)

        self.nav_list = Gtk.ListBox()
        self.nav_list.add_css_class("navigation-sidebar")
        self.nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav_list.connect("row-selected", self.on_nav_selected)
        nav_scroll.set_child(self.nav_list)

        content.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        content.append(self.stack)

        self.build_dashboard_page()
        self.build_graphing_page()
        self.build_diagnostics_page()
        self.build_active_tests_page()
        self.build_settings_page()
        self.build_about_page()

        for page_id, icon_name, title in self.NAV_ITEMS:
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            icon = Gtk.Image.new_from_icon_name(icon_name)
            label = Gtk.Label(label=title, xalign=0.0)
            row_box.append(icon)
            row_box.append(label)
            row = Gtk.ListBoxRow()
            row.set_child(row_box)
            row.page_id = page_id
            self.nav_list.append(row)
        self.nav_list.select_row(self.nav_list.get_row_at_index(0))

        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.set_margin_top(4)
        status_box.set_margin_bottom(4)
        status_box.set_margin_start(10)
        status_box.set_margin_end(10)
        status_box.add_css_class("statusbar")
        self.status_image = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        status_box.append(self.status_image)
        self.status_label = Gtk.Label(label="Ready", xalign=0.0)
        self.status_label.set_hexpand(True)
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
        status_box.append(self.status_label)
        root.append(status_box)

        self.dark_mode = self.apply_theme(str(self.config.get("theme", "system")))
        self.start_gauge_timer()
        if self.simulating:
            self.start_simulation()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def on_nav_selected(self, _box, row):
        if row is not None:
            self.stack.set_visible_child_name(row.page_id)

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    def build_dashboard_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        title = Gtk.Label(label="Live Dashboard", xalign=0.0)
        title.add_css_class("title-2")
        page.append(title)

        grid = Gtk.Grid()
        grid.set_row_spacing(16)
        grid.set_column_spacing(24)
        grid.set_column_homogeneous(True)
        page.append(grid)

        for index, (key, label_text, unit, minimum, maximum) in enumerate(GAUGE_DEFS):
            gauge = GaugeWidget(
                label_text,
                unit,
                minimum,
                maximum,
                digits=GAUGE_DIGITS.get(key, 1),
            )
            self.gauges[key] = gauge
            grid.attach(gauge, index % 3, index // 3, 1, 1)

        note = Gtk.Label(xalign=0.0)
        note.add_css_class("dim-label")
        if SerialAdapter is None or self.processor is None:
            note.set_text("Backend modules unavailable; live data disabled.")
        else:
            note.set_text(
                "Connect to an ECU or enable Simulation to stream live data. "
                "Values are smoothed by DashboardDataProcessor."
            )
        page.append(note)

        self.stack.add_named(page, "dashboard")

    def start_gauge_timer(self):
        timer_id = GLib.timeout_add(GAUGE_INTERVAL_MS, self.refresh_gauges)
        self.timer_ids.append(timer_id)

    def refresh_gauges(self):
        if self.processor is None:
            return True
        for key, _label, _unit, _lo, _hi in GAUGE_DEFS:
            value = self.processor.get_current_value(key)
            if value is None:
                continue
            self.gauges[key].set_value(float(value))
        return True

    # ------------------------------------------------------------------
    # Graphing page
    # ------------------------------------------------------------------

    def build_graphing_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        title = Gtk.Label(label="Graphing", xalign=0.0)
        title.add_css_class("title-2")
        page.append(title)

        if SensorGraphWidget is not None and self.processor is not None:
            graph_widget = SensorGraphWidget(
                data_processor=self.processor,
                config_file=CONFIG_FILE,
            )
            page.append(graph_widget)
            self.graph_widget = graph_widget
        else:
            placeholder = Gtk.Label(label="Sensor graph module unavailable.")
            placeholder.set_vexpand(True)
            placeholder.set_valign(Gtk.Align.CENTER)
            page.append(placeholder)

        self.stack.add_named(page, "graphing")

    # ------------------------------------------------------------------
    # Error codes page
    # ------------------------------------------------------------------

    def build_diagnostics_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        title = Gtk.Label(label="Diagnostics", xalign=0.0)
        title.add_css_class("title-2")
        page.append(title)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.read_dtc_button = Gtk.Button(label="Read Codes")
        self.read_dtc_button.add_css_class("suggested-action")
        self.read_dtc_button.connect("clicked", self.on_read_dtc_clicked)
        buttons.append(self.read_dtc_button)
        self.clear_dtc_button = Gtk.Button(label="Clear Codes")
        self.clear_dtc_button.add_css_class("destructive-action")
        self.clear_dtc_button.connect("clicked", self.on_clear_dtc_clicked)
        buttons.append(self.clear_dtc_button)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        buttons.append(spacer)
        self.dtc_summary_label = Gtk.Label(label="No codes loaded.", xalign=1.0)
        self.dtc_summary_label.add_css_class("dim-label")
        buttons.append(self.dtc_summary_label)
        page.append(buttons)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        page.append(scroll)

        self.dtc_list = Gtk.ListBox()
        self.dtc_list.add_css_class("boxed-list")
        self.dtc_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(self.dtc_list)

        empty_row = Gtk.ListBoxRow()
        empty_label = Gtk.Label(label="Press Read Codes to query the ECU.")
        empty_label.set_margin_top(14)
        empty_label.set_margin_bottom(14)
        empty_row.set_child(empty_label)
        self.dtc_list.append(empty_row)

        self.stack.add_named(page, "diagnostics")

    def set_dtc_rows(self, codes):
        child = self.dtc_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.dtc_list.remove(child)
            child = next_child
        self.dtc_codes = list(codes)
        if not codes:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label="No diagnostic trouble codes stored.")
            label.set_margin_top(14)
            label.set_margin_bottom(14)
            row.set_child(label)
            self.dtc_list.append(row)
            self.dtc_summary_label.set_text("ECU reported no codes.")
            return
        for code in codes:
            definition = None
            if self.db is not None:
                definition = self.db.get_dtc_definition(code)
            self.dtc_list.append(self.build_dtc_row(code, definition))
        self.dtc_summary_label.set_text("{0} code(s) stored.".format(len(codes)))

    def build_dtc_row(self, code, definition):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(14)
        box.set_margin_end(14)
        row.set_child(box)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        code_label = Gtk.Label(label=code, xalign=0.0)
        code_label.add_css_class("heading")
        code_label.set_hexpand(True)
        head.append(code_label)
        severity = getattr(definition, "severity", "info") if definition else "info"
        badge = Gtk.Label(label=severity.upper())
        badge.add_css_class(SEVERITY_CSS.get(severity, "dim-label"))
        badge.add_css_class("caption")
        head.append(badge)
        box.append(head)

        description = getattr(definition, "description", "") if definition else ""
        desc_text = description or "Translation unavailable in ECU database."
        desc_label = Gtk.Label(label=desc_text, xalign=0.0, wrap=True)
        desc_label.set_xalign(0.0)
        box.append(desc_label)

        causes = getattr(definition, "possible_causes", []) if definition else []
        if causes:
            causes_label = Gtk.Label(
                label="Possible causes: " + "; ".join(causes),
                xalign=0.0,
                wrap=True,
            )
            causes_label.add_css_class("dim-label")
            causes_label.set_xalign(0.0)
            box.append(causes_label)

        actions = getattr(definition, "recommended_actions", []) if definition else []
        if actions:
            actions_label = Gtk.Label(
                label="Recommended actions: " + "; ".join(actions),
                xalign=0.0,
                wrap=True,
            )
            actions_label.add_css_class("dim-label")
            actions_label.set_xalign(0.0)
            box.append(actions_label)
        return row

    def require_connection_for_dtc(self):
        if self.connected or self.simulating:
            return True
        self.show_info(
            "Not connected",
            "Connect to the ECU first, or enable Simulation mode.",
        )
        return False

    def on_read_dtc_clicked(self, _button):
        if not self.require_connection_for_dtc():
            return
        if self.simulating or self.worker is None:
            sample = ["13", "08"] if (self.db is not None or dtc_module is not None) else []
            self.set_dtc_rows(sample)
            self.set_status("Simulated DTC scan complete.", "dialog-question-symbolic")
            return
        self.read_dtc_button.set_sensitive(False)
        self.set_status("Reading diagnostic trouble codes...", "dialog-question-symbolic")
        future = self.worker.submit("read_dtc")
        future.add_done_callback(
            lambda fut: GLib.idle_add(self.on_read_dtc_done, fut)
        )

    def on_read_dtc_done(self, future):
        self.read_dtc_button.set_sensitive(True)
        try:
            codes = future.result()
        except Exception as exc:
            self.show_error("DTC read failed", str(exc))
            self.set_status("DTC read failed.", "dialog-error-symbolic")
            return False
        self.set_dtc_rows(codes)
        self.set_status(
            "Found {0} trouble code(s).".format(len(codes)),
            "dialog-warning-symbolic" if codes else "dialog-information-symbolic",
        )
        return False

    def on_clear_dtc_clicked(self, _button):
        if not self.require_connection_for_dtc():
            return
        self.confirm(
            "Clear diagnostic trouble codes?",
            "This erases all stored trouble codes from the ECU memory. "
            "Freeze-frame data will also be lost.",
            self.perform_clear_dtc,
        )

    def perform_clear_dtc(self):
        if self.simulating or self.worker is None:
            self.set_dtc_rows([])
            self.set_status("Simulated DTC clear complete.", "dialog-information-symbolic")
            return
        self.clear_dtc_button.set_sensitive(False)
        self.set_status("Clearing diagnostic trouble codes...", "dialog-question-symbolic")
        future = self.worker.submit("clear_dtc")
        future.add_done_callback(
            lambda fut: GLib.idle_add(self.on_clear_dtc_done, fut)
        )

    def on_clear_dtc_done(self, future):
        self.clear_dtc_button.set_sensitive(True)
        try:
            future.result()
        except Exception as exc:
            self.show_error("DTC clear failed", str(exc))
            self.set_status("DTC clear failed.", "dialog-error-symbolic")
            return False
        self.set_dtc_rows([])
        self.set_status("Trouble codes cleared.", "dialog-information-symbolic")
        return False

    def on_power_balance_clicked(self, _button):
        if not (self.connected or self.simulating):
            self.show_info("Not connected", "Connect to the ECU first.")
            return
        if self.worker is None:
            self.set_status("Simulated power balance (no ECU).", "dialog-information-symbolic")
            return
        try:
            from ecu.active_tests import power_balance_command
            cmd = power_balance_command(0)
            future = self.worker.submit("activate", {"command": cmd})
            future.add_done_callback(lambda fut: GLib.idle_add(self.on_active_done, fut))
        except Exception as exc:
            self.show_error("Active test failed", str(exc))

    def on_solenoid_tests_clicked(self, _button):
        self.set_status("Solenoid tests available on connected ECU.", "dialog-information-symbolic")

    def on_base_idle_clicked(self, _button):
        self.set_status("Base idle adjustment requested.", "dialog-information-symbolic")

    def on_clear_self_learn_clicked(self, _button):
        if not (self.connected or self.simulating):
            self.show_info("Not connected", "Connect to the ECU first.")
            return
        if self.worker is None:
            self.set_status("Simulated self-learn clear.", "dialog-information-symbolic")
            return
        try:
            from ecu.active_tests import clear_self_learn_command
            cmd = clear_self_learn_command()
            future = self.worker.submit("activate", {"command": cmd})
            future.add_done_callback(lambda fut: GLib.idle_add(self.on_active_done, fut))
        except Exception as exc:
            self.show_error("Active test failed", str(exc))

    def on_active_done(self, future):
        try:
            future.result()
            self.set_status("Active test complete.", "dialog-information-symbolic")
        except Exception as exc:
            self.show_error("Active test failed", str(exc))
        return False

    # ------------------------------------------------------------------
    # Settings page
    # ------------------------------------------------------------------

    def build_active_tests_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        title = Gtk.Label(label="Active Tests", xalign=0.0)
        title.add_css_class("title-2")
        page.append(title)

        note = Gtk.Label(xalign=0.0, wrap=True)
        note.set_text(
            "CONSULT-I activation commands (power balance, solenoid control, "
            "base idle, self-learn reset, ROM read). Connect to an ECU to run."
        )
        page.append(note)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for label, cb in (
            ("Power Balance", self.on_power_balance_clicked),
            ("Solenoid Tests", self.on_solenoid_tests_clicked),
            ("Base Idle", self.on_base_idle_clicked),
            ("Clear Self-Learn", self.on_clear_self_learn_clicked),
        ):
            btn = Gtk.Button(label=label)
            btn.connect("clicked", cb)
            buttons.append(btn)
        page.append(buttons)

        self.stack.add_named(page, "active_tests")

    def build_settings_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        title = Gtk.Label(label="Settings", xalign=0.0)
        title.add_css_class("title-2")
        page.append(title)

        form = Gtk.Grid()
        form.set_row_spacing(12)
        form.set_column_spacing(12)
        page.append(form)

        device_label = Gtk.Label(label="Serial device", xalign=0.0)
        form.attach(device_label, 0, 0, 1, 1)
        self.port_entry = Gtk.Entry()
        self.port_entry.set_placeholder_text("/dev/ttyUSB0")
        self.port_entry.set_text(str(self.config.get("serial_port", "")))
        self.port_entry.set_hexpand(True)
        self.port_entry.connect("changed", self.on_port_changed)
        form.attach(self.port_entry, 1, 0, 2, 1)

        scan_label = Gtk.Label(label="Detected ports", xalign=0.0)
        form.attach(scan_label, 0, 1, 1, 1)
        self.port_combo = Gtk.ComboBoxText()
        self.port_combo.set_hexpand(True)
        self.port_combo.connect("changed", self.on_detected_port_selected)
        form.attach(self.port_combo, 1, 1, 1, 1)
        scan_button = Gtk.Button(label="Scan Ports")
        scan_button.connect("clicked", self.on_scan_ports_clicked)
        form.attach(scan_button, 2, 1, 1, 1)

        baud_label = Gtk.Label(label="Baud rate", xalign=0.0)
        form.attach(baud_label, 0, 2, 1, 1)
        self.baud_combo = Gtk.ComboBoxText()
        for rate in BAUD_RATES:
            self.baud_combo.append_text(str(rate))
        saved_baud = str(int(self.config.get("baud_rate", BAUD_RATES[0])))
        if saved_baud in [str(rate) for rate in BAUD_RATES]:
            self.baud_combo.set_active(BAUD_RATES.index(int(saved_baud)))
        else:
            self.baud_combo.set_active(0)
        self.baud_combo.set_hexpand(True)
        self.baud_combo.connect("changed", self.on_baud_changed)
        form.attach(self.baud_combo, 1, 2, 2, 1)

        theme_label = Gtk.Label(label="Theme", xalign=0.0)
        form.attach(theme_label, 0, 3, 1, 1)
        self.theme_combo = Gtk.ComboBoxText()
        for name in THEME_NAMES:
            self.theme_combo.append_text(name)
        saved_theme = str(self.config.get("theme", "system")).title()
        self.theme_combo.set_active(THEME_NAMES.index(saved_theme) if saved_theme in THEME_NAMES else 0)
        self.theme_combo.set_hexpand(True)
        self.theme_combo.connect("changed", self.on_theme_changed)
        form.attach(self.theme_combo, 1, 3, 2, 1)

        hint = Gtk.Label(xalign=0.0)
        hint.add_css_class("dim-label")
        hint.set_wrap(True)
        hint.set_text(
            "CONSULT-I adapters typically use 9600 baud. Free-text device paths "
            "such as /dev/ttyUSB*, /dev/ttyACM* and /dev/rfcomm* are accepted. "
            "Settings are saved to ~/.config/opengonsult/config.json."
        )
        page.append(hint)

        self.stack.add_named(page, "settings")
        self.loading_ui = False
        self.refresh_port_list()

    def refresh_port_list(self, select_first=False):
        """Populate the detected-ports dropdown, preferring the saved device."""
        ports = []
        if SerialAdapter is not None:
            try:
                ports = list(SerialAdapter.detect_ports())
            except Exception:
                ports = []
        self.port_combo.remove_all()
        for port in ports:
            self.port_combo.append_text(port)
        saved = str(self.config.get("serial_port", ""))
        if saved in ports:
            self.port_combo.set_active(ports.index(saved))
        elif select_first and ports:
            self.port_combo.set_active(0)
        return ports

    def persist_settings(self):
        if self.loading_ui:
            return
        save_config(self.config)

    def on_port_changed(self, entry):
        self.config["serial_port"] = entry.get_text().strip()
        self.persist_settings()

    def on_scan_ports_clicked(self, _button):
        ports = self.refresh_port_list(select_first=True)
        if ports:
            self.set_status(
                "Detected {0} serial port(s).".format(len(ports)),
                "dialog-information-symbolic",
            )
        else:
            self.set_status("No serial ports detected.", "dialog-warning-symbolic")

    def on_detected_port_selected(self, combo):
        text = combo.get_active_text()
        if text:
            self.port_entry.set_text(text)

    def on_baud_changed(self, combo):
        text = combo.get_active_text()
        if text:
            self.config["baud_rate"] = int(text)
            self.persist_settings()

    def on_theme_changed(self, combo):
        text = combo.get_active_text()
        if text:
            theme = text.lower()
            self.config["theme"] = theme
            self.dark_mode = self.apply_theme(theme)
            self.config["dark_mode"] = self.dark_mode
            self.persist_settings()
            self.set_status(
                "Theme set to {0}.".format(text),
                "dialog-information-symbolic",
            )

    def _system_prefers_dark(self):
        settings = Gtk.Settings.get_default()
        if settings is None:
            return True
        theme = str(settings.get_property("gtk-theme-name") or "")
        return bool(settings.get_property("gtk-application-prefer-dark-theme")) or "dark" in theme.lower()

    def apply_theme(self, theme):
        """Resolve the requested theme and install its CSS palette.

        Returns True when the resolved appearance is dark so callers can keep
        the legacy dark_mode flag in sync (the graphing page reads it).
        """
        if theme == "system":
            dark = self._system_prefers_dark()
        else:
            dark = theme == "dark"
            settings = Gtk.Settings.get_default()
            if settings is not None:
                settings.set_property("gtk-application-prefer-dark-theme", dark)
        css_name = "dark.css" if dark else "light.css"
        self._load_css_provider(css_name)
        return dark

    def _load_css_provider(self, css_name):
        path = os.path.join(_THEMES_DIR, css_name)
        if not os.path.exists(path):
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(path)
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ------------------------------------------------------------------
    # About page
    # ------------------------------------------------------------------

    def build_about_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_valign(Gtk.Align.CENTER)
        page.set_halign(Gtk.Align.CENTER)
        page.set_margin_top(18)
        page.set_margin_bottom(18)
        page.set_margin_start(18)
        page.set_margin_end(18)

        name_label = Gtk.Label(label=APP_NAME)
        name_label.add_css_class("title-1")
        version_label = Gtk.Label(label="Version " + APP_VERSION)
        version_label.add_css_class("dim-label")
        description_label = Gtk.Label(label=APP_DESCRIPTION, wrap=True)
        description_label.set_max_width_chars(52)
        description_label.set_justify(Gtk.Justification.CENTER)
        license_label = Gtk.Label(label="Released under the GNU GPL v3.0.")
        license_label.add_css_class("dim-label")
        stack_note = Gtk.Label(
            label="Protocol, ECU database, serial adapter and graphing modules "
                  "integrated from the OpenGonsult core libraries."
        )
        stack_note.add_css_class("dim-label")
        stack_note.set_wrap(True)
        stack_note.set_max_width_chars(52)
        stack_note.set_justify(Gtk.Justification.CENTER)

        page.append(name_label)
        page.append(version_label)
        page.append(description_label)
        page.append(license_label)
        page.append(stack_note)

        self.stack.add_named(page, "about")

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    def on_connect_clicked(self, _button):
        if SerialAdapter is None or self.processor is None:
            self.show_error(
                "Serial support unavailable",
                "The pyserial backend could not be imported.",
            )
            return
        port = self.config.get("serial_port") or "/dev/ttyUSB0"
        baud = int(self.config.get("baud_rate", BAUD_RATES[0]))
        self.connect_button.set_sensitive(False)
        self.set_status(
            "Connecting to {0} at {1} baud...".format(port, baud),
            "dialog-question-symbolic",
        )
        self.worker = ConnectionWorker(port, baud)
        self.worker.start()
        future = self.worker.submit("connect")
        future.add_done_callback(
            lambda fut: GLib.idle_add(self.on_connect_result, fut)
        )

    def on_connect_result(self, future):
        port = str(self.config.get("serial_port"))
        try:
            future.result()
        except Exception as exc:
            self.reset_connection_state()
            self.show_error("Connection failed", str(exc))
            self.set_status("Connection failed.", "dialog-error-symbolic")
            return False
        self.connected = True
        self.disconnect_button.set_sensitive(True)
        self.set_status(
            "Connected to {0}.".format(port), "network-transmit-symbolic"
        )
        self.start_poll_timer()
        return False

    def on_disconnect_clicked(self, _button):
        self.stop_poll_timer()
        if self.worker is not None:
            future = self.worker.submit("disconnect")
            future.add_done_callback(
                lambda fut: GLib.idle_add(self.on_disconnect_result, fut)
            )
        else:
            self.reset_connection_state()

    def on_disconnect_result(self, _future):
        self.shutdown_worker()
        self.reset_connection_state()
        self.set_status("Disconnected.", "dialog-information-symbolic")
        return False

    def reset_connection_state(self):
        self.connected = False
        self.connect_button.set_sensitive(True)
        self.disconnect_button.set_sensitive(False)
        self.stop_poll_timer()

    def shutdown_worker(self):
        worker = self.worker
        self.worker = None
        if worker is None:
            return
        worker.request_stop()
        worker.join(timeout=1.5)

    def start_poll_timer(self):
        if not hasattr(self, "_poll_timer_id"):
            self._poll_timer_id = GLib.timeout_add(POLL_INTERVAL_MS, self.poll_tick)

    def stop_poll_timer(self):
        timer_id = getattr(self, "_poll_timer_id", None)
        if timer_id is not None:
            GLib.source_remove(timer_id)
            self._poll_timer_id = None

    def poll_tick(self):
        if not self.connected or self.simulating or self.worker is None:
            return True
        future = self.worker.submit("poll")
        future.add_done_callback(
            lambda fut: GLib.idle_add(self.on_poll_result, fut)
        )
        return True

    def on_poll_result(self, future):
        try:
            readings = future.result()
        except Exception as exc:
            self.stop_poll_timer()
            self.shutdown_worker()
            self.reset_connection_state()
            self.show_error("Communication lost", str(exc))
            self.set_status("Disconnected after communication error.", "dialog-error-symbolic")
            return False
        if self.processor is None:
            return False
        for key, value in readings:
            sensor_type = None
            if SensorType is not None:
                try:
                    sensor_type = SensorType[key.upper()]
                except KeyError:
                    sensor_type = None
            if SensorReading is not None:
                reading = SensorReading(
                    sensor_type=sensor_type,
                    value=float(value),
                    unit=SENSOR_UNITS.get(key, ""),
                    raw_value=int(round(value)),
                )
                self.processor.add_reading(key, reading)
        return False

    # ------------------------------------------------------------------
    # Simulation feed
    # ------------------------------------------------------------------

    def on_sim_toggled(self, _switch, state):
        self.simulating = bool(state)
        self.config["simulation"] = self.simulating
        self.persist_settings()
        if self.simulating:
            self.start_simulation()
            self.set_status(
                "Simulation running: synthetic sensor stream active.",
                "media-playback-start-symbolic",
            )
        else:
            self.stop_simulation()
            self.set_status(
                "Simulation stopped.", "dialog-information-symbolic"
            )
        return False

    def start_simulation(self):
        self.sim_start_time = time.time()
        self.simulator = SimulationEngine(self.processor)
        self.simulator.start()
        if not hasattr(self, "_sim_timer_id"):
            self._sim_timer_id = GLib.timeout_add(SIM_INTERVAL_MS, self.simulation_tick)

    def stop_simulation(self):
        timer_id = getattr(self, "_sim_timer_id", None)
        if timer_id is not None:
            GLib.source_remove(timer_id)
            self._sim_timer_id = None
        if hasattr(self, "simulator"):
            self.simulator.stop()
            del self.simulator
        self.sim_start_time = None

    def simulation_tick(self):
        if not self.simulating or self.processor is None:
            return True
        if hasattr(self, "simulator") and self.simulator:
            self.simulator.tick()
        return True

    # ------------------------------------------------------------------
    # Status area and dialogs
    # ------------------------------------------------------------------

    def set_status(self, text, icon_name="dialog-information-symbolic"):
        self.status_label.set_text(text)
        self.status_image.set_from_icon_name(icon_name)

    def show_info(self, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(text)
        dialog.connect("response", self.on_dialog_response)
        dialog.present()

    def show_error(self, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(text)
        dialog.connect("response", self.on_dialog_response)
        dialog.present()

    def confirm(self, title, text, on_confirm):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dialog.format_secondary_text(text)
        dialog.connect(
            "response",
            lambda dlg, response: self.on_confirm_response(dlg, response, on_confirm),
        )
        dialog.present()

    def on_dialog_response(self, dialog, _response):
        dialog.destroy()

    def on_confirm_response(self, dialog, response, on_confirm):
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            on_confirm()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def do_close_request(self):
        for timer_id in self.timer_ids:
            GLib.source_remove(timer_id)
        self.timer_ids = []
        self.stop_poll_timer()
        self.stop_simulation()
        if self.worker is not None:
            self.worker.request_stop()
            self.worker = None
        return False


class OpenGonsultApp(Gtk.Application):
    """GTK application wrapper for OpenGonsult."""

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        # Drawer entry is org.opengonsult.OpenGonsult.desktop (matches APP_ID);
        # this is the X11 fallback so windows carry the goblin icon too.
        Gtk.Window.set_default_icon_name("opengonsult")

    def do_activate(self):
        window = MainWindow(self)
        window.present()


def main(argv=None):
    app = OpenGonsultApp()
    return app.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
