# OpenGonsult v0.69+ 🧝✨📊⚡

> This is a **wibecoding test** for AI, it will most definetly not work (but somehow does?!) 😂💀

## Why the funny name?
Because "OpenConsult" was too serious and we needed some chaotic vibes 🧝🔥
*Also because goblin energy is superior to corporate software naming.* 👾✨

---

## 🔥 What's New in v0.69+ 📊💪

**REAL-TIME SENSOR MONITORING**! Yes, your car dashboard now has:
- ⚙️ **Live RPM gauge** - watch those numbers dance!
- 🌡️ **Temperature monitoring** (coolant & intake air temp)  
- 🔋 **Battery voltage tracking** with automatic calibration
- 🎨 Beautiful GTK4 progress bars that actually update in real-time!  

The magic happens via our new `ecu/sensor_reader.py` module and CONSULT-I protocol parser. Your car talks, your dashboard listens, chaos ensues (in a scientifically verified way). ⚡🧝

---

## What's in here? 📦
A bizzare collection of components trying to solve car diagnostics:
- `protocol/` - CONSULT-I protocol parser (talking to real cars now!)
- `ecu/sensor_reader.py` - Dashboard data processor with live sensor updates  
- `gui/main_window.py` - GTK4 interface with animated gauges
- `serial/`, `dashboard/`, `themes/` - The usual suspects 🕵️‍♂️
- **System-wide command**: Run `opengonsult` from anywhere! 💻🔨
- **GNOME desktop integration**: Auto-starts with your custom goblin icon!

---

## Installation 🔧
```bash  
debsum -i OpenGonsust_0.69+1ammy_amd64.deb # TODO: build it properly (we're still figuring this part out)
pip3 install . or run ./scripts/install.sh if you feel lucky 🎲
opengnsult --version  # should say v0.69+
```

## Features Showcase ⚡📊
- Real-time RPM: **Live updates every 3 seconds** (configurable)
- Temperature tracking: Celsius with automatic range validation ✅
- Battery voltage monitoring: From raw CAN bus to real numbers 🧮✨
- Dashboard auto-refresh: Your data, always fresh and chaotic
- Error handling: Graceful degradation because sometimes the car lies 💀

---

## Under The Hood (For Nerds) 🔬🤓
```
opengonsult/
├── ecu/sensor_reader.py    # DashboardDataProcessor 🧝⚡  
│   ├── update(sensor_data)
│   └── get_sensor_values() -> {rpm, temp, voltage}
├── gui/main_window.py       # GTK4 dashboard with animated gauges ✨
│   ├── rpm_progress_bar
│   ├── temp_progress_bar (°C) 
│   └── voltage_progress_bar (V)
├── protocol/consult_parser.py  # CONSULT-I decoder 🔧📊
│   ├── raw CAN → engineering units 🔄
│   ├── automatic calibration value fetching ⚙️
│   └── temperature/voltage normalization formulas ✅
```
**Version**: `OpenConsult v0.69+` (changelog in CHANGELOG.md)
---

*Created by wiczajac666 for the chaos 🧝✨📊 - now with real sensor gauges!*

_P.S. The chaotic vibes haven't stopped, we just added scientific monitoring._ 🔥⚡ 