#!/usr/bin/env python3
"""Record a short session to CSV and replay it back through the processor.

Demonstrates the sessionrec library end-to-end:
  SessionLogger (capture) -> save CSV -> load_samples_csv -> SessionReplayer.

Run from anywhere:
    python3 examples/record_replay.py
"""
import math
import os
import sys
import tempfile
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecu.sensors import DashboardDataProcessor, SensorReading, SensorType
from sessionrec import SessionLogger, SessionReplayer, load_samples_csv


def feed(proc: DashboardDataProcessor, n: int = 30, delay: float = 0.02) -> None:
    for step in range(n):
        rpm = round(900 + 700 * math.sin(step / 6.0), 1)
        reading = SensorReading(
            sensor_type=SensorType.ENGINE_RPM,
            value=rpm,
            unit="RPM",
            raw_value=int(rpm),
            timestamp=datetime.now(),
        )
        proc.add_reading(SensorType.ENGINE_RPM, reading)
        time.sleep(delay)


def main() -> None:
    proc = DashboardDataProcessor()
    logger = SessionLogger(proc)

    logger.start()
    feed(proc)
    logger.stop()
    print("Captured samples:", len(logger.samples()))

    path = os.path.join(tempfile.gettempdir(), "opengonsult_demo.csv")
    saved = logger.save(path)
    print("Saved session:", saved)

    reloaded = load_samples_csv(path)
    print("Reloaded samples:", len(reloaded))

    replay_proc = DashboardDataProcessor()
    replayer = SessionReplayer(replay_proc)
    replayer.load(path)
    print("Session duration:", round(replayer.duration_seconds(), 2), "s")

    replayer.play()
    stopwatch = time.time()
    while replayer.is_playing and (time.time() - stopwatch) < 10:
        replayer.pump()
        time.sleep(0.01)
    replayer.pump()

    print("Replayed history points:", len(replay_proc.get_history(SensorType.ENGINE_RPM)))


if __name__ == "__main__":
    main()