"""Logfile analyzer helpers for OpenGonsult (Conzult 'Logfile analyzer')."""
from __future__ import annotations

from typing import Dict, List, Tuple

try:
    from sessionrec.formats import SessionSample, load_samples_csv
except Exception:  # pragma: no cover
    SessionSample = None


def analyze_samples(samples) -> Dict[str, dict]:
    """Return per-sensor statistics: count, min, max, mean."""
    stats: Dict[str, dict] = {}
    for s in samples:
        sensor = getattr(s, "sensor", None)
        if sensor is None and isinstance(s, (tuple, list)):
            sensor = s[1] if len(s) > 1 else None
        value = getattr(s, "value", None)
        if value is None and isinstance(s, (tuple, list)):
            value = s[2] if len(s) > 2 else None
        if sensor is None:
            continue
        bucket = stats.setdefault(sensor, {"count": 0, "min": None, "max": None, "sum": 0.0})
        v = float(value)
        bucket["count"] += 1
        bucket["sum"] += v
        if bucket["min"] is None or v < bucket["min"]:
            bucket["min"] = v
        if bucket["max"] is None or v > bucket["max"]:
            bucket["max"] = v
    for b in stats.values():
        b["mean"] = (b["sum"] / b["count"]) if b["count"] else 0.0
        del b["sum"]
    return stats


def duration_seconds(samples) -> float:
    if not samples:
        return 0.0
    ts = [getattr(s, "timestamp", None) for s in samples]
    if any(t is None for t in ts):
        # fall back to first element if tuple
        ts = [s[0] if isinstance(s, (tuple, list)) else 0 for s in samples]
    return float(max(ts) - min(ts)) if ts else 0.0


def sensor_counts(samples) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for s in samples:
        sensor = getattr(s, "sensor", None)
        if sensor is None and isinstance(s, (tuple, list)):
            sensor = s[1] if len(s) > 1 else None
        if sensor is None:
            continue
        counts[sensor] = counts.get(sensor, 0) + 1
    return counts


class LogfileAnalyzer:
    def __init__(self, samples=None):
        self.samples = list(samples or [])

    def load(self, samples):
        self.samples = list(samples or [])
        return self

    def analyze(self):
        return analyze_samples(self.samples)

    def duration(self):
        return duration_seconds(self.samples)

    def counts(self):
        return sensor_counts(self.samples)


Analyzer = LogfileAnalyzer
LogAnalyzer = LogfileAnalyzer
SessionAnalyzer = LogfileAnalyzer
