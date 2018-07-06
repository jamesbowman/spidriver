#!/usr/bin/env python3

import time
import sys
import struct
import array
import getopt
import random

from PIL import Image

from spidriver import SPIDriver

try:
    # First choice, use Numpy
    import numpy as np
    def as565(im):
        """ Return RGB565 of im """
        (r,g,b) = [np.array(c).astype(np.uint16) for c in im.split()]
        def s(x, n):
            return (x * (2 ** n - 1) / 255).astype(np.uint16)
        return ((s(b, 5) << 11) | (s(g, 6) << 5) | s(r, 5)).flatten().astype('>u2').tobytes()
except ImportError:
    # Second choice, Pillow's BGR;16 support
    def as565(im):
        r,g,b = im.convert("RGB").split()
        bgr = Image.merge("RGB", (b, g, r))
        a = array.array("H", bgr.convert("BGR;16").tobytes())
        a.byteswap()
        return a.tobytes()

if __name__ == '__main__':
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "h:")
    except getopt.GetoptError as reason:
        print()
        print('usage: listenscreenshot.py [options]')
        print()
        print()
        sys.exit(1)
    optdict = dict(optlist)

    NOP            = 0x00
    SWRESET        = 0x01
    RDDID          = 0x04
    RDDST          = 0x09

    SLPIN          = 0x10
    SLPOUT         = 0x11
    PTLON          = 0x12
    NORON          = 0x13

    INVOFF         = 0x20
    INVON          = 0x21
    DISPOFF        = 0x28
    DISPON         = 0x29
    CASET          = 0x2A
    RASET          = 0x2B
    RAMWR          = 0x2C
    RAMRD          = 0x2E

    PTLAR          = 0x30
    COLMOD         = 0x3A
    MADCTL         = 0x36

    FRMCTR1        = 0xB1
    FRMCTR2        = 0xB2
    FRMCTR3        = 0xB3
    INVCTR         = 0xB4
    DISSET5        = 0xB6

    PWCTR1         = 0xC0
    PWCTR2         = 0xC1
    PWCTR3         = 0xC2
    PWCTR4         = 0xC3
    PWCTR5         = 0xC4
    VMCTR1         = 0xC5

    RDID1          = 0xDA
    RDID2          = 0xDB
    RDID3          = 0xDC
    RDID4          = 0xDD

    PWCTR6         = 0xFC

    GMCTRP1        = 0xE0
    GMCTRN1        = 0xE1

    DELAY          = 0x80

    Rcmd1 = [
    SWRESET       ,   DELAY,            #  1: Software reset, 0 args, w/delay
      120,                              #     120 ms delay
    SLPOUT        ,   DELAY,            #  2: Out of sleep mode, 0 args, w/delay
      120,                              #     120 ms delay
    FRMCTR1       , 3      ,            #  3: Frame rate ctrl - normal mode, 3 args:
      0x01, 0x2C, 0x2D,                 #     Rate = fosc/(1x2+40) * (LINE+2C+2D)
    FRMCTR2       , 3      ,            #  4: Frame rate control - idle mode, 3 args:
      0x01, 0x2C, 0x2D,                 #     Rate = fosc/(1x2+40) * (LINE+2C+2D)
    FRMCTR3       , 6      ,            #  5: Frame rate ctrl - partial mode, 6 args:
      0x01, 0x2C, 0x2D,                 #     Dot inversion mode
      0x01, 0x2C, 0x2D,                 #     Line inversion mode
    PWCTR1        , 3      ,            #  7: Power control, 3 args:
      0xA2,
      0x02,                             #     -4.6V
      0x84,                             #     AUTO mode
    PWCTR2        , 1      ,            #  8: Power control, 1 arg:
      0xC5,                             #     VGH25 = 2.4C VGSEL = -10 VGH = 3 * AVDD
    PWCTR3        , 2      ,            #  9: Power control, 2 args:
      0x0A,                             #     Opamp current small
      0x00,                             #     Boost frequency
    PWCTR4        , 2      ,            # 10: Power control, 2 args:
      0x8A,                             #     BCLK/2, Opamp current small & Medium low
      0x2A,  
    PWCTR5        , 2      ,            # 11: Power control, 2 args:
      0x8A, 0xEE,
    VMCTR1        , 1      ,            # 12: Power control, 1 arg:
      0x0E,
    MADCTL        , 1      ,            # 13: Memory access control (directions), 1 arg:
      0xC8,                             #     row addr/col addr, bottom to top refresh
    COLMOD        , 1      ,            # 14: set color mode, 1 arg:
      0x05,                             #     16-bit color
    GMCTRP1       , 16      ,           # 15: Gamma + polarity Correction Characterstics
      0x02 , 0x1c , 0x07 , 0x12 ,
      0x37 , 0x32 , 0x29 , 0x2d ,
      0x29 , 0x25 , 0x2B , 0x39 ,
      0x00 , 0x01 , 0x03 , 0x10 ,
    GMCTRN1       , 16      ,           # 16: Gamma - polarity Correction Characterstics
      0x03 , 0x1d , 0x07 , 0x06 ,
      0x2E , 0x2C , 0x29 , 0x2D ,
      0x2E , 0x2E , 0x37 , 0x3F ,
      0x00 , 0x00 , 0x02 , 0x10 ,
    NORON         , 0       ,           # 17: Normal display on
    DISPON        , 0       ,           # 18: Main screen turn on
    ]
    print(Rcmd1)

    s = SPIDriver(optdict.get('-h', "/dev/ttyUSB0"))

    def select():
        s.setb(0)

    def unselect():
        s.setb(1)

    def writeCommand(c):
        # print('command %02x' % c)
        s.seta(0)
        select()
        s.write(bytes([c]))
        unselect()

    def writeData(c):
        # print('   data %02x' % c)
        s.seta(1)
        select()
        s.write(bytes([c]))
        unselect()
    def commandList(cc):
        i = 0
        while i < len(cc):
            writeCommand(cc[i])
            i += 1
            numArgs = cc[i]
            i += 1
            ms = numArgs & DELAY
            for j in range(numArgs & ~DELAY):
                writeData(cc[i])
                i += 1
            if ms:
                ms = cc[i]
                # print('  delay', ms)
                i += 1
                if ms == 255:
                    time.sleep(.5)
                else:
                    time.sleep(ms * .001)

    if 0:
        select()
        s.setb(1)
        time.sleep(.5)
        s.setb(0)
        time.sleep(.5)
        s.setb(1)
        time.sleep(.5)
        unselect()

    print('command bytes:', len(Rcmd1))
    commandList(Rcmd1)

    xstart, ystart = 0, 0
    def setAddrWindow(x0, y0, x1, y1):
        writeCommand(CASET       ); # Column addr set
        writeData(0x00);
        writeData(x0+xstart);     # XSTART 
        writeData(0x00);
        writeData(x1+xstart);     # XEND

        writeCommand(RASET       ); # Row addr set
        writeData(0x00);
        writeData(y0+ystart);     # YSTART
        writeData(0x00);
        writeData(y1+ystart);     # YEND

        writeCommand(RAMWR       ); # write to RAM
        s.seta(1)
        select()

    def rect(x, y, w, h, color):
        setAddrWindow(x, y, x + w - 1, y + h - 1)
        s.write(w * h * struct.pack(">H", color))
        unselect()
    t0 = time.time()
    rect(0, 0, 128, 160, 0x0000)
    print('took', time.time() - t0)

    while False:
        print('randoms')
        for i in range(8):
            rect(i * 16, i * 16, 16, 16, random.getrandbits(16))

    if False:
        w = (66)
        h = 13
        
        setAddrWindow(0, 0, w - 1, h - 1)
        color = random.getrandbits(16)
        color = 0xffff
        s.write(w * h * struct.pack(">H", color))
        unselect()

    if False:
        f = open("img", "rb")
        (w,h) = struct.unpack("<2H", f.read(4))
        t0 = time.time()
        setAddrWindow(0, 0, 0 + w - 1, 0 + h - 1)
        s.write(f.read())
        unselect()
        print('took', time.time() - t0)

    setAddrWindow(0, 0, 127, 159)
    im = Image.open("grace.png")
    s.write(as565(im.convert("RGB")))
    unselect()
