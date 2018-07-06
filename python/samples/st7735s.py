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

DELAY = 0x80

class ST7735:
    def __init__(self, sd):
        self.sd = sd

    def write(self, a, c):
        self.sd.seta(a)
        self.sd.setb(0)                 # select
        self.sd.write(c)
        self.sd.setb(1)                 # unselect

    def writeCommand(self, cc):
        self.write(0, bytes([cc]))

    def writeData(self, c):
        self.write(1, c)

    def writeData1(self, cc):
        self.writeData(bytes([cc]))

    def cmd(self, cc, args = ()):
        print("CMD", cc, args)
        self.write(0, bytes([cc]))
        self.writeData(bytes(args))

    def setAddrWindow(self, x0, y0, x1, y1):
        self.writeCommand(CASET)        # Column addr set
        self.writeData(struct.pack(">HH", x0, x1))
        self.writeCommand(RASET)        # Row addr set
        self.writeData(struct.pack(">HH", y0, y1))
        self.writeCommand(RAMWR)        # write to RAM

    def rect(self, x, y, w, h, color):
        self.setAddrWindow(x, y, x + w - 1, y + h - 1)
        self.writeData(w * h * struct.pack(">H", color))

    def start(self):
        self.cmd(SWRESET)                   #  1: Software reset, 0 args, w/delay
        time.sleep(.120)
        self.cmd(SLPOUT)                    #  2: Out of sleep mode, 0 args, w/delay
        time.sleep(.120)

        Rcmd1 = [
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

        commands = [
        (FRMCTR1       , (                   #  3: Frame rate ctrl - normal mode, 3 args:
          0x01, 0x2C, 0x2D)),                 #     Rate = fosc/(1x2+40) * (LINE+2C+2D)
        (FRMCTR2       , (                   #  4: Frame rate control - idle mode, 3 args:
          0x01, 0x2C, 0x2D)),                 #     Rate = fosc/(1x2+40) * (LINE+2C+2D)
        (FRMCTR3       , (                   #  5: Frame rate ctrl - partial mode, 6 args:
          0x01, 0x2C, 0x2D,                 #     Dot inversion mode
          0x01, 0x2C, 0x2D)),                 #     Line inversion mode
        (PWCTR1        , (                   #  7: Power control, 3 args:
          0xA2,
          0x02,                             #     -4.6V
          0x84)),                             #     AUTO mode
        (PWCTR2        , (                   #  8: Power control, 1 arg:
          0xC5,)),                           #     VGH25 = 2.4C VGSEL = -10 VGH = 3 * AVDD
        (PWCTR3        , (                   #  9: Power control, 2 args:
          0x0A,                             #     Opamp current small
          0x00)),                            #     Boost frequency
        (PWCTR4        , (                   # 10: Power control, 2 args:
          0x8A,                             #     BCLK/2, Opamp current small & Medium low
          0x2A)), 
        (PWCTR5        , (                   # 11: Power control, 2 args:
          0x8A, 0xEE)),
        (VMCTR1        , (                   # 12: VCOM control, 1 arg:
          0x0E,)),
        (MADCTL        , (                   # 13: Memory access control (directions), 1 arg:
          0xC8, )),                            #     row addr/col addr, bottom to top refresh
        (COLMOD        , (                   # 14: set color mode, 1 arg:
          0x05,)),                             #     16-bit color
        (GMCTRP1       , (                   # 15: Gamma + polarity Correction Characterstics
          0x02 , 0x1c , 0x07 , 0x12 ,
          0x37 , 0x32 , 0x29 , 0x2d ,
          0x29 , 0x25 , 0x2B , 0x39 ,
          0x00 , 0x01 , 0x03 , 0x10)),
        (GMCTRN1       , (                   # 16: Gamma - polarity Correction Characterstics
          0x03 , 0x1d , 0x07 , 0x06 ,
          0x2E , 0x2C , 0x29 , 0x2D ,
          0x2E , 0x2E , 0x37 , 0x3F ,
          0x00 , 0x00 , 0x02 , 0x10)),
        (NORON         , ())       ,           # 17: Normal display on
        (DISPON        , ())       ,           # 18: Main screen turn on
        ][12:]

        cc = Rcmd1
        i = 0
        while i < len(cc):
            self.writeCommand(cc[i])
            i += 1
            numArgs = cc[i]
            i += 1
            ms = numArgs & DELAY
            for j in range(numArgs & ~DELAY):
                self.writeData1(cc[i])
                i += 1
            if ms:
                ms = cc[i]
                # print('  delay', ms)
                i += 1
                if ms == 255:
                    time.sleep(.5)
                else:
                    time.sleep(ms * .001)

        for c, args in commands:
            self.cmd(c, args)
    
if __name__ == '__main__':
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "h:")
    except getopt.GetoptError as reason:
        print()
        print('usage: st7735 [ -h device ] image...')
        print()
        print()
        sys.exit(1)
    optdict = dict(optlist)

    s = SPIDriver(optdict.get('-h', "/dev/ttyUSB0"))
    st = ST7735(s)
    st.start()
    st.rect(0, 0, 128, 160, 0x0000)

    for a in args:
        im = Image.open(a)
        st.setAddrWindow(0, 0, 127, 159)
        st.writeData(as565(im.convert("RGB")))
