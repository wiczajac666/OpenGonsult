#!/usr/bin/env python3
"""Decode a raw CONSULT-I DTC response into human-readable faults.

Shows the full path: raw bytes -> Fault objects -> display codes + descriptions.

Run from anywhere (adds the repo root to sys.path):
    python3 examples/decode_dtc.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecu.dtc import decode_dtc_codes, decode_faults, describe

FRAME = bytes([0xFF, 0x04, 0x13, 0x00, 0x08, 0x03])  # (0xff)(len)(code,starts)...


def main() -> None:
    print("Raw frame:", " ".join(f"{b:02X}" for b in FRAME))
    print("Display codes:", decode_dtc_codes(FRAME))
    for fault in decode_faults(FRAME):
        print(
            f"  {fault.display_code} (engine starts: {fault.starts:02X}) "
            f"- {describe(fault.code)}"
        )


if __name__ == "__main__":
    main()