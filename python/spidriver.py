"""USB SPI interfaces for SPIDriver, SPIDriver2, and SPIDriverQ."""

import json
import math
import operator
import os
from collections.abc import Iterable

import serial

__version__ = "2.0.1"
__all__ = ["SPIDriver"]


class _SPIDriverBase:
    """Serial transport, connection lifetime, and commands shared by all models."""

    def __init__(self, port="/dev/ttyUSB0", *, timeout=1, write_timeout=1):
        if hasattr(port, "read") and hasattr(port, "write"):
            self.ser = port
        else:
            self.ser = serial.Serial(
                os.fspath(port), 460800, timeout=timeout, write_timeout=write_timeout
            )
        try:
            self._write_all(b"@" * 64)
            while self.ser.in_waiting:
                self._read_exact(self.ser.in_waiting)
            for value in (0x55, 0x00, 0xFF, 0xAA):
                self._write_all(bytes((ord("e"), value)))
                reply = self._read_exact(1)[0]
                if reply != value:
                    raise OSError(
                        f"SPIDriver echo test failed: expected {value:#04x}, "
                        f"received {reply:#04x}"
                    )
            self.getstatus()
        except BaseException:
            self.close()
            raise

    def _write_all(self, data) -> None:
        data = memoryview(data).cast("B")
        while data:
            count = self.ser.write(data)
            if not count:
                raise TimeoutError("Timed out writing SPIDriver serial data")
            data = data[count:]

    def _read_exact(self, size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            chunk = self.ser.read(size - len(result))
            if not chunk:
                raise TimeoutError(
                    f"Timed out reading SPIDriver data ({len(result)}/{size} bytes)"
                )
            result.extend(chunk)
        return bytes(result)

    @staticmethod
    def _byte_data(data: Iterable[int]) -> bytes:
        # bytes(5) creates five zeroes; a scalar is not a transfer payload.
        if isinstance(data, int):
            raise TypeError("SPI data must be bytes or an iterable of byte values")
        return bytes(data)

    def detach(self) -> None:
        """Detach all signals, leaving them floating."""
        self._write_all(b"x")

    def sel(self) -> None:
        """Select the SPI device by asserting CS."""
        self._write_all(b"s")

    def unsel(self) -> None:
        """Unselect the SPI device by deasserting CS."""
        self._write_all(b"u")

    def read(self, l: int) -> bytes:  # noqa: E741 - retain the public keyword name
        """Read ``l`` bytes, clocking FF in single SPI mode. Does not change CS.

        On Q in 3-wire, dual, or quad mode, release the data lines for input.
        """
        size = operator.index(l)
        if size < 0:
            raise ValueError("Negative SPI read size")
        result = bytearray()
        for offset in range(0, size, 64):
            count = min(size - offset, 64)
            self._write_all(bytes((0x80 + count - 1,)) + b"\xff" * count)
            result.extend(self._read_exact(count))
        return bytes(result)

    def write(self, bb: Iterable[int]) -> None:
        """Write bytes or byte values to SPI without changing CS."""
        data = self._byte_data(bb)
        for offset in range(0, len(data), 64):
            chunk = data[offset : offset + 64]
            self._write_all(bytes((0xC0 + len(chunk) - 1,)) + chunk)

    def writeread(self, bb: Iterable[int]) -> bytes:
        """Transfer bytes or byte values, returning the same number of bytes.

        Does not change CS. On Q in 3-wire, dual, or quad mode this is
        receive-only: the transmit values are ignored.
        """
        data = self._byte_data(bb)
        result = bytearray()
        for offset in range(0, len(data), 64):
            chunk = data[offset : offset + 64]
            self._write_all(bytes((0x80 + len(chunk) - 1,)) + chunk)
            result.extend(self._read_exact(len(chunk)))
        return bytes(result)

    def _set_io_gpio(self, command: bytes, level: int) -> None:
        level = operator.index(level)
        if level not in (0, 1):
            raise ValueError("GPIO level must be 0 or 1")
        self._write_all(command + bytes((level,)))

    def seta(self, v: int) -> None:
        """Set the A signal to 0 or 1."""
        self._set_io_gpio(b"a", v)

    def setb(self, v: int) -> None:
        """Set the B signal to 0 or 1."""
        self._set_io_gpio(b"b", v)

    def getstatus(self) -> None:
        """Refresh the status attributes from the fixed 80-byte reply."""
        self._write_all(b"?")
        response = self._read_exact(80)
        try:
            if response[:1] != b"[" or response[-1:] != b"]":
                raise ValueError("Missing status delimiters")
            fields = response[1:-1].decode("ascii").split()
            product, serial_number, uptime, voltage, current, temp, a, b, cs, crc = (
                fields[:10]
            )
            mode = self._status_mode(fields)
            status = dict(
                product=product,
                serial=serial_number,
                uptime=int(uptime),
                voltage=float(voltage),
                current=float(current),
                temp=float(temp),
                a=int(a),
                b=int(b),
                cs=int(cs),
                ccitt_crc=int(crc, 16),
                mode=mode,
            )
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Malformed SPIDriver status: {response!r}") from exc
        self.__dict__.update(status)

    def close(self) -> None:
        """Close the serial connection. Does not change SPI or GPIO outputs."""
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self) -> str:
        return f"<{self.product} serial={self.serial} uptime={self.uptime}>"

    def _status_mode(self, fields: list[str]) -> int:
        """Original SPIDriver status has no mode field."""
        return 0


