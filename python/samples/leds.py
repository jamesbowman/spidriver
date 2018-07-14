#!/usr/bin/env python3
# coding=utf-8
import colorsys
import sys

from spidriver import SPIDriver

if __name__ == '__main__':
    s = SPIDriver(sys.argv[1])
    L = 300

    blanking = [0] * ((L + 31) // 32)
    s.write(blanking + [0x80, 0x80, 0x80] * L + blanking)

    rainbow = sum([colorsys.hsv_to_rgb(float(i) / L, 1, 1) for i in range(L)], ())
    rainbow = [int(128 + 127 * v) for v in rainbow]
    while True:
        s.write(rainbow + blanking)
        rainbow = rainbow[3:] + rainbow[:3]
