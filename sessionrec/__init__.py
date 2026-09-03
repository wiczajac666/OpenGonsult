"""Session recording and replay.

Provides :class:`SessionSample` plus writers/readers for CSV, SQLite and JSON,
a :class:`SessionLogger` to capture live sensor samples, and a
:class:`SessionReplayer` to feed recorded sessions back into the processor.

Note: this package is named ``sessionrec`` (not ``logging``) deliberately to
avoid shadowing Python's standard-library ``logging`` module.
"""
from .formats import (
    SessionSample,
    SESSION_HEADERS,
    load_samples_csv,
    load_samples_sqlite,
    load_samples_json,
    write_csv,
    write_sqlite,
    write_json,
)
from .session_logger import SessionLogger
from .replay import SessionReplayer, PlaybackError

__all__ = [
    "SessionSample",
    "SESSION_HEADERS",
    "SessionLogger",
    "SessionReplayer",
    "PlaybackError",
    "load_samples_csv",
    "load_samples_sqlite",
    "load_samples_json",
    "write_csv",
    "write_sqlite",
    "write_json",
]
