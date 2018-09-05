#!/usr/bin/env python3
# coding=utf-8
import array
import getopt
import struct
import sys
import time

from PIL import Image
from spidriver import SPIDriver

# Pure Python rgb to 565 encoder for portablity
def as565(im):
    rr, gg, bb = [list(c.getdata()) for c in im.convert("RGB").split()]
    def s(x, n):
        return x * (2 ** n - 1) // 255
    d565 = [(s(b, 5) << 11) | (s(g, 6) << 5) | s(r, 5) for (r,g,b) in zip(rr, gg, bb)]
    d565h = array.array('H', d565)
    d565h.byteswap()
    return array.array('B', d565h.tostring())

NOP = 0x00
SWRESET = 0x01
RDDID = 0x04
RDDST = 0x09

SLPIN = 0x10
SLPOUT = 0x11
PTLON = 0x12
NORON = 0x13

INVOFF = 0x20
INVON = 0x21
DISPOFF = 0x28
DISPON = 0x29
CASET = 0x2A
RASET = 0x2B
RAMWR = 0x2C
RAMRD = 0x2E

PTLAR = 0x30
COLMOD = 0x3A
MADCTL = 0x36

FRMCTR1 = 0xB1
FRMCTR2 = 0xB2
FRMCTR3 = 0xB3
INVCTR = 0xB4
DISSET5 = 0xB6

PWCTR1 = 0xC0
PWCTR2 = 0xC1
PWCTR3 = 0xC2
PWCTR4 = 0xC3
PWCTR5 = 0xC4
VMCTR1 = 0xC5

RDID1 = 0xDA
RDID2 = 0xDB
RDID3 = 0xDC
RDID4 = 0xDD

PWCTR6 = 0xFC

GMCTRP1 = 0xE0
GMCTRN1 = 0xE1

DELAY = 0x80


class ST7735:
    def __init__(self, sd):
        self.sd = sd
        self.sd.unsel()

    def write(self, a, c):
        self.sd.seta(a)
        self.sd.sel()
        self.sd.write(c)
        self.sd.unsel()

    def writeCommand(self, cc):
        self.write(0, struct.pack("B", cc))

    def writeData(self, c):
        self.write(1, c)

    def writeData1(self, cc):
        self.writeData(struct.pack("B", cc))

    def cmd(self, cc, args=()):
        self.writeCommand(cc)
        n = len(args)
        if n != 0:
            self.writeData(struct.pack(str(n) + "B", *args))

    def setAddrWindow(self, x0, y0, x1, y1):
        self.writeCommand(CASET)  # Column addr set
        self.writeData(struct.pack(">HH", x0, x1))
        self.writeCommand(RASET)  # Row addr set
        self.writeData(struct.pack(">HH", y0, y1))
        self.writeCommand(RAMWR)  # write to RAM

    def rect(self, x, y, w, h, color):
        self.setAddrWindow(x, y, x + w - 1, y + h - 1)
        self.writeData(w * h * struct.pack(">H", color))

    def start(self):
        self.sd.setb(0)
        time.sleep(.001)
        self.sd.setb(1)
        time.sleep(.001)

        self.cmd(SWRESET)   # Software reset, 0 args, w/delay
        time.sleep(.180)
        self.cmd(SLPOUT)    # Out of sleep mode, 0 args, w/delay
        time.sleep(.180)

        commands = [
            (FRMCTR1, (     # Frame rate ctrl - normal mode
                0x01, 0x2C, 0x2D)),  # Rate = fosc/(1x2+40) * (LINE+2C+2D)
            (FRMCTR2, (     # Frame rate control - idle mode
                0x01, 0x2C, 0x2D)),  # Rate = fosc/(1x2+40) * (LINE+2C+2D)
            (FRMCTR3, (     # Frame rate ctrl - partial mode
                0x01, 0x2C, 0x2D,  # Dot inversion mode
                0x01, 0x2C, 0x2D)),  # Line inversion mode
            (PWCTR1, (      # Power control
                0xA2,
                0x02,       # -4.6V
                0x84)),     # AUTO mode
            (PWCTR2, (      # Power control
                0xC5,)),    # VGH25 = 2.4C VGSEL = -10 VGH = 3 * AVDD
            (PWCTR3, (      # Power control
                0x0A,       # Opamp current small
                0x00)),     # Boost frequency
            (PWCTR4, (      # Power control
                0x8A,       # BCLK/2, Opamp current small & Medium low
                0x2A)),
            (PWCTR5, (      # Power control
                0x8A, 0xEE)),
            (VMCTR1, (      # VCOM control
                0x0E,)),
            (MADCTL, (      # Memory access control (directions)
                0xC8,)),    # row addr/col addr, bottom to top refresh
            (COLMOD, (      # set color mode
                0x05,)),    # 16-bit color
            (GMCTRP1, (     # Gamma + polarity Correction Characterstics
                0x02, 0x1c, 0x07, 0x12,
                0x37, 0x32, 0x29, 0x2d,
                0x29, 0x25, 0x2B, 0x39,
                0x00, 0x01, 0x03, 0x10)),
            (GMCTRN1, (     # Gamma - polarity Correction Characterstics
                0x03, 0x1d, 0x07, 0x06,
                0x2E, 0x2C, 0x29, 0x2D,
                0x2E, 0x2E, 0x37, 0x3F,
                0x00, 0x00, 0x02, 0x10)),
            (NORON, ()),    # Normal display on
            (DISPON, ()),   # Main screen turn on
        ]
        for c, args in commands:
            self.cmd(c, args)

    def clear(self):
        self.rect(0, 0, 128, 160, 0x0000)

    def loadimage(self, a):
        im = Image.open(a)
        if im.size[0] > im.size[1]:
            im = im.transpose(Image.ROTATE_90)
        w = 160 * im.size[0] // im.size[1]
        im = im.resize((w, 160), Image.ANTIALIAS)
        (w, h) = im.size
        if w > 128:
            im = im.crop((w // 2 - 64, 0, w // 2 + 64, 160))
        elif w < 128:
            c = Image.new("RGB", (128, 160))
            c.paste(im, (64 - w // 2, 0))
            im = c
        st.setAddrWindow(0, 0, 127, 159)
        st.writeData(as565(im.convert("RGB")))


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

    st = ST7735(SPIDriver(optdict.get('-h', "/dev/ttyUSB0")))
    st.start()
    st.clear()

    for a in args:
        st.loadimage(a)
