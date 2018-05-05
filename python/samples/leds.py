#!/usr/bin/env python3

import colorsys

from spidriver import SPIDriver

if __name__ == '__main__':
    s = SPIDriver()
    L = 300

    blanking = [0] * ((L + 31) // 32)
    d = [0x80,0x80,0x80] * L
    s.write(blanking + d + blanking)

    rainbow = sum([colorsys.hsv_to_rgb(float(i) / L, 1, 1) for i in range(L)], ())
    rainbow = [0x80 + int(127 * v) for v in rainbow]
    while True:
        s.write(rainbow + blanking)
        rainbow = rainbow[3:] + rainbow[:3]
