#!/usr/bin/env python3
"""Exercise the SPIDriver Pico firmware over USB CDC.

This script does not assume a target device is connected; it validates the
host protocol, response lengths, and status format.  If MOSI is looped back
to MISO it also checks duplex data integrity.
"""

import os
import sys
import termios
import time
import tty

PORT = "/dev/ttyACM0"


def open_raw(port):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
    tty.setraw(fd)  # FULL raw: ICANON, ECHO, and IXON/XOFF handling off
    t = termios.tcgetattr(fd)
    t[6][termios.VMIN] = 0
    t[6][termios.VTIME] = 1  # 100 ms per read
    termios.tcsetattr(fd, termios.TCSANOW, t)
    os.set_blocking(fd, True)
    return fd


def drain(fd, timeout=0.5):
    end = time.time() + timeout
    while time.time() < end:
        d = os.read(fd, 256)
        if not d:
            time.sleep(0.01)


def status(fd):
    os.write(fd, b"?")
    data = b""
    for _ in range(100):
        d = os.read(fd, 80 - len(data) if len(data) < 80 else 1)
        data += d
        if len(data) >= 80:
            break
        time.sleep(0.01)
    return data[:80].decode(errors="replace").strip("[]"), len(data)


def echo(fd, b):
    os.write(fd, b"e" + bytes([b]))
    d = os.read(fd, 10)
    return d


def cmd(fd, data, expect_len=0, timeout=0.5):
    os.write(fd, data)
    if expect_len == 0:
        return b""
    out = b""
    end = time.time() + timeout
    while time.time() < end and len(out) < expect_len:
        out += os.read(fd, expect_len - len(out))
    return out


def expect(name, cond, detail=""):
    ok = "PASS" if cond else "FAIL"
    print(f"  {ok}: {name}{detail}")
    return cond


def main():
    print(f"Opening {PORT}")
    fd = open_raw(PORT)
    time.sleep(1.5)  # boot colorbar

    all_ok = True

    # 1. Status
    print("\n1. Status query")
    s, n = status(fd)
    all_ok &= expect("status length == 80", n >= 80, f" (got {n})")
    fields = s.split()
    all_ok &= expect("status has 10 fields", len(fields) == 10, f" ({len(fields)})")
    if len(fields) == 10:
        all_ok &= expect("product field", fields[0] == "spidriver1")
        all_ok &= expect("serial length 16", len(fields[1]) == 16)
        all_ok &= expect("cs bit == 1 (unselected)", fields[8] == "1")
    print("  status:", s.strip())

    # 2. Echo
    print("\n2. Echo")
    for b in (0x00, 0x11, 0x13, 0x55, 0xAA, 0xFF):  # incl. XON/XOFF
        d = echo(fd, b)
        all_ok &= expect(f"echo 0x{b:02x}", d == bytes([b]), f" got {d!r}")

    # 3. Select / unselect changes CS bit
    print("\n3. CS control")
    cmd(fd, b"s")
    time.sleep(0.05)
    s, _ = status(fd)
    fields = s.split()
    all_ok &= expect("CS low after select", fields[8] == "0")
    cmd(fd, b"u")
    time.sleep(0.05)
    s, _ = status(fd)
    fields = s.split()
    all_ok &= expect("CS high after unselect", fields[8] == "1")

    # 4. A / B control
    print("\n4. A/B control")
    cmd(fd, b"a\x01")
    time.sleep(0.05)
    s, _ = status(fd)
    fields = s.split()
    all_ok &= expect("A high", fields[6] == "1")
    cmd(fd, b"a\x00")
    cmd(fd, b"b\x01")
    time.sleep(0.05)
    s, _ = status(fd)
    fields = s.split()
    all_ok &= expect("A low + B high", fields[6] == "0" and fields[7] == "1")
    cmd(fd, b"b\x00")

    # 5. Duplex transfer lengths (A/B toggled during every transfer)
    print("\n5. Duplex transfers")
    patterns = [bytes(range(1, n + 1)) for n in (1, 2, 4, 8, 16, 32, 64)]
    loopback_ok = True
    for i, p in enumerate(patterns):
        cmd(fd, b"a" + bytes([i & 1]))  # A toggles every round
        cmd(fd, b"b" + bytes([(i >> 1) & 1]))  # B toggles every other round
        c = bytes([0x80 | (len(p) - 1)])
        d = cmd(fd, c + p, expect_len=len(p), timeout=1.0)
        all_ok &= expect(
            f"  duplex {len(p):2d}B len", len(d) == len(p), f" got {len(d)}"
        )
        if len(d) == len(p) and d != p:
            loopback_ok = False
    if loopback_ok:
        print("  (MOSI-MISO loopback detected: data matched)")
    else:
        print("  (MOSI not looped to MISO; only length checked)")

    # 6. Write-only transfers (A/B toggled during every transfer)
    print("\n6. Write-only transfers")
    for i, n in enumerate((1, 2, 8, 64)):
        cmd(fd, b"a" + bytes([i & 1]))
        cmd(fd, b"b" + bytes([(i >> 1) & 1]))
        c = bytes([0xC0 | (n - 1)]) + bytes(range(n))
        d = cmd(fd, c, expect_len=0, timeout=0.2)
        all_ok &= expect(f"  write {n:2d}B no response", d == b"", f" got {len(d)}B")

    # 7. Stress: many transactions (A/B toggled throughout)
    print("\n7. Stress: 100 duplex + status rounds")
    for i in range(100):
        cmd(fd, b"a" + bytes([i & 1]))
        cmd(fd, b"b" + bytes([(i >> 1) & 1]))
        c = bytes([0x81, i & 0xFF, (~i) & 0xFF])
        d = cmd(fd, c, expect_len=2, timeout=0.5)
        if len(d) != 2:
            all_ok &= expect(f"stress round {i}", False, f" got {len(d)}B")
            break
    else:
        all_ok &= expect("100 stress rounds", True)

    # 8. Final status
    print("\n8. Final status")
    s, n = status(fd)
    all_ok &= expect("final status length", n >= 80, f" ({n})")
    print(" ", s.strip())

    # 9. Display exercise: SPI traffic interleaved with A/B toggles
    print("\n9. Display exercise (SPI + A/B)")
    cmd(fd, b"s")
    cmd(fd, b"a\x01")  # A high
    d = cmd(fd, bytes([0x80, 0xDE]), expect_len=1)
    all_ok &= expect("  duplex 0xDE", len(d) == 1)
    cmd(fd, b"b\x01")  # B high
    d = cmd(fd, bytes([0x80, 0xAD]), expect_len=1)
    all_ok &= expect("  duplex 0xAD", len(d) == 1)
    cmd(fd, b"a\x00")  # A low
    d = cmd(fd, bytes([0x80, 0xBE]), expect_len=1)
    all_ok &= expect("  duplex 0xBE", len(d) == 1)
    cmd(fd, b"b\x00")  # B low
    d = cmd(fd, bytes([0x80, 0xEF]), expect_len=1)
    all_ok &= expect("  duplex 0xEF", len(d) == 1)
    cmd(fd, b"u")
    print("  A/B toggled during SPI traffic")

    os.close(fd)
    print("\n" + ("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
