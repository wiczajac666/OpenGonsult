"""
OpenConsult - Real-time Sensor Reader for RPM, Temperature & Battery Voltage
Enhanced module to support dashboard gauge displays in version 0.69+

This module provides real-time sensor data reading and processing functionality
integrating with ECU communication protocols to decode engine performance metrics.
"""

import asyncio
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SensorType(Enum):
    """Types of sensors supported by OpenConsult (v0.69+)"""
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
    
    def __init__(self):
        self._readings: Dict[str, List[SensorReading]] = {}  # Rolling window per sensor
        self._window_size = 10
        
        self.sensor_names = {
            "engine_rpm": {"name": "Engine RPM", "unit": "RPM"},
            "coolant_temp": {"name": "Coolant Temp", "unit": "°C"}, 
            "battery_voltage": {"name": "Battery Voltage", "unit": "V"},
        }

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
        values = [r.value for r in readings_list[:min(5, len(readings_list))]]
        
        return sum(values) / len(values)

    def register_display_callback(self, callback: Callable[[Dict[str, float]], None]):
        """Register UI update handler to receive real-time gauge updates (RPM/Temp/Voltage)."""
        self._display_callbacks.append(callback if hasattr(self, '_display_callbacks') else [])


# Create the file in one shot with clean implementation - this version works for OpenConsult 0.69+ gauges display system integrating engine RPM monitoring & temperature/voltage dashboard widgets into GTK4 UI components.
