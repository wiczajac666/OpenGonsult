# Project: OpenGonsult

**Goal**

Create a native Linux GTK4 diagnostic suite for Nissan CONSULT-I (14-pin connector) written entirely in Python.

---

# Orchestrator

The orchestrator is the only agent allowed to merge code into `main`.

Responsibilities:

* maintain project state
* assign tasks
* schedule work
* run automated tests
* generate releases
* monitor coverage
* maintain documentation
* ensure coding standard
* ensure that only one sub agent is running at a time.

Maintains a project database containing:

```text
Tasks
Dependencies
Progress
Completed Modules
Failed Tests
Known Bugs
Agent Status
Current Sprint
```

---

# Agent 1 — Protocol Team

Owns

```
protocol/
```

Tasks

* CONSULT-I packets
* checksum
* serial framing
* timing
* retries
* ECU discovery
* command encoder
* response decoder

Deliverables

```
consult.py
packets.py
serial.py
timing.py
```

---

# Agent 2 — ECU Database

Owns

```
ecu/
```

Tasks

* ECU definitions

* sensor tables

* lookup tables

* DTC database

* scaling

Produces

```
ecu_db.py
dtc.py
sensors.py
```

---

# Agent 3 — GUI

Owns

```
gui/
```

GTK4 only

full Wayland support

Gnome application drawer entry

Responsibilities

Dashboard

Graphs

Menus

Settings

Dialogs

Error code reader

Dark mode

---

# Agent 4 — Dashboard

Creates

```
gauges
digital displays
custom dashboards
widgets
themes
```

---

# Agent 5 — Graphing

Responsible for

```
live graphs from car sensors
zoom
history
recording
playback (play,stop)
CSV export
```

---

# Agent 6 — Serial Communication


```
USB
Bluetooth
FTDI
CH340
PL2303
device discovery
hotplug
```

---

# Agent 7 — Logging

Produces

```
CSV
SQLite
JSON
session recording
replay

```

---

# Agent 8 — Testing

Creates

```
unit tests
protocol tests
GUI tests
performance tests
integration tests
hardware simulation
```

---

# Agent 9 — Documentation

Maintains

```
README
API docs
User manual
Developer guide
Protocol specification
Examples
```

---


---

# Agent 10 — Packaging

Produces

```
Flatpak
.deb
RPM
```

---


---

#Agent 11 — CI/CD

Maintains:

GitHub Actions

Linting

Formatting

Coverage

Nightly builds

Release automation

---



# Repository Layout

```text
OpenGonsult/

    orchestrator/

    protocol/

    serial/

    ecu/

    gui/

    dashboard/

    graphs/

    logging/

    docs/

    tests/

    packaging/

    scripts/

    ci/

    resources/

    icons/

    themes/

    examples/
```

---

# Task Database

Example JSON

```json
{
  "task": "Implement ECU packet parser",
  "owner": "ProtocolAgent",
  "priority": "High",
  "status": "Working",
  "depends_on": [
    "Serial Layer"
  ],
  "progress": 65,
  "tests": 14,
  "coverage": 93.1
}
```

---

# Communication Bus

Agents communicate only through the orchestrator.

```
Agent

↓

Task Queue

↓

Orchestrator

↓

Reviewer

↓

Merge Queue

↓

Main Branch
```

No direct agent-to-agent writes are allowed.

#launchcommand

launch command on linux terminal should be opengonsult

#GUI reference:

GTK4 window title: OpenGonsult <version>
GUI navigation panel left side ( like gnome settings window )
Gnome application drawer entry icon OpenGonsult.png
initial app window size 1280x720px, resizeable
Window list:
1. Dashboard 
- contains voltages, rpm, Etc meters, visual style gauges, and common numbers for gauges.
- the gauges shuold have dynamic placing. when resizing the window it rearranges them where they fit.
also selections for graphing sources should be in a separate window with the button named :"sources"

2. Graphing
- graphing sources should be in a separate window with the button named :"sources"
- shows graphs from multiple selectable sources
- the graphing should show source name and the line in different color for every source like it is in "https://github.com/GNOME/gnome-system-monitor"  resources tab.

3. Diagnostics
- contains error code readings and translations for them, also error code reset button

4. Active Tests
- power balance, solenoid/relay control, base idle adjustment, throttle position
  adjustment, fuel pressure release, self-learn clear, ECCS reset, ROM reads

5. Monitoring Set
- selectable, reorderable, persistable sensor sets for dashboard/graphing

6. settings 
- contains device selection (drop down and open field), theme selection,
  monitoring set configuration

7. About
- contains software information

8. Logfile Analyzer
- per-sensor min/max/mean and sample counts for recorded sessions
9. Responsive Dashboard
- gauges flow and rearrange automatically on window resize
10. Graph Sources Dialog
- separate "Sources" window for selecting graphed sensors
11. GNOME-style Graph Legend
- colored line + source name for each plotted series

Additional current modules/features:
- ecu/active_tests.py — CONSULT-I activation commands (0x0A)
- ecu/monitoring.py — monitoring set persistence
- sessionrec/analyzer.py — logfile analysis
- Wayland-native GTK4 operation with null-safe display/theme handling
- Ubuntu/Debian packaging (0.99-1jammy) and GitHub releases

# Milestones

1. Repository and CI setup
2. Serial communication
3. CONSULT-I protocol implementation
4. ECU discovery
5. Live sensor streaming
6. Basic GTK dashboard
7. Graphing and logging
8. DTC read/clear (nissan trouble codes)
9. Session recording and replay
10. Documentation and packaging
11. Version 1.0 release

This structure is well suited to orchestration frameworks such as OpenAI Codex, Claude Code, Aider, Roo Code, or similar systems where multiple coding agents can work concurrently under the supervision of an orchestrator that tracks task ownership, dependencies, progress, and integration.

