#!/usr/bin/env python3
# coding=utf-8

# Arduino programmer for SPIDriver
#
# Connect to the ISP header like this:
#
#                +------+
#  (yellow) MISO | 1  2 | 3.3V (red)
#  (orange)  SCK | 3  4 | MOSI (green)
#  (purple)    A | 5  6 | GND  (black)
#                +------+
#
# Then load a hex file with:
#
#   ./atmega8.py foo.hex
#
# See Atmega328 datasheet section 31.8 for protocol details.
#

import sys

from spidriver import SPIDriver


class ConnectionError(Exception):
    pass


class AtMega:
    def __init__(self, s):
        self.s = s

    def pulse_reset(self):
        # +ve pulse on RESET
        self.s.seta(1)
        self.s.seta(0)

    def programming_enable(self):
        # Datasheet recommended method for getting into programming sync
        for i in range(10):
            self.pulse_reset()
            response = self.s.writeread(bytes([0xac, 0x53, 0, 0]))
            if response[2] == 0x53:
                return
            print(repr(response))
        raise ConnectionError

    def multifetch(self, insns):
        # Send insns, return last byte of each packet
        r = self.s.writeread(bytes(insns))
        return [r[i] for i in range(3, len(insns), 4)]

    def lohi(self, bb):
        (lo, hi) = self.multifetch(bb)
        return lo | (hi << 8)

    def read_program_memory(self, a):
        return self.lohi([0x20, a >> 8, a & 0xff, 0,
                          0x28, a >> 8, a & 0xff, 0])

    def read_fuses(self):
        return self.lohi([0x50, 0x00, 0, 0,
                          0x58, 0x08, 0, 0])

    def waitready(self):
        # Poll RDY/BSY until operation completes
        while True:
            (rdy,) = self.multifetch([0xf0, 0, 0, 0])
            if (rdy & 1) == 0:
                return

    def erase(self):
        self.s.write(bytes([0xac, 0x80, 0, 0]))
        self.waitready()

    def write_page(self, a, page):
        for i, v in enumerate(page):
            self.s.write(bytes([0x40, 0, i, v & 0xff]))
            self.s.write(bytes([0x48, 0, i, v >> 8]))
        self.s.write(bytes([0x4c, a >> 8, a & 0xff, 0]))
        self.waitready()

    def load(self, program):
        for i in range(0, len(program), 64):
            self.write_page(i, program[i:i + 64])

    def verify(self, program):
        for i, p in enumerate(program):
            assert self.read_program_memory(i) == p, ("Mismatch at offset %d" % i)

    def release(self):
        self.s.seta(1)
        self.s.detach()


def read_hex(filename):
    m = []

    def hexbyte(l, n):
        return int(l[2 * n + 1:2 * n + 3], 16)

    def hexword(l, n):
        return hexbyte(l, n) | (hexbyte(l, n + 1) << 8)

    for l in open(filename, "rt"):
        count = hexbyte(l, 0)
        for i in range(4, 4 + count, 2):
            m.append(hexword(l, i))
    # print("".join(["%04x " % w for w in m]))
    return m


if __name__ == '__main__':
    program = read_hex(sys.argv[2])
    s = SPIDriver(sys.argv[1])
    a = AtMega(s)
    a.programming_enable()
    a.erase()
    a.load(program)
    a.verify(program)
    a.release()
    print("Loaded and verified program %s" % sys.argv[2])
