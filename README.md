# OpenGonsult 🧝✨📊⚡

> An open-source diagnostic suite for Nissan vehicles equipped with the
> **CONSULT-I (14-pin)** diagnostic interface. Native GTK4, zero corporate
> software energy, maximum goblin energy. 🧝🔥
>
> It reads live engine sensors, graphs them, records sessions for replay, and
> wrangles diagnostic trouble codes. Somehow it works. Probably.

## 🔥 What's New in v0.99 📊💪

- ⚙️ **Real-time gauges** — RPM, coolant temp, battery voltage, vehicle speed,
  throttle position, O2 sensor (left/right), plus intake air, MAF, ignition
  timing, IACV, A/F alpha and injector pulse/duty. SPINNY. 🎡
- 📈 **Live graphing** — zoom, pan, per-sensor toggles, and **CSV export** of
  whatever chaos the car is spewing.
- 💾 **Session recording & replay** — capture a drive in **CSV, SQLite or JSON**
  and play it back on the graph. Your car's best moments, preserved forever.
- 📊 **Logfile analyzer** — per-sensor min/max/mean and sample counts for
  recorded sessions.
- 🔧 **Diagnostic Trouble Codes** — real CONSULT-I read (`0xd1`) and clear
  (`0xc1`), with plain-English translations from the built-in DTC index.
- 🧪 **Active tests** — power balance, solenoid/relay control, base idle
  adjustment, throttle position adjustment, fuel pressure release, self-learn
  clear, ECCS reset and ROM reads via CONSULT-I activation (`0x0A`).
- 🎛️ **Monitoring set** — pick, reorder and persist the sensors shown on the
  dashboard/graphing pages ("MONITORING (SET)").
- 🎨 **Dark mode** — because staring at a laptop in a dark garage is a
  lifestyle. Config persisted to `~/.config/opengonsult/config.json`.
- 🤖 **Simulation mode** — no car? No problem. The dashboard fakes it with
  software-synthesized sensor data so you can still fiddle forever.

## What's in here? 📦

A bizarre collection of cooperating modules:

- `protocol/consult.py` — CONSULT-I protocol implementation (framing,
  timestamp/signature validation, replay protection, exponential-backoff retry)
- `serial/adapter.py` — async pyserial layer (USB/Bluetooth) with a race-free
  command queue and auto-reconnect
- `ecu/` — sensor processing (`sensors.py`), the Nissan ECU database
  (`ecu_db.py`), the **DTC decoder** (`dtc.py`), active tests
  (`active_tests.py`) and the monitoring set (`monitoring.py`)
- `sessionrec/` — session sample formats + logger + replayer + logfile
  analyzer (`analyzer.py`) (CSV/SQLite/JSON)
- `graphs/sensor_graph.py` — GTK4 graphing widget with session record/replay
- `dashboard/` — gauge widgets and a software simulator for sensor data
- `gui/main_window.py` — the GTK4 app shell (Dashboard, Graphing, Diagnostics,
  Active Tests, Settings, About pages)

## Installation 🔧

**From source (pip):**

```bash
pip install .
opengonsult --version   # should say OpenGonsult 1.0
```

**From the `.deb` package** (grab the one in `releases/` after a build, or check
the GitHub releases page):

```bash
dpkg -i OpenGonsult_1.0-1jammy_all.deb
opengonsult --version
```

Installing from `.deb`/`.rpm` also drops the app into your **GNOME
application drawer** (with the goblin icon) via the
`org.opengonsult.OpenGonsult.desktop` entry.

**RPM folk:** the spec lives in `packaging/rpm/opengonsult.spec`, and
`scripts/build-rpm.sh` builds `opengonsult-<version>.noarch.rpm` locally:

```bash
./scripts/build-rpm.sh        # outputs to releases/
```

Both package formats are rebuilt by the **release workflow** whenever a `v*`
tag is pushed, and the artifacts are attached to the GitHub release. To build
the `.deb` locally:

```bash
./scripts/build-deb.sh        # outputs to releases/
```

## Usage 🚗

Just run it:

```bash
opengonsult
```

- Connect the 14-pin CONSULT-I adapter to a serial port (default
  `/dev/ttyUSB0`), pick a baud rate in **Settings**, hit Connect.
- No hardware? Flip on **simulation mode** in Settings and the dashboard
  comes alive with fictional-but-plausible data.
- Diagnostics page: **Read Codes** to fetch stored DTCs, **Clear Codes** to
  wipe them. Codes are translated via the DTC index where known.
- Graphing page: toggle sensors, record a session, export it, and replay it.

## Under The Hood (For Nerds) 🔬🤓

```
opengonsult/
├── bin/opengonsult          # system launcher (inserts repo root on PATH)
├── gui/
│   └── main_window.py       # GTK4 app shell + 5-page navigation
├── protocol/
│   └── consult.py           # CONSULT-I framing, packets, retry/security
├── serial/
│   └── adapter.py           # async pyserial adapter + command queue
├── ecu/
│   ├── sensors.py           # DashboardDataProcessor (gauges + history)
│   ├── ecu_db.py            # ECU/sensor/DTC database & definitions
│   └── dtc.py               # CONSULT-I DTC decoder + fault index
├── graphs/
│   └── sensor_graph.py      # GTK4 graphing + session record/replay UI
├── sessionrec/              # CSV / SQLite / JSON sample formats, logger, replayer
├── dashboard/               # gauge widgets + sensor simulator
├── themes/                  # (future) CSS themes
└── tests/                   # unittest suite (39 tests, all green)
```

## Development 🧪

```bash
# run the test suite (headless, no hardware or GTK display needed)
python3 -m unittest discover -s tests -v

# lint (bug-risk rules only)
ruff check .

# launch without installing
PYTHONPATH=$PYTHONPATH:$(pwd) python3 gui/main_window.py
```

CI (GitHub Actions) runs lint + tests (under Xvfb) + a build for every push to
`main`/`master`.

## License 📜

**GPL-3.0-or-later.** Free software, chaos included. See `LICENSE` and the
Debian copyright file in `debian-build/`.

---

*Created by wiczajac666 for the chaos 🧝✨📊 — v0.99 reverse-engineers the
Conzult active tests, monitoring sets and logfile analyzer. Fuel injector
séances, probably.*