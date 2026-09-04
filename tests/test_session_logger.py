import os
import json
import sqlite3
import tempfile
import unittest

from ecu.sensors import DashboardDataProcessor, SensorReading, SensorType
from sessionrec.session_logger import SessionLogger


def make_processor():
    return DashboardDataProcessor(graph_history_seconds=300)


def add_reading(processor, key, value, ts=None):
    from datetime import datetime
    reading = SensorReading(
        sensor_type=key,
        value=value,
        unit="u",
        raw_value=float(value),
        timestamp=ts if ts is not None else datetime.now(),
    )
    processor.add_reading(key, reading)


class TestSessionLogger(unittest.TestCase):
    def test_recording_captures_samples_and_stops(self):
        proc = make_processor()
        logger = SessionLogger(proc)
        self.assertFalse(logger.is_recording)
        logger.start()
        self.assertTrue(logger.is_recording)

        add_reading(proc, SensorType.ENGINE_RPM, 1200.0)
        add_reading(proc, SensorType.ENGINE_RPM, 1300.0)
        add_reading(proc, SensorType.COOLANT_TEMP, 85.0)

        samples = logger.stop()
        self.assertFalse(logger.is_recording)
        self.assertIsNotNone(samples)
        self.assertEqual(len(samples), 3)
        self.assertEqual(samples[0].sensor, "engine_rpm")
        self.assertAlmostEqual(samples[2].value, 85.0)

    def test_samples_not_captured_before_start(self):
        proc = make_processor()
        logger = SessionLogger(proc)
        add_reading(proc, SensorType.ENGINE_RPM, 999.0)  # before start
        logger.start()
        add_reading(proc, SensorType.ENGINE_RPM, 1500.0)
        samples = logger.stop()
        self.assertEqual(len(samples), 1)
        self.assertAlmostEqual(samples[0].value, 1500.0)

    def test_sensor_counts(self):
        proc = make_processor()
        logger = SessionLogger(proc)
        logger.start()
        add_reading(proc, SensorType.ENGINE_RPM, 1.0)
        add_reading(proc, SensorType.ENGINE_RPM, 2.0)
        add_reading(proc, SensorType.COOLANT_TEMP, 3.0)
        logger.stop()
        counts = logger.sensors
        self.assertEqual(counts, {"engine_rpm": 2, "coolant_temp": 1})

    def test_save_roundtrip_all_formats(self):
        proc = make_processor()
        logger = SessionLogger(proc)
        logger.start()
        add_reading(proc, SensorType.ENGINE_RPM, 2000.0)
        add_reading(proc, SensorType.COOLANT_TEMP, 88.0)
        logger.stop()

        with tempfile.TemporaryDirectory() as d:
            # CSV
            csv_path = os.path.join(d, "s.csv")
            logger.save(csv_path, ".csv")
            with open(csv_path) as fh:
                header = fh.readline().strip()
                self.assertEqual(header, "timestamp,sensor,value")

            # JSON
            json_path = os.path.join(d, "s.json")
            logger.save(json_path, ".json")
            with open(json_path) as fh:
                data = json.load(fh)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["sensor"], "engine_rpm")

            # SQLite
            sqlite_path = os.path.join(d, "s.sqlite")
            logger.save(sqlite_path, ".sqlite")
            conn = sqlite3.connect(sqlite_path)
            n = conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            conn.close()
            self.assertEqual(n, 2)

    def test_save_unsupported_format_raises(self):
        proc = make_processor()
        logger = SessionLogger(proc)
        logger.start()
        logger.stop()
        with self.assertRaises(ValueError):
            logger.save("out.xyz", ".xyz")


if __name__ == "__main__":
    unittest.main()
