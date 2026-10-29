"""
OpenGonsult - Serial Communication Adapter
Nissan CONSULT-I protocol serial communication layer with pyserial integration.

Handles USB (FTDI, CH340, PL2303) and Bluetooth serial connections with:
- Async command queue for race-condition-free I/O
- Connection health monitoring and auto-reconnect
- Proper timeout handling and error recovery
"""

import asyncio
import logging
from typing import Optional, Callable, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    import serial
except ImportError:
    raise ImportError("pyserial is required. Install with: pip install pyserial")

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class SerialCommunicationError(Exception):
    """Base exception for serial communication errors."""
    pass


class SerialTimeoutError(SerialCommunicationError):
    """Exception raised when a serial operation times out."""
    pass


class SerialWriteError(SerialCommunicationError):
    """Exception raised when a write operation fails."""
    pass


class SerialReadError(SerialCommunicationError):
    """Exception raised when a read operation fails."""
    pass


class ConnectionLostError(SerialCommunicationError):
    """Exception raised when the serial connection is unexpectedly lost."""
    pass


# ============================================================================
# Core Types
# ============================================================================

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class SerialConfig:
    port: str = "/dev/ttyUSB0"
    baud_rate: int = 115200
    bytesize: int = 8
    parity: str = "N"
    stopbits: float = 1.0
    timeout: float = 1.0
    auto_reconnect: bool = True
    reconnect_delay_s: float = 2.0
    heartbeat_interval_s: float = 5.0


@dataclass
class SerialCommand:
    command_type: str  # 'write', 'read', 'read_raw', 'flush'
    data: bytes = b''
    callback: Optional[Callable[[Any], None]] = None
    timeout: Optional[float] = None
    result_queue: asyncio.Queue = field(default_factory=asyncio.Queue, repr=False)


# ============================================================================
# Command Queue - Serializes all I/O to prevent race conditions
# ============================================================================

class SerialOperationQueue:
    """FIFO queue that serializes ALL serial operations through a single worker.
    Prevents race conditions from concurrent read/write/transaction sequences."""

    def __init__(self):
        self._queue: asyncio.Queue[SerialCommand] = asyncio.Queue(maxsize=100)
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self, adapter: "SerialAdapter") -> bool:
        if not self._running:
            async with self._lock:
                if not self._running:
                    self._running = True
                    self._worker_task = asyncio.create_task(
                        self._process_commands(adapter)
                    )
        return True

    async def stop(self) -> bool:
        self._running = False
        if self._worker_task:
            try:
                await asyncio.wait_for(asyncio.shield(self._worker_task), timeout=2.0)
            except (asyncio.TimeoutError, Exception):
                pass  # Task may already be done/cancelled - OK during shutdown
        return not self._running

    async def enqueue_command(self, command: SerialCommand) -> Any:
        if not self._running:
            raise RuntimeError("Serial queue is not running")
        await self._queue.put(command)
        timeout = command.timeout or 5.0
        try:
            return await asyncio.wait_for(command.result_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Serial operation timed out after {timeout}s")

    async def _process_commands(self, adapter: "SerialAdapter"):
        while self._running:
            try:
                command = await asyncio.wait_for(
                    self._queue.get(), timeout=10.0
                )
            except asyncio.TimeoutError:
                continue  # Periodic check to allow shutdown

            try:
                if command.command_type == "write":
                    result = await asyncio.to_thread(
                        self._perform_write, adapter, command.data
                    )
                elif command.command_type in ("read", "read_raw"):
                    timeout_s = command.timeout or 1.0
                    try:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(
                                adapter._port.read,
                                size=adapter._port.in_waiting or 4096,
                            )
                            if adapter._port and adapter._port.in_waiting > 0
                            else asyncio.to_thread(
                                adapter._port.read,
                                size=1,
                            ),
                            timeout=timeout_s * 2,
                        )
                    except (SerialTimeoutError, TimeoutError):
                        result = b""
                elif command.command_type == "flush":
                    await asyncio.to_thread(self._perform_flush, adapter)
                    result = True
                else:
                    raise ValueError(f"Unknown serial command type: {command.command_type}")

                await command.result_queue.put(result)
                logger.debug(f"Completed {command.command_type} successfully")

            except Exception as e:
                logger.error(f"Error processing serial command: {e}", exc_info=True)
                try:
                    await command.result_queue.put((False, str(e)))
                except asyncio.QueueFull:
                    pass  # Queue may be closed during shutdown

    @staticmethod
    def _perform_write(adapter: "SerialAdapter", data: bytes) -> Tuple[bool, int]:
        try:
            written = adapter._port.write(data)
            return (True, written if isinstance(written, int) else len(data))
        except serial.SerialException as e:
            raise SerialWriteError(f"Serial write failed: {e}") from e

    @staticmethod
    def _perform_flush(adapter: "SerialAdapter") -> bool:
        try:
            adapter._port.reset_output_buffer()
            adapter._port.reset_input_buffer()
            return True
        except serial.SerialException as e:
            raise SerialCommunicationError(f"Serial flush failed: {e}") from e


# ============================================================================
# Main Serial Adapter
# ============================================================================

