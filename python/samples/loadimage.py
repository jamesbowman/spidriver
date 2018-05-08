#!/usr/bin/env python3

import sys
from spidriver import SPIDriver
from Eve import Eve

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

    e.cmd_loadimage(0, Eve.OPT_NODL)
    e.c(open("logo480.png", "rb").read())
