# OpenGonsult API Reference

Hand-written reference for the public APIs of the OpenGonsult libraries.
Signatures are derived from the source docstrings. Each module below is also
the authoritative doc source — read the docstrings for the full detail.

---

## `ecu.dtc` — DTC decoding

Diagnostic trouble code reading/decoding for the CONSULT-I protocol.

| Symbol | Description |
|--------|-------------|
| `NO_FAULT = 0x55` | sentinel meaning "no fault", used as padding |
| `FRAME_START = 0xFF` | optional frame-start leader byte |
| `@dataclass Fault(code: int, starts: int = 0)` | one decoded fault |
| `Fault.display_code -> str` | zero-padded `"%02X"` string (stable, sortable) |
| `Fault.is_no_fault -> bool` | true if code is `NO_FAULT` |
| `DTC_INDEX: Dict[int, str]` | numeric code → description (starter set) |
| `decode_faults(data: bytes) -> List[Fault]` | decode raw response bytes into faults |
| `decode_dtc_codes(data: bytes) -> List[str]` | display strings for stored faults |
| `describe(code: int) -> str` | DTC index description or fallback text |
| `lookup(code: int) -> Tuple[str, str]` | `(display_code, description)` |

Decoding walks `(code, starts)` pairs, skips `0x55`, strips an optional
`(0xff)(len)` prefix, and ignores a trailing odd byte.

## `ecu.sensors` — live sensor processing

| Symbol | Description |
|--------|-------------|
| `SensorType(Enum)` | `ENGINE_RPM, VEHICLE_SPEED, THROTTLE_POSITION, COOLANT_TEMP, INTAKE_AIR_TEMP, MAF_SENSOR, OXYGEN_SENSOR, BATTERY_VOLTAGE` |
| `@dataclass SensorReading(sensor_type, value, unit, raw_value, quality="good", timestamp=now)` | a time-stamped reading |
| `DashboardDataProcessor(graph_history_seconds=120)` | aggregates readings; stable smoothed gauges + rolling history + observer hooks |
| `.subscribe(callback: Callable[[str, float, float], None]) -> None` | register an observer invoked as `fn(key, epoch_seconds, value)` per reading (best-effort) |
| `.unsubscribe(callback) -> None` | remove an observer |
| `.add_reading(sensor_type: str \| SensorType, reading: SensorReading) -> None` | ingest a reading (updates gauges, history, observers) |
| `.get_history(sensor_type) -> List[Tuple[float, float]]` | copy of `[(epoch, value), ...]` for a sensor |
| `.get_current_value(sensor_type) -> Optional[float]` | simple moving average (last 5) for stable gauges |
| `.register_display_callback(callback: Callable[[Dict[str, float]], None])` | UI update hook for gauge refreshes |

## `ecu/ecu_db` — ECU, sensor and DTC database

| Symbol | Description |
|--------|-------------|
| `@dataclass SensorDefinition(name, unit, min_value, max_value, scaling_factor=1.0, offset=0.0)` | sensor metadata |
| `SensorDefinition.decode(raw_value) -> float` | `raw * scaling_factor + offset` |
| `@dataclass DTCDefinition(code, description, severity, possible_causes, recommended_actions)` | DTC metadata (`severity` ∈ `"warning"\|"critical"\|"info"`) |
| `@dataclass ECUDefinition(name, id_code, protocol_version, sensors, dtc_codes)` | an ECU |
| `ECUDatabase()` | registry of Nissan ECUs, sensors, DTCs |
| `.get_ecu(id_code: int) -> Optional[ECUDefinition]` | look up by ECU id |
| `.get_sensor_definition(ecu_id, sensor_name) -> Optional[SensorDefinition]` | sensor for an ECU (`SensorDefinition` uses new API; sensors without a definition fall back to numeric decode) |
| `.get_dtc_definition(dtc_code: str) -> Optional[DTCDefinition]` | DTC by code string (falls back to a numeric DTC index for simulator codes) |
| `.list_ecus() -> List[str]` / `.list_sensors(ecu_id) -> List[str]` / `.list_dtc_codes(ecu_id) -> List[str]` | listing helpers |

## `protocol/consult.py` — CONSULT-I protocol

| Symbol | Description |
|--------|-------------|
| `MAX_TIMESTAMP_WINDOW_SECONDS = 60` | frames older than this are expired |
| `REPLAY_CACHE_SIZE = 1024` | max cached signatures |
| `ConnectionState(Enum)` | `INIT, CONNECTING, ESTABLISHED, DISCONNECTED, RECONNECTING` |
| `FrameError(Exception)` | base parse error |
| `TimestampExpiredError(message, age_seconds)` | expired frame (`age_seconds` attr) |
| `ReplayAttackError(FrameError)` | duplicate signature in window |
| `@dataclass FrameMetadata(timestamp=now)` | metadata with `age_seconds` |
| `@dataclass FramedFrame(payload=b"", timestamp=now, signature="", metadata=None)` | envelope w/ `sha256(payload+ts)[:32]` signature |
| `FramedFrame.validate_timestamp(max_age_seconds=60) -> bool` | raises `TimestampExpiredError` when stale |
| `FramedFrame.validate_signature_no_replay(signature_cache) -> bool` | raises `ReplayAttackError` on duplicate |
| `FramedFrame.validate_frame_complete(signature_cache=None) -> bool` | TIMING → SIGNATURE → CONTENT |
| `@dataclass ConsultPacket(header=b"\\x02", payload=b"", framed_frame=None)` | base packet; `to_bytes()` appends XOR checksum |
| `ConsultPacket.timestamp` / `.get_expiry_time(...)` | freshness helpers |
| `@dataclass RequestPacket(mode=0x81)` | `.encode(sub_function, data=None) -> bytes` |
| `@dataclass ResponsePacket(response_code=0x41)` | `.decode() -> (sub_function, data)` |
| `@dataclass DiagnosticPacket` | `.encode_diagnostic_request(diagnostic_mode, address_high, address_low, length) -> bytes` |
| `RetryConfig(base_delay_ms=100, max_retries=5, jitter_factor=0.3)` | backoff config |
| `RetryController(config=None)` | `.calculate_delay_ms(attempt) -> float`, `.should_retry() -> bool` |
| `calculate_checksum(data) -> int` | XOR checksum |
| `validate_packet(packet_data, timestamp_cache=None) -> bool` | checksum + length check |
| `format_hex(data) -> bytes` | `"01 0A ..."` hex string |