class SerialAdapter:
    """Handles serial communication with the CONSULT-I adapter.
    Supports USB (FTDI, CH340) and Bluetooth RS232 adapters via pyserial."""

    def __init__(self, config: Optional[SerialConfig] = None):
        self.state = ConnectionState.DISCONNECTED
        self.config = config or SerialConfig()
        self._port: Optional[serial.Serial] = None
        self._queue = SerialOperationQueue()
        self._reconnect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._disconnect_callbacks: list[Callable] = []

    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED and self._port is not None

    async def connect(self, config: Optional[SerialConfig] = None) -> bool:
        if config:
            self.config = config

        if self.is_connected:
            await self.disconnect()

        self.state = ConnectionState.CONNECTING

        try:
            self._port = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                timeout=self.config.timeout,
            )

            # Small delay to let the hardware settle (FTDI/CH340 need this)
            await asyncio.sleep(0.2)

            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to {self.config.port} @ {self.config.baud_rate}")

            # Start background workers
            await self._queue.start(self)
            if self.config.auto_reconnect:
                self._reconnect_task = asyncio.create_task(
                    self._monitor_connection()
                )
            if self.config.heartbeat_interval_s > 0:
                self._heartbeat_task = asyncio.create_task(
                    self._send_heartbeats()
                )

            return True

        except serial.SerialException as e:
            self.state = ConnectionState.ERROR
            logger.error(f"Failed to connect to {self.config.port}: {e}")
            raise ConnectionError(f"Connection failed: {e}") from e

    async def disconnect(self) -> None:
        # Set a flag so auto-reconnect stops trying
        self.config.auto_reconnect = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        await self._queue.stop()

        if self._port and self._port.is_open:
            try:
                self._port.close()
            except Exception:
                pass

        self.state = ConnectionState.DISCONNECTED
        self._port = None
        logger.info("Disconnected from serial device")

        for cb in self._disconnect_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb()
                else:
                    cb()
            except Exception as e:
                logger.error(f"Disconnect callback error: {e}")

    def on_disconnect(self, callback: Callable) -> None:
        self._disconnect_callbacks.append(callback)

    async def write(self, data: bytes, timeout: Optional[float] = None) -> Tuple[bool, int]:
        if not self.is_connected:
            raise ConnectionError("Not connected")
        cmd = SerialCommand(command_type="write", data=data, timeout=timeout)
        return await self._queue.enqueue_command(cmd)

    async def read(self, size: Optional[int] = None, timeout: Optional[float] = None) -> bytes:
        if not self.is_connected:
            raise ConnectionError("Not connected")
        cmd = SerialCommand(command_type="read_raw", data=b"", timeout=timeout)
        return await self._queue.enqueue_command(cmd)

    async def flush(self) -> bool:
        if not self.is_connected:
            raise ConnectionError("Not connected")
        cmd = SerialCommand(command_type="flush")
        return await self._queue.enqueue_command(cmd)

    # --- Background workers ---

    async def _monitor_connection(self):
        """Periodically check if the serial port is still alive."""
        while True:
            try:
                await asyncio.sleep(1.0)
                if not self.is_connected:
                    break
                # Quick check: is the port still open?
                if not self._port or not self._port.is_open:
                    logger.warning("Serial port closed unexpectedly")
                    self.state = ConnectionState.ERROR
                    await self.disconnect()
                    if self.config.auto_reconnect:
                        await self._auto_reconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")

    async def _send_heartbeats(self):
        """Send minimal data to keep the connection alive."""
        while True:
            try:
                await asyncio.sleep(self.config.heartbeat_interval_s)
                if not self.is_connected:
                    break
                # Send a dummy byte through the command queue to verify the
                # port is responsive without racing with other I/O.
                try:
                    await self.write(b'\x00')
                except Exception:
                    pass
            except (SerialTimeoutError, TimeoutError):
                logger.warning("Heartbeat timeout detected")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _auto_reconnect(self):
        """Attempt to reconnect after unexpected disconnect."""
        delay = self.config.reconnect_delay_s
        while self.config.auto_reconnect:
            try:
                logger.info(f"Attempting auto-reconnect in {delay}s...")
                await asyncio.sleep(delay)
                if self.is_connected:
                    break  # Already reconnected elsewhere
                await self.connect()
                delay = self.config.reconnect_delay_s  # Reset on success
            except Exception as e:
                logger.error(f"Auto-reconnect failed: {e}")
                delay *= 2  # Exponential backoff for reconnect attempts
                if delay > 30:
                    delay = 30

    async def transaction(self, command: bytes,
                          expected_length: int = None) -> bytes:
        """Send a command and read the response. Convenience wrapper."""
        success, written = await self.write(command)
        if not success:
            raise SerialWriteError("Command write failed")

        # Read response - wait for expected data or timeout
        await asyncio.sleep(0.1)  # Let ECU process and respond

        if expected_length:
            result = await self.read(size=expected_length, timeout=self.config.timeout * 3)
        else:
            result = await self.read(timeout=self.config.timeout * 2)

        return result

    @staticmethod
    def detect_ports() -> list[str]:
        """Detect available serial ports using pyserial."""
        try:
            from serial.tools.list_ports import comports
            return [port.device for port in comports()]
        except ImportError:
            # Fallback: check common Linux paths
            import glob
            ports = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
            if not ports:
                ports.append("/dev/rfcomm0")  # Bluetooth RFCOMM fallback
            return ports

    @property
    def available_ports(self) -> list[str]:
        """Alias for detect_ports."""
        return self.detect_ports()