class _SPIDriver2Mixin:
    """SPI mode selection and status, shared by SPIDriver2 and SPIDriverQ.

    Requires the transport and status interface of _SPIDriverBase. The status
    hook cooperates with the next class in the MRO for the original hardware.
    """

    def setmode(self, m: int) -> None:
        """Set SPI mode 0, 1, 2, or 3. SPIDriver1 supports only mode 0.

        Q hardware SPI0 (width 11) supports only mode 0; firmware ignores
        requests for other modes in that width. Call getstatus() to read back.
        """
        m = operator.index(m)
        if m not in (0, 1, 2, 3):
            raise ValueError("SPI mode must be 0, 1, 2 or 3")
        if self.product == "spidriver1":
            if m != 0:
                raise OSError("SPIDriver1 supports only SPI mode 0")
        elif self.product in ("spidriver2", "spidriverq"):
            self._write_all(bytes((ord("m"), m)))
        else:
            raise OSError(f"Unrecognized SPIDriver product: {self.product!r}")

    def _status_mode(self, fields: list[str]) -> int:
        # During initialization, self.product has not been populated yet.
        if fields[0] in ("spidriver2", "spidriverq"):
            return int(fields[10])
        return super()._status_mode(fields)


class _SPIDriverQMixin:
    """Q-only commands, using the transport helpers of _SPIDriverBase.

    Each public operation checks the connected product before sending bytes.
    Mixins have no constructor; connection ownership stays in the base class.
    """

    def _require_q(self) -> None:
        if self.product != "spidriverq":
            raise NotImplementedError("This operation requires SPIDriverQ")

    def set_width(self, width: int) -> None:
        """Select 3-wire (0), SPI (1), dual (2), quad (4), or hardware SPI0 (11).

        3-wire uses IO0 for both directions: write() drives it; read() releases
        it. Like dual/quad, writeread() is read-only and ignores its transmit bytes.
        Deselect before switching between PIO and SPI0. Widths 0, 1, 2 and 4 keep
        the clock mode; 11 forces CPOL=CPHA=0. Value 0 selects bidirectional IO0.
        """
        self._require_q()
        width = operator.index(width)
        if width not in (0, 1, 2, 4, 11):
            raise ValueError("SPI width must be 0, 1, 2, 4 or 11")
        self._write_all(b"d\x0b" if width == 11 else f"d{width}".encode("ascii"))

    def set2(self, level: int) -> None:
        """Drive IO2 low (0) or high (1) in SPI/3-wire mode; ignored in quad."""
        self._require_q()
        self._set_io_gpio(b"2", level)

    def set3(self, level: int) -> None:
        """Drive IO3 low (0) or high (1) in SPI/3-wire mode; ignored in quad."""
        self._require_q()
        self._set_io_gpio(b"3", level)

    def set_speed(self, hz: int) -> None:
        """Set the requested SPI clock in Hz (up to 25 MHz); no reply."""
        self._require_q()
        hz = operator.index(hz)
        if not 1 <= hz <= 25_000_000:
            raise ValueError("SPI speed must be between 1 and 25000000 Hz")
        self._write_all(f"c{hz:08d}".encode("ascii"))

    def bulk_write(self, data) -> None:
        """TX-only SPI, in blocks of up to 65536 bytes. Does not change CS."""
        self._require_q()
        data = memoryview(data).cast("B")
        for offset in range(0, len(data), 65536):
            chunk = data[offset : offset + 65536]
            self._write_all(b"w" + (len(chunk) - 1).to_bytes(2, "big"))
            self._write_all(chunk)

    def bulk_read(self, size: int) -> bytes:
        """RX-only: transmit FF in SPI; release data in 3-wire/dual/quad. Keeps CS."""
        self._require_q()
        size = operator.index(size)
        if size < 0:
            raise ValueError("Negative bulk read size")
        result = bytearray()
        while size:
            count = min(size, 65536)
            self._write_all(b"r" + (count - 1).to_bytes(2, "big"))
            result.extend(self._read_exact(count))
            size -= count
        return bytes(result)

    def readings(self) -> dict:
        """Return raw INA226 voltage, shunt ADC and tare counts as a JSON dict."""
        self._require_q()
        self._write_all(b"%SPI%n")
        return self._read_json_object("INA226 readings")

    def build_info(self) -> dict:
        """Return firmware commit, dirty flag and display revision over USB."""
        self._require_q()
        self._write_all(b"%SPI%v")
        return self._read_json_object("firmware build info")

    def _read_json_object(self, description: str) -> dict:
        data = bytearray()
        for _ in range(65536):
            chunk = self.ser.read(1)
            if not chunk:
                raise TimeoutError(f"Timed out reading {description}")
            data.extend(chunk)
            try:
                result = json.loads(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(result, dict):
                raise ValueError(f"Expected a JSON object for {description}")
            return result
        raise ValueError(f"Oversized or malformed {description} JSON response")

    def tare(self) -> None:
        """Request a fresh zero-current measurement; does not save to flash."""
        self._require_q()
        self._write_all(b"%SPI%t")
        self.ser.flush()

    def save_config(self, timeout: float = 5) -> None:
        """Wait for any pending tare, save settings, and require a success reply."""
        self._require_q()
        if timeout is None or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Save timeout must be positive and finite")
        previous_timeout = self.ser.timeout
        try:
            self.ser.timeout = timeout
            self._write_all(b"%SPI%w")
            self.ser.flush()
            response = self.ser.read(1)
            if response == b"0":
                raise OSError("Failed to save SPIDriverQ settings")
            if not response:
                raise TimeoutError("Timed out saving SPIDriverQ settings")
            if response != b"1":
                raise OSError(f"Unexpected save response: {response!r}")
        finally:
            self.ser.timeout = previous_timeout

    def enter_sink(self) -> None:
        """Enter a CDC-only sink until hardware reset. No reply or escape command."""
        self._require_q()
        self._write_all(b"%SPI%>")

    def snapshot(self) -> bytes:
        """Return an opaque binary DeviceData capture for this firmware layout."""
        self._require_q()
        self._write_all(b"%SPI%s")

        size = int.from_bytes(self._read_exact(2), "big")
        return self._read_exact(size)

    def display_state(self, state: bytes) -> None:
        """Upload a 440-byte DeviceData capture and freeze it on the LCD.

        Use snapshot() or spidriverq_sim.DeviceData.to_bytes() for the payload.
        The layout must match this firmware. Does not drive SPI or GPIO.
        After an interrupted upload, reset before sending more commands.
        """
        self._require_q()
        state = memoryview(state).cast("B")
        if len(state) != 440:
            raise ValueError("DeviceData state must contain exactly 440 bytes")
        self._write_all(b"%SPI%S")
        size_bytes = bytearray()
        while len(size_bytes) < 2:
            data = self.ser.read(2 - len(size_bytes))
            if not data:
                raise TimeoutError(
                    "Timed out starting display upload; firmware may not support it"
                )
            size_bytes.extend(data)
        if int.from_bytes(size_bytes, "big") != len(state):
            raise ValueError(
                "DeviceData layout size mismatch; reset the device before continuing"
            )
        self._write_all(state)
        response = self.ser.read(1)
        if not response:
            raise TimeoutError(
                "Timed out uploading display state; reset before continuing"
            )
        if response == b"0":
            raise ValueError("Firmware rejected invalid DeviceData state")
        if response != b"1":
            raise OSError(f"Unexpected display upload response: {response!r}")

    def screenshot(self, slot: int = 0) -> None:
        """Show a saved scene until reset. Unpopulated slots leave the state alone."""
        self._require_q()
        slot = operator.index(slot)
        if not 0 <= slot <= 9:
            raise ValueError("Screenshot slot must be between 0 and 9")
        self._write_all(b"%SPI%" + bytes((ord("0") + slot,)))

    def lcd_test_pattern(self) -> None:
        """Freeze a coordinate/ruler pattern for measuring the visible LCD area."""
        self._require_q()
        self._write_all(b"%SPI%T")

    def lcd_test_card(self) -> None:
        """Freeze a flat gray card with 0..15 RGB/white ramps and a white border."""
        self._require_q()
        self._write_all(b"%SPI%C")

    def lcd_test_loop(self) -> None:
        """Repeat LCD reset, initialization, red fill and 250 ms wait. No reply."""
        self._require_q()
        self._write_all(b"%SPI%L")

    def enter_bootloader(self) -> None:
        """Request a UF2/BOOTSEL reboot. No reply."""
        self._require_q()
        self._write_all(b"%SPI%b")


class SPIDriver(_SPIDriverQMixin, _SPIDriver2Mixin, _SPIDriverBase):
    """Connect to any SPIDriver product.

    ``port`` is a serial port name (or path), or an open serial-compatible
    transport with read, write, in_waiting, timeout, flush, and close support.
    The driver closes either kind of transport on initialization failure,
    :meth:`close`, or context-manager exit. ``timeout`` and ``write_timeout``
    apply only when opening a port; supplied transports retain their settings.

    Status attributes are refreshed by :meth:`getstatus`: ``product``,
    ``serial``, ``uptime`` (seconds), ``voltage`` (V), ``current`` (mA),
    ``temp`` (degrees C), ``a``, ``b``, ``cs``, ``ccitt_crc``, and ``mode``.
    Q-only methods reject other products before writing to the device.
    """
