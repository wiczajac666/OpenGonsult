# OpenGonsult User Manual

OpenGonsult is a GTK4 diagnostic suite for Nissan vehicles with the
**CONSULT-I (14-pin)** interface. This manual walks through the five pages of
the app and shows you how to get readings from your car — or from no car at
all.

---

## 1. Getting started

Launch the app:

```bash
opengonsult
```

You should see a window with a left sidebar listing five pages:

1. **Dashboard** — live gauges
2. **Graphing** — time-series graphs, session record/replay
3. **Diagnostics** — diagnostic trouble codes
4. **Settings** — serial port, baud rate, simulation, dark mode
5. **About** — version and legal bits

## 2. Connecting to a car

1. Plug the CONSULT-I (14-pin) interface into the car and connect its
   serial end (USB adapter such as FTDI/CH340/PL2303, or Bluetooth) to your PC.
2. Open **Settings**.
3. Set **Serial device** (default `/dev/ttyUSB0`) and a **Baud rate**
   (default 9600; options go up to 230400).
4. Click **Connect** in the toolbar.

The status bar should confirm the connection. The Dashboard then polls the
ECU and the gauges start to spin. 🎡

> **Which baud rate?** CONSULT-I adapters commonly work at 9600. If the
> Dashboard shows `None`/no data, try other rates in Settings and reconnect.

## 3. No car? Simulation mode

If you don't have hardware, flip **Simulation** on in Settings. The app
synthesizes realistic-looking RPM / temperature / voltage readings and the
Dashboard, Graphing and recording all work exactly as they would with a live
ECU. Great for demoing or testing configs.

## 4. Dashboard page

Six gauges are available: **Engine RPM**, **Coolant Temp**, **Battery
Voltage**, **Vehicle Speed**, **Throttle Position** and **O2 Sensor**. Each
shows the current value, refreshed every ~500 ms, with per-sensor bounds.

If the car reports no value for a sensor (or the sensor isn't fitted), the
gauge stays idle rather than showing garbage.

## 5. Diagnostics page (DTCs)

- **Read Codes** sends the CONSULT-I DTC read command (`0xd1`) to the ECU and
  lists stored codes.
  - Each row shows the **2-hex-digit code** and, where known, a plain-English
    description from the built-in DTC index.
  - A summary line reports the total count (or "ECU reported no codes").
  - Full frames sent by the ECU (e.g. `13 00 08 03`) are decoded into
    code/starts pairs; `0x55` padding is ignored.
- **Clear Codes** sends `0xc1` to wipe stored faults. Use with care — it's a
  real write to the ECU.

> Known codes display descriptions; codes not in the local index fall back to
> the raw code string.

## 6. Graphing page

The graphing page plots live sensor history (rolling 5-minute window by
default) as separate colored lines.

- **Sensor toggles** — tick/untick which sensors to plot.
- **Zoom / pan** — use the mouse wheel to zoom the time axis; drag to pan.
- **Export CSV** — save the current plotted series to a CSV file. Each column
  is `timestamp, sensor, value` rows grouped by sensor.

### Recording a session

1. Click **Record** — every incoming reading is buffered.
2. Click **Stop** — you're prompted to save as **CSV**, **SQLite** or
   **JSON**.
3. Files are plain `timestamp, sensor, value` sample streams (SQLite stores
   them in a `samples` table).

### Replaying a session

1. Click **Open Session** and pick a saved file.
2. Hit **Play** — the recorded samples are pumped back into the processor and
   re-drawn on the graph at their original timestamps.
3. Use **Pause**, **Seek** and **Stop** to control playback.

This is the same mechanism used by the `sessionrec` library, so sessions can
be produced/consumed programmatically (see `examples/`).

## 7. Settings page

| Setting        | Meaning                                                   |
|----------------|-----------------------------------------------------------|
| Serial device  | serial port path (e.g. `/dev/ttyUSB0`)                    |
| Baud rate      | one of 9600–230400                                        |
| Simulation     | use software-synthesized data instead of the serial link  |
| Dark mode      | toggle the dark theme                                     |

Settings are saved to `~/.config/opengonsult/config.json`:

```json
{
  "dark_mode": true,
  "serial_port": "/dev/ttyUSB0",
  "baud_rate": 9600,
  "simulation": false
}
```

You can edit this file directly with the app closed.

## 8. About page

Shows the app name, version, a description and the license (**GPL-3.0-or-later**).

---

## Troubleshooting

| Symptom                        | Likely cause / fix                                   |
|--------------------------------|------------------------------------------------------|
| Gauges show no data            | Wrong port or baud rate; try Simulation to check UI  |
| "No module named 'dashboard'"  | You ran `python3 gui/main_window.py` without setting up the Python path — use `bin/opengonsult` or install the package |
| DTC read times out             | Adapter not seated, ignition off, or wrong baud rate |
| Graph is blank                 | No sensors toggled on, or no history yet             |