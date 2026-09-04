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

Gnome Desktop icon

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
Gnome desktop icon OpenGonsult.png

Window list:
1. Dashboard 
- contains voltages, rpm, Etc meters, visual style gauges, and common numbers for gauges
2. Graphing
- shows graphs from multiple selectable sources
3. Diagnostics
- contains error code readings and translations for them, also error code reset button
4. settings 
- contains device selection (drop down and open field), theme selection 
5. About
- contains software information
---

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
11. Version 0.88 release

This structure is well suited to orchestration frameworks such as OpenAI Codex, Claude Code, Aider, Roo Code, or similar systems where multiple coding agents can work concurrently under the supervision of an orchestrator that tracks task ownership, dependencies, progress, and integration.