See `docs/PROTOCOL_SPEC.md` for the wire-format details.

## `serial/adapter.py` — async serial I/O

| Symbol | Description |
|--------|-------------|
| `SerialCommunicationError(Exception)` | base serial error |
| `SerialTimeoutError` / `SerialWriteError` / `SerialReadError` / `ConnectionLostError` | specific errors |
| `SerialConfig(port="/dev/ttyUSB0", baud_rate=115200, bytesize=8, parity="N", stopbits=1.0, timeout=1.0, auto_reconnect=True, reconnect_delay_s=2.0, heartbeat_interval_s=5.0)` | connection config |
| `SerialCommand(command_type, data=b"", callback=None, timeout=None, result_queue=None)` | tagged queue entry |
| `SerialOperationQueue` | FIFO worker serializing all I/O; `.start(adapter)`, `.stop()`, `.enqueue_command(cmd)` |
| `SerialAdapter(config=None)` | main adapter |
| `SerialAdapter.is_connected() -> bool` | connected flag |
| `SerialAdapter.on_disconnect(callback)` | register disconnect hook |
| `SerialAdapter.detect_ports() -> list[str]` | static port detection |
| `SerialAdapter.available_ports() -> list[str]` | cached/refreshed port list |

## `sessionrec` — session recording & replay

Namedtuple sample: `SessionSample(timestamp: float, sensor: str, value: float)`
with `SESSION_HEADERS = ["timestamp", "sensor", "value"]`.

| Symbol | Description |
|--------|-------------|
| `write_csv(path, samples)` / `write_sqlite(path, samples)` / `write_json(path, samples)` | write an iterable of `SessionSample` |
| `load_samples_csv(path)` / `load_samples_sqlite(path)` / `load_samples_json(path)` | read back `List[SessionSample]` |
| `SessionLogger(processor)` | records live `add_reading` samples best-effort |
| `SessionLogger.start()` / `.stop() -> Optional[List[SessionSample]]` / `.reset()` | lifecycle |
| `SessionLogger.is_recording()` / `.start_time()` / `.sample_count()` / `.elapsed_seconds()` | status |
| `SessionLogger.sensors() -> Dict[str, int]` / `.samples() -> List[SessionSample]` | buffered data |
| `SessionLogger.save(path, fmt=None) -> str` | write to CSV/SQLite/JSON (inferred from extension) |
| `SessionReplayer(processor)` | feeds recorded sessions back into a processor |
| `SessionReplayer.load(path)` / `.source_path()` / `.is_loaded()` / `.duration_seconds()` | setup |
| `SessionReplayer.play()` / `.pause()` / `.stop()` / `.seek(seconds)` | transport control |
| `SessionReplayer.is_playing()` / `.position_seconds()` / `.at_end()` | status |
| `SessionReplayer.pump()` | advance playback (call from a timer) |
| `PlaybackError(RuntimeError)` | raised on replay problems |

## `graphs/sensor_graph.py` — GTK4 graphing

| Symbol | Description |
|--------|-------------|
| `plot_xy(t, v, window_start, window_seconds, y_min, y_max, plot_x0, plot_y0, plot_width, plot_height) -> (x, y)` | pure math: time/value → Cairo pixel coords (y inverted), GTK/cairo-free, unit-testable |
| `SensorGraphWidget(data_processor=None, config_file=None)` | full graph widget (toogles, zoom/pan, CSV export, record/session/replay UI) |
| `SensorGraphWidget.set_data_processor(processor)` | attach a data source |
| `SensorGraphWidget.destroy()` | clean up timers/handlers |
| `SENSOR_COLORS` / `SENSOR_LABELS` / `SENSOR_UNITS` | per-sensor presentation maps |
## `ecu.active_tests` — active tests / ECU control

| Symbol | Description |
|--------|-------------|
| `CONSULT_CMD_ACTIVATE = 0x0A` | activation command mode byte |
| `ACTIVE_POWER_BALANCE = 0x88` | power-balance activation type |
| `ACTIVE_FUEL_PUMP_RELAY = 0x89` | fuel-pump relay activation type |
| `ACTIVE_SELF_LEARN_CLEAR = 0x8B` | clear self-learn activation type |
| `power_balance_command(cylinders_off=0) -> bytes` | build a power-balance command |
| `fuel_pump_command(on=True) -> bytes` | fuel-pump relay on/off |
| `clear_self_learn_command() -> bytes` | clear learned trim values |
| `rom_read_command(addresses) -> bytes` | read ROM bytes |
| `ActiveTestController(sender=None)` | high-level helper grouping operations |

## `ecu.monitoring` — monitoring set

| Symbol | Description |
|--------|-------------|
| `MonitoringSet(sensors=None)` | ordered, de-duplicated sensor set |
| `.add(sensor) / .remove(sensor) / .move(sensor, index)` | mutate the set |
| `.to_config() / .from_config(config)` | persist/restore |
