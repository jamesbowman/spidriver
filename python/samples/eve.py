#!/usr/bin/env python3

from spidriver import SPIDriver
import math
import random
import time
import sys
import binascii
from crc16pure import crc16xmodem

from Eve import Eve

def rnd(n):
    return random.randrange(n)

s = SPIDriver()
def hostcmd(x):
    s.sel()
    s.write(bytes([x, 0, 0]))
    s.unsel()
    time.sleep(.100)

while 0:
    s.unsel()
    s.write(bytes([0x55]))
while 0:
    hostcmd(0x00)
    # hostcmd(0x68)
    time.sleep(.300)

    print
    for j in range(100000):
        s.sel()
        m = [0x30, 0x20, 0x00]
        s.write(bytes(m))
        r = s.read(2)
        # print(" ".join(["%02x" % x for x in r]))
        assert r == bytes([0x42, 0x7c])
        s.unsel()
        # time.sleep(.1)

def pinwheels(s, e):
    def polar(th, r):
        x = int(16 * (240 + math.cos(th) * r))
        y = int(16 * (136 + math.sin(th) * r))
        e.Vertex2f(x, y)

    t = 0
    for cycle in range(999999):
        e.Clear()
        e.cmd_text(240, 136, 27, e.OPT_CENTER, time.ctime())
        # s.getstatus()
        # e.cmd_text(240, 150, 29, e.OPT_CENTER, "%.1f C" % s.temp)
        e.LineWidth(10)
        e.ColorRGB(0xff, 0xc0, 0x80)
        e.BlendFunc(e.SRC_ALPHA, e.ONE)
        e.Begin(e.LINE_STRIP)
        for i in range(48):
            polar(t + ((i * 17) * 2 * math.pi / 47), 245)
        e.swap()
        e.finish()
        print(cycle)
        t += .01

if __name__ == '__main__':
    e = Eve(s)
    e.initialize()
    e.cmd_regwrite(e.REG_GPIO, 0x80)
    e.Clear()
    e.swap()
    e.finish()
    e.cmd_regwrite(e.REG_SWIZZLE, 3)
    e.cmd_regwrite(e.REG_PCLK_POL, 1)
    e.cmd_regwrite(e.REG_PCLK, 6)
    e.cmd_setrotate(2)

    e.cmd_setbitmap(0, e.RGB565, 480, 200)
    sz = 480 * 200 * 2

    pinwheels(s, e)

    while 0:
        e.cmd_regwrite(e.REG_PWM_HZ, 10000)
        e.cmd_regwrite(e.REG_PWM_DUTY, 0)
        time.sleep(3)
        e.cmd_regwrite(e.REG_PWM_DUTY, 128)
        time.sleep(3)

    cycle = 0

    pattern = bytes([rnd(256) for i in range(2000)])
    while 1:
        s.getstatus()
        print("%d: %8d %.3f V   %4d mA   %.1f C   %04x" % (cycle, s.uptime, s.voltage, s.current, s.temp, s.debug))
        cycle += 1

        for i in range(10):
            s.setb(i & 1)
            e.cmd_memwrite(0, len(pattern))
            e.c(pattern)

        s.seta(1)
        assert pattern == (e.rdbytes(0, len(pattern)))
        s.seta(0)

    t1 = time.time() + float(sys.argv[1])
    while time.time() < t1:
        s.getstatus()
        print("%d: %.3f V   %4d mA   %.1f C   %04x" % (cycle, s.voltage, s.current, s.temp, s.debug))
        cycle += 1

        s.seta(1)
        e.cmd_memwrite(0, sz)
        pattern = bytes([rnd(256) for i in range(sz)])
        s.seta(0)
        e.c(pattern)
        e.Clear()
        e.cmd_text(240, 0, 30, Eve.OPT_CENTERX, time.ctime())
        e.Vertex2ii(0, 72, 0, 0)
        e.swap()
        e.cmd_memcrc(0, sz, 0)
        assert (e.result(1) == binascii.crc32(pattern))
