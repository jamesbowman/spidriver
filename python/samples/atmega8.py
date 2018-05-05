#!/usr/bin/env python3

import sys
import time

from spidriver import SPIDriver

class ConnectionError(Exception):
    pass

def pulse_reset(s):
    # +ve pulse on RESET
    s.seta(1)
    s.seta(0)

def programming_enable(s):
    for i in range(10):
        pulse_reset(s)
        response = s.writeread([0xac, 0x53, 0, 0])
        if response[2] == 0x53:
            return
    raise ConnectionError

def multifetch(s, insns):
    r = s.writeread(insns)
    return [r[i] for i in range(3, len(insns), 4)]
    
def lohi(s, bb):
    (lo, hi) = multifetch(s, bb)
    return lo | (hi << 8)

def read_program_memory(s, a):
    return lohi(s, [0x20, a >> 8, a & 0xff, 0,
                    0x28, a >> 8, a & 0xff, 0])

def read_fuses(s):
    return lohi(s, [0x50, 0x00, 0, 0,
                    0x58, 0x08, 0, 0])

def erase(s):
    s.write([0xac, 0x80, 0, 0])
    time.sleep(.0105)

def write_page(s, a, page):
    for i,v in enumerate(page):
        s.write([0x40, 0, i, v & 0xff])
        s.write([0x48, 0, i, v >> 8])
    s.write([0x4c, a >> 8, a & 0xff, 0])
    time.sleep(.1)

def read_hex(filename):
    for l in open(filename, "rt"):
        print(l)

if __name__ == '__main__':
    program = read_hex(sys.argv[1])

    s = SPIDriver()
    programming_enable(s)
    erase(s)
    write_page(s, 64, range(128))
    print("Fuses: %04x" % read_fuses(s))
    # Fuses d9ff
    for i in range(140):
        print("%04x: %04x" % (i, read_program_memory(s, i)))
