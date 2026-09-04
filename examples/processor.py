#!/usr/bin/env python3
"""Drive DashboardDataProcessor with simulated sensor readings.

No car, no GUI, no GTK: just the pure sensor-processing core. Demonstrates
the rolling-window moving average and the time-series history buffer.

Run from anywhere:
    python3 examples/processor.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecu.sensors import DashboardDataProcessor, SensorReading, SensorType


def main() -> None:
    proc = DashboardDataProcessor(graph_history_seconds=60)
    for step in range(200):
        rpm = round(900 + 700 * math.sin(step / 6.0), 1)
        raw_value = int(rpm * 10 / 497)  # pretend scaling factor ~49.7 rpm/raw
        reading = SensorReading(
            sensor_type=SensorType.ENGINE_RPM,
            value=rpm,
            unit="RPM",
            raw_value=raw_value,
        )
        proc.add_reading(SensorType.ENGINE_RPM, reading)

    print("Smoothed RPM (last 5 avg):", proc.get_current_value(SensorType.ENGINE_RPM))
    print("History points:", len(proc.get_history(SensorType.ENGINE_RPM)))
    print("History sample:", proc.get_history(SensorType.ENGINE_RPM)[-1])


if __name__ == "__main__":
    main()