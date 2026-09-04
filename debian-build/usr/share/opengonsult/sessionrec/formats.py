"""Session sample format + CSV/SQLite/JSON readers and writers.

A "sample" is a single time/value observation:
    SessionSample(timestamp: float (epoch seconds), sensor: str, value: float)

All writers/readers operate on an iterable of SessionSample so the on-disk
format is decoupled from the in-memory representation.
"""
import csv
import json
import sqlite3
from collections import namedtuple
from typing import Iterable, List

SessionSample = namedtuple("SessionSample", ["timestamp", "sensor", "value"])

SESSION_HEADERS = ["timestamp", "sensor", "value"]


def write_csv(path: str, samples: Iterable[SessionSample]) -> None:
    """Write samples to a CSV file (timestamp, sensor, value)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(SESSION_HEADERS)
        for s in samples:
            writer.writerow([f"{s.timestamp:.3f}", s.sensor, f"{s.value:.6g}"])


def load_samples_csv(path: str) -> List[SessionSample]:
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        out = []
        for row in reader:
            out.append(
                SessionSample(
                    float(row["timestamp"].strip()),
                    row["sensor"].strip(),
                    float(row["value"]),
                )
            )
    return out


def write_sqlite(path: str, samples: Iterable[SessionSample]) -> None:
    """Write samples into a SQLite database with a samples table."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("BEGIN")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS samples (timestamp REAL, sensor TEXT, value REAL)"
        )
        conn.executemany(
            "INSERT INTO samples (timestamp, sensor, value) VALUES (?, ?, ?)",
            [(s.timestamp, s.sensor, s.value) for s in samples],
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_samples_time ON samples (timestamp)"
        )
        conn.commit()
    finally:
        conn.close()


def load_samples_sqlite(path: str) -> List[SessionSample]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(
            "SELECT timestamp, sensor, value FROM samples ORDER BY timestamp"
        ).fetchall()
    finally:
        conn.close()
    return [SessionSample(t, s, v) for t, s, v in rows]


def write_json(path: str, samples: Iterable[SessionSample]) -> None:
    """Write samples as a JSON list of {timestamp, sensor, value} dicts."""
    data = [
        {"timestamp": s.timestamp, "sensor": s.sensor, "value": s.value}
        for s in samples
    ]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_samples_json(path: str) -> List[SessionSample]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [SessionSample(float(d["timestamp"]), str(d["sensor"]), float(d["value"])) for d in data]


# Public loader dispatch used by replay.
LOADERS = {
    ".csv": load_samples_csv,
    ".sqlite": load_samples_sqlite,
    ".db": load_samples_sqlite,
    ".json": load_samples_json,
}
