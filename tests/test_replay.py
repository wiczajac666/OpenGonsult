import os
import tempfile
import unittest

from ecu.sensors import DashboardDataProcessor
from sessionrec.replay import SessionReplayer, PlaybackError
from sessionrec.formats import SessionSample, write_csv


def make_csv(path, samples):
    write_csv(path, samples)


class TestSessionReplayer(unittest.TestCase):
    def setUp(self):
        self.processor = DashboardDataProcessor(graph_history_seconds=300)

    def test_unsupported_format_raises(self):
        rp = SessionReplayer(self.processor)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(PlaybackError):
                rp.load(os.path.join(d, "s.xyz"))

    def test_load_sorts_samples_and_reports_duration(self):
        rp = SessionReplayer(self.processor)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.csv")
            # Deliberately out of order.
            make_csv(path, [
                SessionSample(100.0, "coolant_temp", 90.0),
                SessionSample(101.0, "engine_rpm", 1000.0),
                SessionSample(102.0, "engine_rpm", 1100.0),
            ])
            rp.load(path)
            self.assertTrue(rp.is_loaded)
            self.assertAlmostEqual(rp.duration_seconds(), 2.0)
            self.assertFalse(rp.is_playing)
            self.assertAlmostEqual(rp.position_seconds(), 0.0)

    def test_play_and_pump_delivers_all_samples_in_order(self):
        import time as _time
        rp = SessionReplayer(self.processor)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.csv")
            base = _time.time() - 3.0  # near-now so the processor keeps them
            make_csv(path, [
                SessionSample(base + 0.0, "engine_rpm", 1000.0),
                SessionSample(base + 1.0, "engine_rpm", 1100.0),
                SessionSample(base + 2.0, "engine_rpm", 1200.0),
                SessionSample(base + 3.0, "engine_rpm", 1300.0),
            ])
            rp.load(path)

            # Jump to the end then play -> pump immediately delivers everything.
            rp.seek(rp.duration_seconds())
            rp.play()
            rp.pump()

            history = self.processor.get_history("engine_rpm")
            self.assertEqual(len(history), 4)
            values = [v for _, v in history]
            self.assertEqual(values, [1000.0, 1100.0, 1200.0, 1300.0])
            self.assertFalse(rp.is_playing)  # auto-stops at end

    def test_control_state_transitions(self):
        rp = SessionReplayer(self.processor)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.csv")
            make_csv(path, [
                SessionSample(0.0, "engine_rpm", 1.0),
                SessionSample(10.0, "engine_rpm", 2.0),
            ])
            rp.load(path)

            self.assertFalse(rp.is_playing)
            rp.play()
            self.assertTrue(rp.is_playing)
            rp.pause()
            self.assertFalse(rp.is_playing)
            rp.play()
            self.assertTrue(rp.is_playing)
            rp.stop()
            self.assertFalse(rp.is_playing)
            self.assertAlmostEqual(rp.position_seconds(), 0.0)

    def test_unloaded_play_raises(self):
        rp = SessionReplayer(self.processor)
        with self.assertRaises(PlaybackError):
            rp.play()

    def test_pump_is_idempotent_when_not_playing(self):
        rp = SessionReplayer(self.processor)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.csv")
            make_csv(path, [SessionSample(0.0, "engine_rpm", 5.0)])
            rp.load(path)
            rp.pump()  # not playing -> no-op
            self.assertEqual(len(self.processor.get_history("engine_rpm")), 0)


if __name__ == "__main__":
    unittest.main()
