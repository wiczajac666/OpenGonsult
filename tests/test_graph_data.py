import unittest
from ecu.sensors import DashboardDataProcessor, SensorReading, SensorType

class TestGraphData(unittest.TestCase):
    def setUp(self):
        # Initialize processor with 120s history
        self.processor = DashboardDataProcessor(graph_history_seconds=120)

    def test_history_buffer_accumulation(self):
        """Verify that readings are correctly added to the time-series history buffer."""
        sensor = SensorType.ENGINE_RPM

        # Add 5 readings
        for i in range(5):
            reading = SensorReading(
                sensor_type=sensor,
                value=1000.0 + (i * 100),
                unit="RPM",
                raw_value=int(1000.0 + (i * 100)),
                timestamp=None # Uses datetime.now() inside
            )
            self.processor.add_reading(sensor, reading)
            
        history = self.processor.get_history(sensor)
        self.assertEqual(len(history), 5, f"Expected 5 history points, got {len(history)}")
        
        # Check value integrity
        # history is [(epoch, value), ...]
        for i in range(5):
            self.assertAlmostEqual(history[i][1], 1000.0 + (i * 100))

    def test_history_buffer_trimming(self):
        """Verify that history is trimmed based on the configured window (seconds)."""
        sensor = SensorType.BATTERY_VOLTAGE
        
        # We need to simulate old timestamps. Since SensorReading uses datetime.now(),
        # we might need to mock datetime or just rely on the fact that get_history 
        # doesn't trim on read, but add_reading calls _trim_history.
        
        # Injecting a reading from 200 seconds ago
        from datetime import datetime, timedelta
        old_time = datetime.now() - timedelta(seconds=200)
        
        # This is tricky because SensorReading uses datetime.now() as default.
        # Let's see if we can pass a timestamp.
        # Looking at SensorReading dataclass: timestamp: datetime = field(default_factory=datetime.now)
        
        # Try to add an old reading
        old_reading = SensorReading(
            sensor_type=sensor,
            value=12.0,
            unit="V",
            raw_value=12,
            timestamp=old_time
        )
        
        self.processor.add_reading(sensor, old_reading)
        
        # Add a new reading to trigger _trim_history
        new_reading = SensorReading(
            sensor_type=sensor,
            value=13.0,
            unit="V",
            raw_value=13
        )
        self.processor.add_reading(sensor, new_reading)
        
        history = self.processor.get_history(sensor)
        
        # The old reading (200s ago) should have been trimmed because window is 120s.
        # Only the new reading should remain.
        self.assertEqual(len(history), 1, f"Expected 1 history point after trim, got {len(history)}")
        self.assertAlmostEqual(history[0][1], 13.0)

    def test_get_current_value_smoothing(self):
        """Verify that get_current_value returns the moving average of the last 5 readings."""
        sensor = SensorType.COOLANT_TEMP
        
        # Add 10 readings
        for i in range(10):
            val = 50.0 + i
            reading = SensorReading(
                sensor_type=sensor,
                value=val,
                unit="deg C",
                raw_value=int(val)
            )
            self.processor.add_reading(sensor, reading)
            
        # Last 5 readings: 55, 56, 57, 58, 59
        # Average: (55+56+57+58+59) / 5 = 285 / 5 = 57.0
        avg = self.processor.get_current_value(sensor)
        self.assertAlmostEqual(avg, 57.0)

if __name__ == "__main__":
    unittest.main()
