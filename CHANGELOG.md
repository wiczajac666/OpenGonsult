# Changelog

All notable changes to OpenConsult will be documented in this file.

## [0.69] - 2024-07-25 🧝✨📊

### Added 🔥

**Real-time Sensor Gauges Dashboard Module**
- New module: `ecu/sensor_reader.py` with `DashboardDataProcessor` class for live gauge updates
- Real-time RPM, temperature, and battery voltage monitoring on dashboard UI
- Live progress bar displays in the main GUI window showing current sensor readings
- Battery voltage tracking integrated into ECU database (`database.voltage` sensor definition)

**GUI Enhancements (gui/main_window.py)**
- Integrated live sensor visualization with GTK4 widgets
- Progress bars for RPM, temperature, and battery voltage metrics
- Auto-refresh mechanism using `DashboardDataProcessor.update()` calls at regular intervals
- Improved error handling in dashboard data updates (`_update_dashboard_data()`)

**ECU Database Updates (ecu/database.py)**
- Added new sensor definitions: 
  - `'voltage': {'unit': 'V', 'min_value': float('nan'), 'max_value': float('nan')}` for battery voltage monitoring
  - Sensor readings stored with timestamps for historical analysis
- Enhanced `add_sensor_reading()` method to support live data from connected vehicles

**CONSULT-I Protocol Integration (ecu/consult_parser.py)**
- Implemented CONSULT-I protocol parsing engine (`ConsultIParser` class)
- Real-time decoding of sensor values: RPM, coolant temp, intake air temp, throttle position, battery voltage
- Data normalization methods for temperature conversions and voltage scaling from raw CAN bus data
- Automatic calibration value fetching from database with default fallbacks

**System-Wide Command & Packaging (v0.69+)**
- Systemwide `opengonsult` command available after installation
- Desktop shortcut at `/usr/share/applications/opengonsult.desktop` for GNOME desktop environments  
  - Name: OpenGonsult v0.69 🧝✨ 
  - Icon: Custom goblin mascot included in package resources

### Changed ⚡

- Dashboard auto-refresh interval optimized to every 3 seconds (configurable via `auto_refresh_interval_ms`)
- Improved error handling with graceful degradation when sensor data unavailable
- Enhanced logging integration for better debugging of vehicle communication issues

### Fixed 🐛

- **Critical fix**: Corrected battery voltage scaling factor in CONSULT-I parser from `/10.0` to correct normalization calculation
- Fixed RPM value validation: now properly bounds within expected ranges (597, 3268) with proper handling
- Better null/NaN value checking before sensor data visualization updates

### Technical Details 📚

**Sensor Reader Module Architecture:**
```python
ecu/sensor_reader.py
├── DashboardDataProcessor class
│   ├── __init__(db_path: str, rpm_min=0.0, rpm_max=8000.0)
│   ├── update(sensor_data: dict): Real-time sensor ingestion  
│   └── get_sensor_values(): Returns current RPM/temp/voltage values for UI rendering
```

**CONSULT-I Protocol Decoding:**
- Raw CAN bus → normalized engineering units conversion
- Temperature: Celsius conversions with proper range validation (0°C to 154°C)
- Voltage scaling from raw bytes using calibration factors retrieved from database
- Throttle position tracking at 8% increments for driver behavior analysis

**GUI Integration Points:**
```python
gui/main_window.py:MainWindow.__init__()
└── self.dashboard_processor = DashboardDataProcessor(...)  
    ├── rpm_label, temp_label, voltage_label labels updated every refresh interval
    └── Progress bars (rpm_progress_bar, etc.) animate in real-time during vehicle connection


### Version Bump ✅

- Package version officially bumped from 0.67 to **0.69** 🧝✨📊  
- Release artifacts available as `OpenGonsult_0.69-1jammy_amd64.deb` (to be built in future releases)
- Documentation updated: README.md includes v0.69+ feature list and installation instructions

---
[Unreleased] - Changes under development for the next version bump