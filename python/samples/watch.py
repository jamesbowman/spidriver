#!/usr/bin/env python3

from spidriver import SPIDriver
import random
import time
import sys
from crc16pure import crc16xmodem

# print(hex(crc16xmodem(bytes([0xaa, 0xbb, 0xcc]), 0xffff)))

def rnd(n):
    return random.randrange(n)

if __name__ == '__main__':
    s = SPIDriver()
    while 1:
        s.getstatus()
        print("%.3f V   %4d mA   %.1f C   %04x" % (s.voltage, s.current, s.temp, s.debug))
