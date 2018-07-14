#!/usr/bin/env python3
# coding=utf-8
import sys

from Eve import Eve
from spidriver import SPIDriver


def align4(s):
    return s + bytes(-len(s) & 3)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        s = SPIDriver(sys.argv[1])
    else:
        s = SPIDriver()
    e = Eve(s)
    e.initialize()

    e.cmd_setbitmap(0, e.RGB565, 480, 272)
    e.Clear()
    e.Begin(Eve.BITMAPS)
    e.Vertex2f(0, 0)
    e.swap()
    e.finish()

    for a in sys.argv[2:]:
        e.cmd_loadimage(0, Eve.OPT_NODL)
        e.c(align4(open(a, "rb").read()))
