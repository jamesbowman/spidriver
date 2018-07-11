#!/usr/bin/env python3
# coding=utf-8
import math
import sys
import time

from Eve import Eve
from spidriver import SPIDriver

if __name__ == '__main__':
    if len(sys.argv) > 1:
        s = SPIDriver(sys.argv[1])
    else:
        s = SPIDriver()
    e = Eve(s)
    e.initialize()


    def polar(th, r):
        x = int(16 * (240 + math.cos(th) * r))
        y = int(16 * (136 + math.sin(th) * r))
        e.Vertex2f(x, y)


    t = 0
    for cycle in range(999999):
        e.Clear()
        e.cmd_text(240, 136, 27, e.OPT_CENTER, time.ctime())
        e.LineWidth(10)
        e.ColorRGB(0xff, 0xc0, 0x80)
        e.BlendFunc(e.SRC_ALPHA, e.ONE)
        e.Begin(e.LINE_STRIP)
        for i in range(48):
            polar(t + ((i * 17) * 2 * math.pi / 47), 245)
        e.swap()
        e.finish()
        print(cycle)
        t += .005
