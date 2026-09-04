import math
import random
import time
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ecu.sensors import DashboardDataProcessor, SensorReading, SensorType

# Constants for simulation
SIM_INTERVAL_MS = 200

GAUGE_UNITS = {
    "engine_rpm": "RPM",
    "coolant_temp": "deg C",
    "battery_voltage": "V",
    "vehicle_speed": "km/h",
    "throttle_position": "%",
    "oxygen_sensor": "V",
}

class SimulationEngine:
    """Handles synthetic sensor data generation for development and testing."""
    
    def __init__(self, processor: Any):
        self.processor = processor
        self.sim_start_time = None

    def start(self):
        self.sim_start_time = time.time()

    def stop(self):
        self.sim_start_time = None

    def tick(self) -> bool:
        """Generates a single frame of synthetic sensor data."""
        if self.processor is None or self.sim_start_time is None:
            return True
        
        elapsed = time.time() - self.sim_start_time
        rev_band = abs(((elapsed % 26.0) / 26.0) * 2.0 - 1.0)
        
        rpm = (
            900.0
            + 140.0 * (1.0 + (elapsed % 7.0) / 7.0)
            + rev_band ** 5 * 4200.0
            + random.gauss(0.0, 25.0)
        )
        rpm = max(0.0, rpm)
        
        speed = max(0.0, min(130.0, rev_band ** 2 * 110.0 + random.gauss(0.0, 2.0)))
        throttle = max(0.0, min(100.0, (rpm - 850.0) / 55.0 + random.gauss(0.0, 1.5)))
        coolant = min(93.0, 22.0 + elapsed * 0.9) + random.gauss(0.0, 0.15)
        voltage = 13.9 + 0.12 * ((elapsed % 5.0) / 5.0) + random.gauss(0.0, 0.03)
        o2 = max(0.1, min(0.9, 0.5 + 0.35 * (elapsed % 1.2 > 0.6) + random.gauss(0.0, 0.02)))

        samples = {
            "engine_rpm": rpm,
            "coolant_temp": coolant,
            "battery_voltage": voltage,
            "vehicle_speed": speed,
            "throttle_position": throttle,
            "oxygen_sensor": o2,
        }
        
        self._apply_samples(samples)
        return True

    def _apply_samples(self, samples: Dict[str, float]):
        # Importing inside method to avoid circular dependency if needed
        # or if types are not available in the environment
        from ecu.sensors import SensorReading, SensorType
        
        for key, value in samples.items():
            sensor_type = None
            try:
                sensor_type = SensorType[key.upper()]
            except (KeyError, NameError):
                sensor_type = None
                
            # Using local SensorReading/SensorType check
            try:
                reading = SensorReading(
                    sensor_type=sensor_type,
                    value=float(value),
                    unit=GAUGE_UNITS.get(key, ""),
                    raw_value=int(round(value)),
                )
                self.processor.add_reading(key, reading)
            except Exception:
                pass
