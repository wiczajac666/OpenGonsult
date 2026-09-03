import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ---- Minimal fake GTK so the module can be imported ----
fake_gtk = types.ModuleType("gi")
fake_gtk.require_version = staticmethod(lambda *a: None)
fake_repo = types.ModuleType("gi.repository")

class FakeGtk:
    Box = type("Box", (), {"__init__": lambda self, *a, **k: None})
    DrawingArea = type("DrawingArea", (), {"__init__": lambda self, *a, **k: None})
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
    class ButtonsType:
        OK = 0
    class ResponseType:
        YES = 0
    @staticmethod
    def require_version(*a):
        pass

fake_repo.Gtk = FakeGtk()
fake_repo.Gdk = types.ModuleType("Gdk")
fake_repo.Gdk.MemoryFormat = type("MF", (), {"B8G8R8A8_PREMULTIPLIED": 0})
fake_repo.Gdk.MemoryTexture = type("MT", (), {})
fake_repo.GLib = types.ModuleType("GLib")
fake_repo.GLib.timeout_add_seconds = staticmethod(lambda *a: 1)
fake_repo.Gio = types.ModuleType("Gio")
fake_repo.Gio.ApplicationFlags = type("AF", (), {"FLAGS_NONE": 0})
fake_repo.GdkPixbuf = types.ModuleType("GdkPixbuf")

sys.modules["gi"] = fake_gtk
sys.modules["gi.repository"] = fake_repo
sys.modules["cairo"] = types.ModuleType("cairo")

from graphs.sensor_graph import plot_xy  # noqa: E402


class TestPlotXY(unittest.TestCase):
    """Unit tests for the pure plot coordinate-mapping function."""

    def setUp(self):
        # plot rect: x from 60..780 (width 720), y from 20..460 (height 440)
        self.x0, self.y0 = 60.0, 20.0
        self.w, self.h = 720.0, 440.0
        self.window_start = 1000.0
        self.window = 100.0

    def test_leftmost_time_maps_to_plot_x0(self):
        x, y = plot_xy(
            1000.0, 0.0, self.window_start, self.window,
            -1.0, 1.0, self.x0, self.y0, self.w, self.h,
        )
        self.assertAlmostEqual(x, self.x0)

    def test_rightmost_time_maps_to_plot_rhs(self):
        x, _ = plot_xy(
            1100.0, 0.0, self.window_start, self.window,
            -1.0, 1.0, self.x0, self.y0, self.w, self.h,
        )
        self.assertAlmostEqual(x, self.x0 + self.w)

    def test_max_value_maps_to_top(self):
        # y inverted: max value -> plot_y0 (top)
        _, y = plot_xy(
            1000.0, 1.0, self.window_start, self.window,
            -1.0, 1.0, self.x0, self.y0, self.w, self.h,
        )
        self.assertAlmostEqual(y, self.y0)

    def test_min_value_maps_to_bottom(self):
        _, y = plot_xy(
            1000.0, -1.0, self.window_start, self.window,
            -1.0, 1.0, self.x0, self.y0, self.w, self.h,
        )
        self.assertAlmostEqual(y, self.y0 + self.h)

    def test_output_clamped_to_plot_rect(self):
        # Value far above range should clamp to the bottom edge (max y).
        _, y = plot_xy(
            1000.0, 9999.0, self.window_start, self.window,
            0.0, 1.0, self.x0, self.y0, self.w, self.h,
        )
        self.assertGreaterEqual(y, self.y0)
        self.assertLessEqual(y, self.y0 + self.h)

    def test_degenerate_ranges_dont_crash(self):
        x, y = plot_xy(
            1000.0, 0.5, self.window_start, 0.0,
            0.5, 0.5, self.x0, self.y0, self.w, self.h,
        )
        self.assertEqual(type(x), float)
        self.assertEqual(type(y), float)


if __name__ == "__main__":
    unittest.main()
