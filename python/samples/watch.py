#!/usr/bin/env python3
# coding=utf-8
import random
import time

from spidriver import SPIDriver


# print(hex(crc16xmodem(bytes([0xaa, 0xbb, 0xcc]), 0xffff)))

def rnd(n):
    return random.randrange(n)


if __name__ == '__main__':
    s = SPIDriver()

    u = s.uptime
    while s.uptime == u:
        s.getstatus()

    t0 = time.time()
    d0 = s.uptime
    while 1:
        s.getstatus()
        du = s.uptime - d0  # device uptime
        tu = int(time.time() - t0)  # true uptime
        fastness = du - tu
        print("%9d   %.3f V   %4d mA   %.1f C   %04x  fast=%d" % (tu, s.voltage, s.current, s.temp, s.ccitt_crc, fastness))
        time.sleep(10)
