"""Session replayer: feed recorded samples back into a data processor.

A SessionReplayer loads a recorded session (CSV/SQLite/JSON), then replays it
in chronological order into a target ``DashboardDataProcessor`` using elapsed
wall-clock time, so a GUI timeout can drive playback at real speed. Supporting
play, pause, stop and absolute seek makes it suitable for a timeline control.
"""
import os
import time
from typing import List, Optional

from .formats import LOADERS, SessionSample


class PlaybackError(RuntimeError):
    """Raised for invalid or unloadable playback sessions."""


class SessionReplayer:
    """Play, pause, stop and seek through a recorded session."""

    def __init__(self, processor) -> None:
        self._processor = processor
        self._samples: List[SessionSample] = []
        self._start_ts: float = 0.0      # session-relative playback position (seconds)
        self._wall_at_start: float = 0.0 # wall clock when (re)play began or seeked
        self._playing = False
        self._source_path: Optional[str] = None

    # -- loading ----------------------------------------------------------
    def load(self, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()
        loader = LOADERS.get(ext)
        if loader is None:
            raise PlaybackError(f"Unsupported session format: {ext}")
        self._samples = sorted(loader(path), key=lambda s: s.timestamp)
        self._source_path = path
        self.stop()

    @property
    def source_path(self) -> Optional[str]:
        return self._source_path

    @property
    def is_loaded(self) -> bool:
        return bool(self._samples)

    def duration_seconds(self) -> float:
        if len(self._samples) < 2:
            return 0.0
        return self._samples[-1].timestamp - self._samples[0].timestamp

    # -- transport --------------------------------------------------------
    def play(self) -> None:
        if not self._samples:
            raise PlaybackError("No session loaded")
        if not self._playing:
            self._wall_at_start = time.time()
            self._playing = True

    def pause(self) -> None:
        if self._playing:
            self._start_ts = self.position_seconds()
            self._playing = False

    def stop(self) -> None:
        self._start_ts = 0.0
        self._playing = False

    def seek(self, seconds: float) -> None:
        seconds = max(0.0, seconds)
        dur = self.duration_seconds()
        if dur > 0:
            seconds = min(seconds, dur)
        self._start_ts = seconds
        self._wall_at_start = time.time()

    @property
    def is_playing(self) -> bool:
        return self._playing

    def position_seconds(self) -> float:
        """Elapsed session time from the start of the recording."""
        if self._playing:
            return self._start_ts + (time.time() - self._wall_at_start)
        return self._start_ts

    def at_end(self) -> bool:
        dur = self.duration_seconds()
        return dur > 0 and self.position_seconds() >= dur

    # -- delivery ---------------------------------------------------------
    def pump(self) -> None:
        """Deliver all samples up to the current playback position.

        Call from a GUI timeout while playing; idempotent and non-blocking.
        """
        if not self._playing or not self._samples:
            return
        pos = self.position_seconds()
        base = self._samples[0].timestamp
        delivered = 0
        for s in self._samples:
            if (s.timestamp - base) > pos:
                break
            self._processor.add_reading(s.sensor, _FakeReading(s.timestamp, s.value))
            delivered += 1
        if delivered:
            del self._samples[:delivered]
        if not self._samples:
            self._playing = False


class _FakeReading:
    """Minimal SensorReading-compatible shim for replay injection."""

    __slots__ = ("timestamp", "value")

    def __init__(self, timestamp: float, value: float) -> None:
        self.timestamp = _Epoch(timestamp)
        self.value = value


class _Epoch:
    """Wraps an epoch float with a .timestamp() method (as datetime does)."""

    __slots__ = ("_epoch",)

    def __init__(self, epoch: float) -> None:
        self._epoch = epoch

    def timestamp(self) -> float:
        return self._epoch
