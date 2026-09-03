import unittest
import os
import time
import subprocess
from unittest.mock import MagicMock

# Mocking GTK/Gdk before importing anything else
import sys
sys.modules['gi'] = MagicMock()
sys.modules['gi.repository'] = MagicMock()
sys.modules['cairo'] = MagicMock()

import ecu.sensors as sensors

class TestGraphUIIntegration(unittest.TestCase):
    def setUp(self):
        self.processor = sensors.DashboardDataProcessor(graph_history_seconds=60)

    def test_processor_integration(self):
        """Verify that the processor can feed a mock graph widget."""
        # 1. Simulate data
        for i in range(10):
            reading = sensors.SensorReading(
                sensor_type=sensors.SensorType.ENGINE_RPM,
                value=2000.0 + (i * 10),
                unit="RPM",
                raw_value=2000 + (i * 10)
            )
            self.processor.add_reading(sensors.SensorType.ENGINE_RPM, reading)
        
        # 2. Check if history is available
        history = self.processor.get_history(sensors.SensorType.ENGINE_RPM)
        self.assertEqual(len(history), 10)
        self.assertAlmostEqual(history[0][1], 2000.0)
        self.assertAlmostEqual(history[-1][1], 2090.0)

if __name__ == "__main__":
    unittest.main()
