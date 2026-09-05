"""
OpenGonsult - Real-time Sensor Reader for RPM, Temperature & Battery Voltage
Enhanced module to support dashboard gauge displays in version 0.69+

This module provides real-time sensor data reading and processing functionality
integrating with ECU communication protocols to decode engine performance metrics.
"""

import time
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SensorType(Enum):
    """Types of sensors supported by OpenGonsult (v0.69+)"""
    ENGINE_RPM = "engine_rpm"  # Engine revolutions per minute (0-8000 RPM)
    VEHICLE_SPEED = "vehicle_speed"  # Vehicle speed in km/h
    THROTTLE_POSITION = "throttle_position"  # Throttle position % 
    COOLANT_TEMP = "coolant_temp"  # Coolant temperature °C (-40 to +150°C)
    INTAKE_AIR_TEMP = "intake_air_temp"  # Intake air temp °C
    MAF_SENSOR = "maf_sensor"  # Mass airflow g/s
    OXYGEN_SENSOR = "oxygen_sensor"  # O2 sensor voltage V (0.1-3V typical)
    BATTERY_VOLTAGE = "battery_voltage"  # Battery/system voltage V


@dataclass
class SensorReading:
    """Real-time sensor reading with timestamp"""
    sensor_type: SensorType
    value: float
    unit: str
    raw_value: int
    quality: str = "good"
    timestamp: datetime = field(default_factory=datetime.now)


class DashboardDataProcessor:
    """Processes and aggregates sensor data for dashboard display
    
    Real-time updates of RPM, engine temperature, battery voltage with smoothing.
    Supports gauge widgets binding via callbacks to UI components.
    
    v0.69+ additions: Core gauges - ENGINE_RPM (RPM), COOLANT_TEMP (temp °C), 
                       BATTERY_VOLTAGE (V) for automotive diagnostics dashboards.
    """
    
    def __init__(self, graph_history_seconds: int = 120):
        self._readings: Dict[str, List[SensorReading]] = {}  # Rolling window per sensor
        self._window_size = 10
        self._display_callbacks: List[Callable[[Dict[str, float]], None]] = []
        # Rolling TIME-SERIES history per sensor for live line-graph rendering (v0.70)
        self._history: Dict[str, List[tuple]] = {}  # key -> [(epoch_seconds, value), ...]
        self._history_seconds = graph_history_seconds
        # Observers receive (key, epoch_seconds, value) per reading (v0.88 logging)
        self._observers: List[Callable[[str, float, float], None]] = []

        self.sensor_names = {
            "engine_rpm": {"name": "Engine RPM", "unit": "RPM"},
            "coolant_temp": {"name": "Coolant Temp", "unit": "°C"}, 
            "battery_voltage": {"name": "Battery Voltage", "unit": "V"},
        }

    def subscribe(self, callback: Callable[[str, float, float], None]) -> None:
        """Register a callback invoked for every reading: fn(key, epoch_seconds, value).

        Used by the session logger to capture raw samples regardless of source
        (simulation or live ECU). Callbacks are best-effort; exceptions do not
        propagate to the caller.
        """
        if callback not in self._observers:
            self._observers.append(callback)

    def unsubscribe(self, callback: Callable[[str, float, float], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def add_reading(self, sensor_type: str | SensorType, reading: SensorReading):
        """Add a new sensor reading to the processor"""
        
        if isinstance(sensor_type, SensorType):
            key = sensor_type.value
        else:
            key = str(sensor_type).lower()
            
        if key not in self._readings:
            self._readings[key] = []
            
        self._readings[key].append(reading)
        
        # Rolling window - keep only last N readings for stability
        while len(self._readings[key]) > self._window_size:
            self._readings[key].pop(0)

        # Append to the time-series history buffer (for live line graphs)
        if key not in self._history:
            self._history[key] = []
        
        ts = reading.timestamp.timestamp() if reading.timestamp else time.time()
        self._history[key].append((ts, reading.value))
        self._trim_history(key)

        # Notify observers (session logging) of the raw sample.
        for callback in list(self._observers):
            try:
                callback(key, ts, reading.value)
            except Exception:
                pass

    def _trim_history(self, key: str):
        """Drop history samples older than the configured window (keeps graph bounded)."""
        bucket = self._history.get(key)
        if not bucket:
            return
        cutoff = datetime.now().timestamp() - self._history_seconds
        while bucket and bucket[0][0] < cutoff:
            bucket.pop(0)

    def get_history(self, sensor_type: str | SensorType) -> List[tuple]:
        """Return a copy of the time-series history for a sensor: [(epoch, value), ...].

        Used by the live line-graph renderer (v0.70). Empty list if no data yet."""
        if isinstance(sensor_type, SensorType):
            key = sensor_type.value
        else:
            key = str(sensor_type).lower()
        return list(self._history.get(key, []))

    def get_current_value(self, sensor_type: str | SensorType) -> Optional[float]:
        """Get smoothed value of most recent reading
        
        Uses simple moving average over last 5 readings for stable gauge display.
        
        Core v0.69+ gauges supported: engine_rpm (RPM), coolant_temp (°C), 
                                     battery_voltage (V) - all return float or None."""
        
        if isinstance(sensor_type, SensorType):
            key = sensor_type.value
        else:
            key = str(sensor_type).lower()
            
        readings_list = self._readings.get(key)
        if not readings_list:
            return None
            
        # Last 5 samples for smooth gauge updates (avoids jitter from single readings)
        values = [r.value for r in readings_list[-min(5, len(readings_list)):]]
        
        return sum(values) / len(values)

    def register_display_callback(self, callback: Callable[[Dict[str, float]], None]):
        """Register UI update handler to receive real-time gauge updates (RPM/Temp/Voltage)."""
        self._display_callbacks.append(callback)


# Create the file in one shot with clean implementation - this version works for OpenGonsult 0.69+ gauges display system integrating engine RPM monitoring & temperature/voltage dashboard widgets into GTK4 UI components.
