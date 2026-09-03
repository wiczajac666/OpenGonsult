"""DTC (Diagnostic Trouble Code) reading for Nissan CONSULT-I.

Nissan's Consult protocol returns stored fault codes as single-byte numeric
codes. Per the Consult protocol specification (Issue 5/6):

* Read DTC  -> command 0xd1
* Clear DTC -> command 0xc1
* Each stored fault is transmitted as a two-byte pair:
    byte 1 = fault code number
    byte 2 = number of ECU (engine) starts since the fault last occurred
* 0x55 means "no fault" and is used as padding / end sentinel.

This module decodes the raw response bytes into :class:`Fault` objects and
provides the human-readable code strings that the GUI displays. It also holds
a small "DTC Index" of common Nissan fault codes mapped to descriptions, so
raw numeric codes can be translated for the Diagnostics page.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Sentinel marking "no fault" (and used as padding).
NO_FAULT = 0x55

# Frame-start leader used by Consult responses.
FRAME_START = 0xFF


@dataclass
class Fault:
    """A single decoded fault code from the ECU.

    ``code`` is the numeric fault code byte; ``starts`` is the number of
    engine starts since the fault last occurred (0 for a current fault).
    """

    code: int
    starts: int = 0

    @property
    def display_code(self) -> str:
        """Stable, sortable string used for display and DB lookup."""
        return f"{self.code:02X}"

    @property
    def is_no_fault(self) -> bool:
        return self.code == NO_FAULT

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Fault(code={self.code:02X}, starts={self.starts})"


# Known Nissan fault-code index (numeric code -> description). This is an
# illustrative starter set; expand with the vehicle-specific DTC Index as data
# becomes available. Codes not present fall back to a generic label.
DTC_INDEX: Dict[int, str] = {
    0x01: "Ignition signal circuit malfunction",
    0x02: "Injector circuit malfunction",
    0x03: "Mass air flow sensor circuit malfunction",
    0x04: "Engine coolant temperature sensor circuit malfunction",
    0x05: "Oxygen sensor circuit malfunction",
    0x06: "Vehicle speed sensor circuit malfunction",
    0x07: "Throttle position sensor circuit malfunction",
    0x08: "Engine crankshaft position (CKP) sensor circuit malfunction",
    0x09: "Camshaft position (CMP) sensor circuit malfunction",
    0x0A: "Knock sensor circuit malfunction",
    0x0B: "Idle air control (IAC) valve malfunction",
    0x0C: "EGR function malfunction",
    0x0D: "EVAP control system malfunction",
    0x0E: "Fuel pressure regulator system malfunction",
    0x0F: "Intake air temperature sensor circuit malfunction",
    0x10: "Battery voltage circuit malfunction",
    0x11: "Closed loop control malfunction",
    0x12: "Fuel injector circuit malfunction (bank)",
    0x13: "Engine misfire detected",
    0x14: "Random/multiple cylinder misfire detected",
    0x15: "Ignition coil primary circuit malfunction",
    0x16: "Catalyst system efficiency below threshold",
    0x17: "System too lean (bank 1)",
    0x18: "System too rich (bank 1)",
    0x19: "System too lean (bank 2)",
    0x1A: "System too rich (bank 2)",
    0x1B: "Crankshaft position sensor signal circuit malfunction",
    0x1C: "Fuel pump circuit malfunction",
    0x1D: "Neutral position switch signal malfunction",
    0x1E: "A/T diagnosis communication line malfunction",
}


def _strip_frame_prefix(data: bytes) -> bytes:
    """Remove an optional Consult frame-start + length prefix.

    A response may arrive as ``(0xff)(length)(code)(starts)...``. If the
    leading byte is the frame-start leader, drop it and the length byte.
    """
    if not data:
        return data
    if data[0] == FRAME_START:
        # 0xff prefix, then a length byte: (frame)(len)(data...)
        return data[2:] if len(data) >= 2 else b""
    return data


def decode_faults(data: bytes) -> List[Fault]:
    """Decode raw Consult DTC response bytes into a list of Fault objects.

    Iterates the data in ``(code, starts)`` pairs, skipping the 0x55
    no-fault sentinel. Any trailing odd byte is ignored.
    """
    data = _strip_frame_prefix(bytes(data)) if data else b""
    faults: List[Fault] = []
    n = len(data)
    i = 0
    while i < n:
        # Faults are transmitted as (code, starts) pairs. A trailing odd
        # byte is a truncated/partial pair and is ignored to avoid reporting
        # a phantom fault from incomplete reads.
        if i + 1 >= n:
            break
        code = data[i]
        starts = data[i + 1]
        if code != NO_FAULT:
            faults.append(Fault(code=code, starts=starts))
        i += 2
    return faults


def decode_dtc_codes(data: bytes) -> List[str]:
    """Return the display strings for all stored faults (skips no-fault)."""
    return [f.display_code for f in decode_faults(data)]


def describe(code: int) -> str:
    """Return the DTC Index description for a fault code, or a fallback."""
    return DTC_INDEX.get(code, "Fault code not in local DTC index.")


def lookup(code: int) -> Tuple[str, str]:
    """Return (display_code, description) for a numeric fault code."""
    return f"{code:02X}", describe(code)
