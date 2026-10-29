"""Monitoring-set helpers for OpenGonsult."""
from __future__ import annotations

from typing import List, Sequence

DEFAULT_MONITORED_SENSORS = [
    "engine_rpm",
    "coolant_temp",
    "battery_voltage",
    "vehicle_speed",
    "throttle_position",
    "oxygen_sensor",
]

ALL_KNOWN_SENSORS = [
    "engine_rpm",
    "coolant_temp",
    "battery_voltage",
    "vehicle_speed",
    "throttle_position",
    "oxygen_sensor",
    "intake_air_temp",
    "maf_sensor",
    "oxygen_sensor_left",
    "oxygen_sensor_right",
    "ignition_timing",
    "iacv_aacv",
    "af_alpha",
    "injector_pulse",
    "injector_duty",
]


class MonitoringSet:
    def __init__(self, sensors=None):
        self._sensors = []
        for s in (sensors if sensors is not None else DEFAULT_MONITORED_SENSORS):
            self.add(s)

    def sensors(self):
        return list(self._sensors)

    def add(self, sensor):
        key = str(sensor).strip().lower()
        if not key or key in self._sensors:
            return False
        self._sensors.append(key)
        return True

    def remove(self, sensor):
        key = str(sensor).strip().lower()
        if key in self._sensors:
            self._sensors.remove(key)
            return True
        return False

    def move(self, sensor, new_index):
        key = str(sensor).strip().lower()
        if key not in self._sensors:
            return False
        self._sensors.remove(key)
        new_index = max(0, min(len(self._sensors), int(new_index)))
        self._sensors.insert(new_index, key)
        return True

    def clear(self):
        self._sensors.clear()

    def reset(self):
        self._sensors = list(DEFAULT_MONITORED_SENSORS)

    def contains(self, sensor):
        return str(sensor).strip().lower() in self._sensors

    def __len__(self):
        return len(self._sensors)

    def __iter__(self):
        return iter(self._sensors)

    def to_list(self):
        return list(self._sensors)

    @classmethod
    def from_list(cls, sensors):
        return cls(sensors)

    def to_config(self):
        return {"monitored_sensors": list(self._sensors)}

    @classmethod
    def from_config(cls, config):
        sensors = None
        if isinstance(config, dict):
            sensors = config.get("monitored_sensors") or config.get("gauge_order")
        return cls(sensors)


MonitoringConfig = MonitoringSet
SensorSelection = MonitoringSet

MonitoringManager = MonitoringSet
MonitoringConfigManager = MonitoringSet
SensorMonitor = MonitoringSet
