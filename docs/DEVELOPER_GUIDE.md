# OpenGonsult Developer Guide

How OpenGonsult is put together, how data flows through it, and how to extend
it without setting your laptop on fire.

---

## 1. Architecture overview

```
serial port / Bluetooth          GTK4 UI (gui/main_window.py)
        │                                     ▲
        ▼                                     │
 SerialAdapter (serial/adapter.py)            ├─ Dashboard  ─ dashboard/ gauges + ecu.sensors
        │                                     ├─ Graphing   ─ graphs/sensor_graph.py
        ▼                                     ├─ Diagnostics─ ecu.dtc + ecu.ecu_db
 RequestPacket/ResponsePacket                 ├─ Settings   ─ config.json
 (protocol/consult.py)                        └─ About
        │
        ▼
 DashboardDataProcessor (ecu/sensors.py)
     └─ observers (sessionrec.SessionLogger) → CSV/SQLite/JSON
```

Two independent halves meet at `DashboardDataProcessor`:

- **Acquisition**: serial adapter → CONSULT-I packets → decoded values →
  `processor.add_reading(...)`.
- **Presentation**: the processor's history + observer hooks feed the GTK4
  dashboard gauges and the graphing page.

Both halved work in **simulation mode** too — the simulator synthesizes
readings and pushes them through the *same* processor, so every downstream
feature (graphs, recording, replay) is identical with or without a car.

## 2. Module map

| Package / module           | Responsibility |
|----------------------------|----------------|
| `gui/main_window.py`       | GTK4 app shell, 5 pages, config, connect/simulate controls |
| `protocol/consult.py`      | CONSULT-I framing, packets, checksum, timestamp/signature validation, retry |
| `serial/adapter.py`        | async pyserial adapter, race-free command queue, auto-reconnect |
| `ecu/sensors.py`           | `DashboardDataProcessor`: smoothing, time-series history, observers |
| `ecu/dtc.py`               | DTC decoder + fault index for the Diagnostics page |
| `ecu/ecu_db.py`            | ECU/sensor/DTC definitions database |
| `graphs/sensor_graph.py`   | GTK4 graph widget: toggles, zoom/pan, CSV export, record/replay UI |
| `sessionrec/`              | sample formats (CSV/SQLite/JSON), `SessionLogger`, `SessionReplayer` |
| `dashboard/`               | gauge widgets + software sensor simulator |
| `bin/opengonsult`          | launcher that puts the repo root on `sys.path` |

## 3. Data flow in detail

1. **Connect** – `MainWindow` creates a `SerialAdapter` with the configured
   port/baud.
2. **Live poll** – a periodic task asks for each enabled sensor by building a
   `RequestPacket(mode=CONSULT_MODE_LIVE_DATA)` and running
   `adapter.transaction(frame)`. The response is decoded via
   `ResponsePacket.decode()` and mapped to physical units with
   `ecu_db.SensorDefinition`.
3. **Ingest** – each value lands in `processor.add_reading(key, reading)`.
   - the rolling gauge window is updated,
   - the time-series history is appended and trimmed,
   - every observer (`fn(key, epoch, value)`) is invoked — the session
     logger uses this to capture samples.
4. **Render** – GTK timeouts read `processor.get_history()` (graphing) and
   `get_current_value()` (gauges) and redraw.

## 4. Configuration

App config lives at `~/.config/opengonsult/config.json` (see
`load_config()` in `gui/main_window.py`):

```json
{
  "dark_mode": true,
  "serial_port": "/dev/ttyUSB0",
  "baud_rate": 9600,
  "simulation": false
}
```

## 5. Extending

### Add a new live sensor

1. Add a read command to `SENSOR_COMMANDS` in `gui/main_window.py`
   (sub-function byte per the CONSULT-I spec).
2. Add a `SensorDefinition` for the relevant ECU in `ecu/ecu_db.py`
   (`scaling_factor`/`offset` map raw → physical).
3. Optionally add a `SensorType` and `SensorReading` unit to `ecu/sensors.py`
   and a `GaugeDef` row in `GAUGE_DEFS` to give it a gauge.
4. The graph picks sensors up from the labels/units maps
   (`SENSOR_LABELS`/`SENSOR_UNITS` in `graphs/sensor_graph.py`).

### Add a DTC definition

Add an entry to `DTC_INDEX` in `ecu/dtc.py` (numeric code → description).
Codes not present fall back to a generic label automatically. For richer
metadata (severity, causes, actions), add a `DTCDefinition` on the relevant
ECU in `ecu/ecu_db.py`.

### Reuse the core library headlessly

The `ecu`, `protocol`, `serial`, `sessionrec` parts have **no GTK
dependency** — they can be used from scripts, tests and other tools. See
`examples/`.

## 6. Testing & quality

| Tool/command | Purpose |
|--------------|---------|
| `python3 -m unittest discover -s tests -v` | the full suite (39 tests) |
| `ruff check .` | lint (bug-risk rules `E4,E7,E9,F`) |
| GitHub Actions (`.github/workflows/ci.yml`) | lint + test (apt GTK4 deps, `xvfb-run`) + package build |

Conventions:

- Keep **plotting math and decoding pure** where possible (e.g. `plot_xy`,
  `decode_faults`) so it can be unit-tested without GTK.
- GTK tests mock `gi` so they run headless (see `tests/test_*.py`).
- Line length 100, `py38` target, Python imports standard + dataclasses/typing.

### Running against real hardware

Requires a CONSULT-I → serial (USB/Bluetooth) adapter and ignition on.
There is no unit test for the live wire; validate with `bin/opengonsult` and
check the Diagnostics page reads/clears codes.

## 7. Packaging pointers

- `pyproject.toml` (setuptools, PEP 621) is the single source of truth for
  version (`gui/__init__.py` → `__version__`) and the `opengonsult` entry
  point.
- `debian-build/` is the Debian packaging staging tree; keep its
  `usr/share/opengonsult/` copy of the Python sources in sync with the live
  tree (see M1 Stage C for the sync procedure).
- `packaging/rpm/` holds the RPM spec; `packaging/rpm/opengonsult.1` is the
  shared manpage source (re-`gzip` into the debian tree when it changes).
- **GNOME integration**: the app drawer entry must match the GTK application
  id — the desktop file is `org.opengonsult.OpenGonsult.desktop` (equals
  `APP_ID`), so GNOME/Wayland attribute the window + drawer icon to
  OpenGonsult. The hicolor theme canonically lives in `packaging/hicolor/`
  (`index.theme` is mandatory for `gtk-update-icon-cache` to build the icon
  cache); keep `debian-build/usr/share/icons/hicolor/` in sync. GTK4 dropped
  per-window icon setters; the static
  `Gtk.Window.set_default_icon_name("opengonsult")` is the X11 fallback (the
  Wayland path is the app-id-matched desktop file).
- The `.deb`/`.rpm` artifacts are built in **Milestone 12**.

## 8. Common pitfalls

- `python3 gui/main_window.py` fails with `ModuleNotFoundError: No module
  named 'dashboard'` unless the repo root is on `PYTHONPATH` — always launch
  via `bin/opengonsult` or the installed entry point.
- `sessionrec` is named that way on purpose — a package called `logging`
  would shadow the stdlib and chaos would ensue.
- The `dashboard/simulator` module is intentionally flat (no package
  `__init__.py`); don't "helpfully" turn it into a package.