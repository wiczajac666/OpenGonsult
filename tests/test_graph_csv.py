import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Build a fake GTK that lets SensorGraphWidget subclass a plain object,
# while still exposing the attributes the module uses at import time.
import types

fake_gtk = types.ModuleType("gi")
fake_repo = types.ModuleType("gi.repository")
fake_gtk.require_version = lambda *a: None

class FakeBox:
    def __init__(self, *a, **k):
        pass


# Provide the GTK symbols the module references.
class FakeGtk:
    Box = FakeBox
    class Orientation:
        VERTICAL = 0
        HORIZONTAL = 1
    class Align:
        CENTER = 0
    class PolicyType:
        NEVER = 0
        AUTOMATIC = 1
    class SelectionMode:
        SINGLE = 0
        NONE = 1
    class StackTransitionType:
        CROSSFADE = 0
    class MessageType:
        ERROR = 0
        INFO = 1
        QUESTION = 2
    class ButtonsType:
        OK = 0
        YES_NO = 1
    class ResponseType:
        YES = 0
    class Justification:
        CENTER = 0
    def require_version(self, *a):
        pass


fake_repo.Gtk = FakeGtk()
fake_repo.Gdk = type("Gdk", (), {})
fake_repo.GLib = type("GLib", (), {"timeout_add_seconds": lambda *a: 1})
fake_repo.Gio = type("Gio", (), {"ApplicationFlags": type("AF", (), {"FLAGS_NONE": 0})})
fake_repo.Pango = type("Pango", (), {"EllipsizeMode": type("EM", (), {"END": 0})})
fake_repo.GdkPixbuf = type("GdkPixbuf", (), {})

sys.modules["gi"] = fake_gtk
sys.modules["gi.repository"] = fake_repo
sys.modules["cairo"] = types.ModuleType("cairo")

from graphs.sensor_graph import SensorGraphWidget, SENSOR_LABELS


class TestCsvExport(unittest.TestCase):
    def setUp(self):
        self.widget = object.__new__(SensorGraphWidget)
        self.widget.data_processor = None
        self.widget.checkboxes = {}
        self.widget.time_window_seconds = 120.0

    def test_write_csv_headers_and_values(self):
        series = {
            "engine_rpm": [(1000.0, 2000.0), (1001.0, 2100.0), (1002.0, 2200.0)],
            "battery_voltage": [(1000.0, 13.5), (1002.0, 13.6)],
        }
        handler, tmp = tempfile.mkstemp(suffix=".csv")
        os.close(handler)
        try:
            self.widget._write_csv(tmp, series)
            with open(tmp) as fh:
                content = fh.read()
        finally:
            os.unlink(tmp)

        lines = content.strip().splitlines()
        header = lines[0]
        self.assertIn("timestamp", header)
        self.assertIn(SENSOR_LABELS["engine_rpm"], header)
        self.assertIn(SENSOR_LABELS["battery_voltage"], header)

        # Engine RPM has 3 samples, battery voltage has 2 -> 3 data rows.
        data_rows = lines[1:]
        self.assertEqual(len(data_rows), 3)
        self.assertIn("13.5", content)
        self.assertIn("13.6", content)


if __name__ == "__main__":
    unittest.main()
