# CONSULT-I Protocol Specification

OpenGonsult implements the Nissan **CONSULT-I** diagnostic protocol for the
14-pin connector. This document is the ground truth for the wire format as
implemented in `protocol/consult.py`, `serial/adapter.py` and `ecu/dtc.py`.

> **Compatibility note:** CONSULT-I is the same family of protocol used by
> the `Consult-I` parts of Nissan's `consult3`/`consult-i` tooling. The
> byte-level framing here follows the classic Consult protocol (Issue 5/6)
> conventions: STX-prefixed payloads, XOR checksums, and single-byte
> sub-function command codes.

---

## 1. Transport & Connection

- Serial port default: `/dev/ttyUSB0` (USB-serial adapters: FTDI, CH340,
  PL2303; Bluetooth SPP supported via the same adapter).
- Default baud config: **9600 8N1**, 1.0 s timeout (GUI exposes
  `9600, 19200, 38400, 57600, 115200, 230400`).
- Connection is managed by `SerialAdapter` (see `serial/adapter.py`) with a
  single command worker queue so reads/writes/transactions never race.
- States follow a proper state machine
  (`ConnectionState`): `init → connecting → established → disconnected/reconnecting`.

## 2. Frame Format

`protocol/consult.py` defines a **framed, timestamped envelope** around every
packet (`FramedFrame`) to add integrity and replay protection on top of the
classic wire format.

### 2.1 On-the-wire packet

```
+------+----------+-------------+----------+----------+
| STX  | mode     | sub-function| data...  | checksum |
| 0x02 | 1 byte   | 1 byte      | 0..N     | 1 byte   |
+------+----------+-------------+----------+----------+
```

- `STX = 0x02` (Start of Text) — the packet header.
- The **checksum is the XOR** of all prior bytes (`calculate_checksum`).
  A packet is valid only if `xor(all bytes except last) == last byte`.
- `RequestPacket.encode(sub_function, data)` builds `[0x02][mode][sub][data...][xor]`.
- `ResponsePacket.decode()` returns `(sub_function, data)` after frame validation.

### 2.2 Framed metadata (`FramedFrame`)

Each `ConsultPacket` also carries a `FramedFrame` with:

| Field       | Meaning                                                            |
|-------------|--------------------------------------------------------------------|
| `payload`   | raw payload bytes (`mode + sub-function + data`)                   |
| `timestamp` | `time.time()` nonce used for freshness + replay detection          |
| `signature` | `sha256(payload || pack('d', timestamp))[:32]` hex digest          |

Validation is strictly ordered — **TIMING → SIGNATURE → CONTENT**:

1. `validate_timestamp()` — frames older than `MAX_TIMESTAMP_WINDOW_SECONDS`
   (**60 s**) raise `TimestampExpiredError`. Cheap check runs first to avoid
   expensive crypto on stale frames.
2. `validate_signature_no_replay(cache)` — a signature already present in the
   per-session cache raises `ReplayAttackError`; otherwise it is added
   (cache size `REPLAY_CACHE_SIZE = 1024`).
3. Content is processed only after 1 & 2 pass.

## 3. Command / Mode Constants

Set in `gui/main_window.py`:

| Constant                    | Value | Meaning                        |
|-----------------------------|-------|--------------------------------|
| `CONSULT_ECU_ID`            | `0x01`| Default ECU address            |
| `CONSULT_MODE_LIVE_DATA`    | `0x01`| Live data mode                 |
| `CONSULT_CMD_DTC_READ`      | `0xD1`| Read stored DTCs               |
| `CONSULT_CMD_DTC_CLEAR`     | `0xC1`| Clear stored DTCs              |

### 3.1 Live sensor read commands

`SENSOR_COMMANDS` — the sub-function sent in live-data mode:

| Sensor             | Command |
|--------------------|---------|
| `engine_rpm`       | `0x09`  |
| `coolant_temp`     | `0x0B`  |
| `battery_voltage`  | `0x14`  |
| `vehicle_speed`    | `0x08`  |
| `throttle_position`| `0x11`  |
| `oxygen_sensor`    | `0x13`  |

Raw response values are mapped to physical units through
`SensorDefinition` (scaling factor + offset) in `ecu/ecu_db.py`.

## 4. Diagnostic Trouble Codes (DTC)

Implemented in `ecu/dtc.py`.

Per the Consult protocol specification:

- **Read DTC** → send `RequestPacket(mode=0xD1).encode(0x00)`.
- **Clear DTC** → send `RequestPacket(mode=0xC1).encode(0x00)`.
- Each stored fault is **two bytes**:

  ```
  byte 1 = fault code number
  byte 2 = ECU (engine) starts since the fault last occurred
  ```

- `0x55` is the **"no fault"** sentinel and is used as padding / end marker.
- A response may be prefixed with a `0xFF` + length leader:
  `(0xff)(length)(code)(starts)...` — `_strip_frame_prefix()` removes it.

### 4.1 Example

Raw response:

```
0xFF 0x04 0x13 0x00 0x08 0x03
```

Decoded with `decode_dtc_codes()` → `["13", "08"]`:

| Code | Starts | DTC Index entry                          |
|------|--------|------------------------------------------|
| `13` | `00`   | Engine misfire detected                  |
| `08` | `03`   | Engine crankshaft position (CKP) circuit |

`Fault.display_code` is the zero-padded uppercase hex string (`"%02X"`), used
for display and DB lookup.

> **Decoder caveat:** any trailing **odd byte** is treated as a truncated
> pair and ignored — this deliberately avoids reporting phantom faults from
> incomplete reads.

## 5. Retry / Backoff

`RetryController` implements exponential backoff **with jitter**
(`RetryConfig`: `base_delay_ms=100`, `max_retries=5`, `jitter_factor=0.3`):

```
delay_ms = base_delay_ms * 2^attempt ± (base_delay_ms * 2^attempt * jitter_factor * uniform(-1,1))
```

Example (jitter ±30%) for `base_delay_ms=100`:

| Attempt | nominal delay | range          |
|---------|---------------|----------------|
| 0       | 100 ms        | 58–142 ms      |
| 1       | 200 ms        | 75–196 ms      |
| 2       | 400 ms        | 130–330 ms     |

`should_retry()` returns `False` once `attempt_count >= max_retries`.

## 6. Errors

| Exception                 | Raised when                                          |
|---------------------------|------------------------------------------------------|
| `FrameError`              | base class for frame parsing errors                  |
| `TimestampExpiredError`   | frame older than the 60 s window (`age_seconds` attr)|
| `ReplayAttackError`       | duplicate signature seen in the session cache        |
| `SerialCommunicationError`| base serial error                                    |
| `SerialTimeoutError`      | serial op timed out                                  |
| `SerialWriteError`        | write failed                                         |
| `SerialReadError`         | read failed                                          |
| `ConnectionLostError`     | connection dropped unexpectedly                      |

## 7. Frame validation algorithm

```
validate_packet(data):
    if len(data) < 3: fail
    if xor(data[:-1]) != data[-1]: fail
    ok
```