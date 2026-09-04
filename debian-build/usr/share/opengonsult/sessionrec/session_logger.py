"""Session logger: capture live sensor samples for later export/replay.

A SessionLogger subscribes to a ``DashboardDataProcessor`` and buffers each
incoming reading as a SessionSample while recording is active. When stopped,
the buffered session can be written to CSV, SQLite or JSON via the formats
module.

Typical usage::

    logger = SessionLogger(processor)
    logger.start()
    # ... readings arrive via processor.add_reading() ...
    logger.stop()
    logger.save("session.csv", ".csv")
"""
import time
from typing import Dict, List, Optional

from .formats import SessionSample, write_csv, write_sqlite, write_json

FORMAT_EXTENSION_TO_WRITER = {
    ".csv": write_csv,
    ".sqlite": write_sqlite,
    ".db": write_sqlite,
    ".json": write_json,
}


class SessionLogger:
    """Thread-safe-ish best-effort recorder attached to a data processor."""

    def __init__(self, processor) -> None:
        self._processor = processor
        self._samples: List[SessionSample] = []
        self._recording = False
        self._start_time: Optional[float] = None
        self._sensor_count: Dict[str, int] = {}

    # -- controller -------------------------------------------------------
    def start(self) -> None:
        if self._recording:
            return
        self._samples = []
        self._sensor_count = {}
        self._start_time = time.time()
        self._recording = True
        self._processor.subscribe(self._on_sample)

    def stop(self) -> Optional[List[SessionSample]]:
        if not self._recording:
            return None
        self._recording = False
        self._processor.unsubscribe(self._on_sample)
        return list(self._samples)

    def reset(self) -> None:
        self.stop()
        self._samples = []
        self._sensor_count = {}
        self._start_time = None

    # -- observer ---------------------------------------------------------
    def _on_sample(self, key: str, ts: float, value: float) -> None:
        if not self._recording:
            return
        self._samples.append(SessionSample(ts, str(key), float(value)))
        self._sensor_count[str(key)] = self._sensor_count.get(str(key), 0) + 1

    # -- queries ----------------------------------------------------------
    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def start_time(self) -> Optional[float]:
        return self._start_time

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def sensors(self) -> Dict[str, int]:
        return dict(self._sensor_count)

    def samples(self) -> List[SessionSample]:
        return list(self._samples)

    # -- export -----------------------------------------------------------
    def save(self, path: str, fmt: Optional[str] = None) -> str:
        """Persist the recorded session using the given (or inferred) format.

        Returns the path written. Raises ValueError for an unsupported format.
        """
        ext = (fmt or "." + path.rsplit(".", 1)[-1]).lower()
        if not ext.startswith("."):
            ext = "." + ext
        writer = FORMAT_EXTENSION_TO_WRITER.get(ext)
        if writer is None:
            raise ValueError(f"Unsupported log format: {ext}")
        writer(path, self.samples())
        return path
