# Changelog

All notable changes to OpenGonsult are documented in this file. The chaos is
tracked, versioned, and mostly intentional. 🧝✨📊

The format is based on [Keep a Changelog](https://keepachangelog.com/), and
this project adheres to a vaguely optimistic form of
[Semantic Versioning](https://semver.org/).

## [0.95] - 2026-10-29

### Added 🔥

- **v0.95 feature set (from Conzult reverse engineering)**:
  - Expanded sensor set: intake air temp, MAF, ignition timing, IACV-AAC/V,
    A/F alpha, injector pulse/duty, left/right O2 sensors
  - **Active tests** module (`ecu/active_tests.py`): power balance, solenoid
    and relay control, base idle adjustment, throttle position adjustment,
    fuel pressure release, self-learn clear, ECCS reset, ROM reads
  - **Monitoring set** (`ecu/monitoring.py`): selectable, reorderable,
    persistable dashboard/graph sensor sets
  - **Logfile analyzer** (`sessionrec/analyzer.py`): per-sensor min/max/mean
    and sample counts
  - Active Tests page in the GTK4 UI
- **Diagnostic Trouble Codes (DTC)** — real CONSULT-I read (`0xd1`) and clear
  (`0xc1`) on the Diagnostics page, with a new `ecu/dtc.py` decoder:
  - fault pairs `(code, engine_starts)`, `0x55` "no fault" sentinel handling,
    and optional `0xff` + length frame-prefix stripping
  - built-in DTC index translating numeric codes to plain-English descriptions
- **Session recording & replay** — new `sessionrec` package:
  - `SessionLogger` captures every reading (live or simulated) via processor
    observers while recording
  - samples export to **CSV, SQLite or JSON** (`sessionrec.formats`)
  - `SessionReplayer` plays sessions back with play/pause/seek/stop
- **Live graphing page** — `graphs/sensor_graph.py`:
  - per-sensor toggles, mouse-wheel zoom, drag-to-pan
  - **CSV export** of plotted series
  - integrated record/session/replay controls on the page
- **Software simulation expander** — `dashboard/simulator` synthesizes live
  readings so the whole app (gauges, graphs, recording) works without a car
- **Packaging** — `pyproject.toml` (PEP 621) with a single-source version
  (`gui.__init__.__version__`), `opengonsult` console entry point, and
  Debian/RPM packaging trees (`debian-build/`, `packaging/rpm/`)
- **CI & linting** — GitHub Actions workflow (lint with ruff, test under
  Xvfb with GTK4 deps, package build) plus a ruff bug-risk config
  (`E4/E7/E9/F`)

### Changed ⚡

- Protocol layer hardened in `protocol/consult.py`: timestamped framing,
  signature replay protection, strict TIMING → SIGNATURE → CONTENT validation,
  exponential-backoff retry with jitter
- Serial I/O serialized through a race-free async command queue
  (`serial/adapter.py`) with auto-reconnect
- Dashboard gauges now driven by `ecu/sensors.py`
  (`DashboardDataProcessor`), which also feeds the graphing history
- Module renames (old names retired): `ecu/sensor_reader.py` →
  `ecu/sensors.py`, `ecu/database.py` → `ecu/ecu_db.py`,
  `protocol/consult_parser.py` → `protocol/consult.py`
- README rewritten to match reality (and keep the goblin energy)

### Fixed 🐛

- Corrected DTC command constants to the real CONSULT-I values
  (read `0xd1` / clear `0xc1`)
- Fixed a latent `NameError` in packet validation logging
- License harmonized to **GPL-3.0-or-later** everywhere (pyproject, Debian
  copyright, RPM spec, About page, `LICENSE`)

---

## [0.69] - 2024-07-25 🧝✨📊

### Added 🔥

**Real-time Sensor Gauges Dashboard**
- Live RPM, coolant temperature, and battery voltage monitoring with GTK4
  gauges (progress bars, later circular gauges) on the Dashboard page
- Auto-refresh mechanism and graceful degradation when sensor data is missing
- System-wide `opengonsult` command and GNOME desktop integration

**CONSULT-I Protocol (early days)**
- First live sensor decoding: RPM, temps, throttle position, battery voltage
- Calibration values fetched from the ECU database with safe defaults
- Improved battery-voltage scaling based on real-world range observations

**Version bump**: 0.67 → 0.69.

### Changed ⚡

- Auto-refresh interval configurable; logging improvements
- Value validation / bounds checking before gauge updates

### Fixed 🐛

- Corrected battery voltage scaling factor in the parser (`/10.0` →
  proper normalization)
- RPM value validation bounded to plausible ranges

---

*(Yes, a lot happened between 0.69 and 0.88. Milestones get cracked, hardware
gets wired, and the goblins refactor modules when nobody's looking.)*