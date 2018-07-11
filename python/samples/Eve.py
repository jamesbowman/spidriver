# coding=utf-8
import struct
import sys
import time


def const(x): return x


PYTHON2 = (sys.version_info < (3, 0))
if PYTHON2:
    def align4(s):
        return s + (chr(0) * (-len(s) & 3))
else:
    def align4(s):
        return s + bytes(-len(s) & 3)


class CoprocessorException(Exception):
    pass


class SimpleTransport:

    def stream(self):
        pass

    def unstream(self):
        pass

    def c4(self, v):
        """
        Write 32-bit value v to the command FIFO
        """
        while self.space < 4:
            self.getspace()
        self.wr32(self.REG_CMDB_WRITE, v)
        self.space -= 4

    def c(self, ss):
        """
        Write s to the command FIFO
        """
        for i in range(0, len(ss), 256):
            s = ss[i:i + 256]
            while self.space < len(s):
                self.getspace()
            self.wr(self.REG_CMDB_WRITE, s)
            self.space -= len(s)

    def finish(self):
        while self.space < 4092:
            self.getspace()


class StreamingTransport:
    def stream(self):
        self.start(0x800000 | self.REG_CMDB_WRITE)

    def unstream(self):
        self.spi.unsel()

    def reserve(self, n):
        if self.space < n:
            self.unstream()
            while self.space < n:
                self.getspace()
            self.stream()

    def c4(self, v):
        """
        Write 32-bit value v to the command FIFO
        """
        self.reserve(4)
        self.spi.write(struct.pack("I", v))
        self.space -= 4

    def c(self, ss):
        """
        Write s to the command FIFO
        """
        for i in range(0, len(ss), 256):
            s = ss[i:i + 256]
            self.reserve(len(s))
            self.spi.write(s)
            self.space -= len(s)

    def finish(self):
        self.reserve(4092)

    def is_idle(self):
        self.unstream()
        self.getspace()
        self.stream()
        return self.space == 4092


class DisplayList:
    def __init__(self, eve, addr, size):
        self.eve = eve
        self.addr = addr
        self.size = size

    def draw(self, n=None):
        if n is None:
            self.eve.cmd_append(self.addr, self.size)
        else:
            assert 0 <= (4 * n) <= self.size
            self.eve.cmd_append(self.addr, 4 * n)


class Evebase:
    # ------------------------------------------------------ Host commands
    ACTIVE = const(0x00)  # init
    STANDBY = const(0x41)  # Standby clock running
    SLEEP = const(0x42)  # Sleep clock off
    PWRDOWN = const(0x50)  # Core off
    CLKEXT = const(0x44)  # Set external clock
    CLKINT = const(0x48)  # Set internal clock
    CORERST = const(0x68)  # Reset core

    # ------------------------------------------------------ Register addresses
    # Addresses bytes largest to smallest.

    RAM_CMD = const(0x308000)
    RAM_DL = const(0x300000)
    REG_CLOCK = const(0x302008)
    REG_CMD_DL = const(0x302100)
    REG_CMD_READ = const(0x3020f8)
    REG_CMDB_SPACE = const(0x302574)
    REG_CMDB_WRITE = const(0x302578)
    REG_CMD_WRITE = const(0x3020fc)
    REG_CPURESET = const(0x302020)
    REG_CSPREAD = const(0x302068)
    REG_DITHER = const(0x302060)
    REG_DLSWAP = const(0x302054)
    REG_FRAMES = const(0x302004)
    REG_FREQUENCY = const(0x30200c)
    REG_GPIO = const(0x302094)
    REG_GPIO_DIR = const(0x302090)
    REG_HCYCLE = const(0x30202c)
    REG_HOFFSET = const(0x302030)
    REG_HSIZE = const(0x302034)
    REG_HSYNC0 = const(0x302038)
    REG_HSYNC1 = const(0x30203c)
    REG_ID = const(0x302000)
    REG_INT_EN = const(0x3020ac)
    REG_INT_FLAGS = const(0x3020a8)
    REG_INT_MASK = const(0x3020b0)
    REG_MACRO_0 = const(0x3020d8)
    REG_MACRO_1 = const(0x3020dc)
    REG_OUTBITS = const(0x30205c)
    REG_PCLK = const(0x302070)
    REG_PCLK_POL = const(0x30206c)
    REG_PLAY = const(0x30208c)
    REG_PLAYBACK_FORMAT = const(0x3020c4)
    REG_PLAYBACK_FREQ = const(0x3020c0)
    REG_PLAYBACK_LENGTH = const(0x3020b8)
    REG_PLAYBACK_LOOP = const(0x3020c8)
    REG_PLAYBACK_PLAY = const(0x3020cc)
    REG_PLAYBACK_READPTR = const(0x3020bc)
    REG_PLAYBACK_START = const(0x3020b4)
    REG_PWM_DUTY = const(0x3020d4)
    REG_PWM_HZ = const(0x3020d0)
    REG_ROTATE = const(0x302058)
    REG_SOUND = const(0x302088)
    REG_SWIZZLE = const(0x302064)
    REG_TAG = const(0x30207c)
    REG_TAG_X = const(0x302074)
    REG_TAG_Y = const(0x302078)
    REG_TAP_CRC = const(0x302024)
    REG_TOUCH_ADC_MODE = const(0x302108)
    REG_TOUCH_CHARGE = const(0x30210c)
    REG_TOUCH_DIRECT_XY = const(0x30218c)
    REG_TOUCH_DIRECT_Z1Z2 = const(0x302190)
    REG_TOUCH_MODE = const(0x302104)
    REG_TOUCH_OVERSAMPLE = const(0x302114)
    REG_TOUCH_RAW_XY = const(0x30211c)
    REG_TOUCH_RZ = const(0x302120)
    REG_TOUCH_RZTHRESH = const(0x302118)
    REG_TOUCH_SCREEN_XY = const(0x302124)
    REG_TOUCH_SETTLE = const(0x302110)
    REG_TOUCH_TAG = const(0x30212c)
    REG_TOUCH_TAG_XY = const(0x302128)
    REG_TOUCH_TRANSFORM_A = const(0x302150)
    REG_TOUCH_TRANSFORM_B = const(0x302154)
    REG_TOUCH_TRANSFORM_C = const(0x302158)
    REG_TOUCH_TRANSFORM_D = const(0x30215c)
    REG_TOUCH_TRANSFORM_E = const(0x302160)
    REG_TOUCH_TRANSFORM_F = const(0x302164)
    REG_TRACKER = const(0x309000)
    REG_TRIM = const(0x302180)
    REG_VCYCLE = const(0x302040)
    REG_VOFFSET = const(0x302044)
    REG_VOL_PB = const(0x302080)
    REG_VOL_SOUND = const(0x302084)
    REG_VSIZE = const(0x302048)
    REG_VSYNC0 = const(0x30204c)
    REG_VSYNC1 = const(0x302050)

    # ------------------------------------------------------ Primitives
    PRIM_POINTS = const(0x02)
    PRIM_BITMAP = const(0x01)
    PRIM_LINES = const(0x03)
    PRIM_RECTS = const(0x09)

    BITMAPS = 1
    POINTS = 2
    LINES = 3
    LINE_STRIP = 4
    EDGE_STRIP_R = 5
    EDGE_STRIP_L = 6
    EDGE_STRIP_A = 7
    EDGE_STRIP_B = 8
    RECTS = 9

    NEAREST = 0
    BILINEAR = 1

    BORDER = 0
    REPEAT = 1

    KEEP = 1
    REPLACE = 2
    INCR = 3
    DECR = 4
    INVERT = 5

    ZERO = 0
    ONE = 1
    SRC_ALPHA = 2
    DST_ALPHA = 3
    ONE_MINUS_SRC_ALPHA = 4
    ONE_MINUS_DST_ALPHA = 5

    OPT_MONO = 1
    OPT_NODL = 2
    OPT_FLAT = 256
    OPT_CENTERX = 512
    OPT_CENTERY = 1024
    OPT_CENTER = (OPT_CENTERX | OPT_CENTERY)
    OPT_NOBACK = 4096
    OPT_NOTICKS = 8192
    OPT_NOHM = 16384
    OPT_NOPOINTER = 16384
    OPT_NOSECS = 32768
    OPT_NOHANDS = 49152
    OPT_RIGHTX = 2048
    OPT_SIGNED = 256

    # Eve's built-in audio samples
    HARP = 0x40  # Instruments
    XYLOPHONE = 0x41
    TUBA = 0x42
    GLOCKENSPIEL = 0x43
    ORGAN = 0x44
    TRUMPET = 0x45
    PIANO = 0x46
    CHIMES = 0x47
    MUSICBOX = 0x48
    BELL = 0x49
    CLICK = 0x50  # Percussive
    SWITCH = 0x51
    COWBELL = 0x52
    NOTCH = 0x53
    HIHAT = 0x54
    KICKDRUM = 0x55
    POP = 0x56
    CLACK = 0x57
    CHACK = 0x58
    MUTE = 0x60  # Management
    UNMUTE = 0x61

    # Bitmap formats
    ARGB1555 = 0
    L1 = 1
    L4 = 2
    L8 = 3
    RGB332 = 4
    ARGB2 = 5
    ARGB4 = 6
    RGB565 = 7
    PALETTED = 8
    TEXT8X8 = 9
    TEXTVGA = 10
    BARGRAPH = 11
    L2 = 17

    def packstring(self, s):
        if PYTHON2:
            return align4(s + chr(0))
        else:
            return align4(bytes(s, "utf-8") + bytes(1))

    # Low-level drawing opcodes

    def AlphaFunc(self, func, ref):
        self.c4((9 << 24) | ((func & 7) << 8) | ((ref & 255) << 0))

    def Begin(self, prim):
        self.c4((31 << 24) | ((prim & 15) << 0))

    def BitmapHandle(self, handle):
        self.c4((5 << 24) | ((handle & 31) << 0))

    def BitmapLayout(self, format, linestride, height):
        self.c4((7 << 24) | ((format & 31) << 19) | ((linestride & 1023) << 9) | ((height & 511) << 0))

    def BitmapSize(self, filter, wrapx, wrapy, width, height):
        self.c4((8 << 24) | ((filter & 1) << 20) | ((wrapx & 1) << 19) | ((wrapy & 1) << 18) | ((width & 511) << 9) | ((height & 511) << 0))

    def BitmapSource(self, addr):
        self.c4((1 << 24) | ((addr & 0xffffff) << 0))

    def BitmapTransformA(self, a):
        self.c4((21 << 24) | ((a & 131071) << 0))

    def BitmapTransformB(self, b):
        self.c4((22 << 24) | ((b & 131071) << 0))

    def BitmapTransformC(self, c):
        self.c4((23 << 24) | ((c & 16777215) << 0))

    def BitmapTransformD(self, d):
        self.c4((24 << 24) | ((d & 131071) << 0))

    def BitmapTransformE(self, e):
        self.c4((25 << 24) | ((e & 131071) << 0))

    def BitmapTransformF(self, f):
        self.c4((26 << 24) | ((f & 16777215) << 0))

    def BlendFunc(self, src, dst):
        self.c4((11 << 24) | ((src & 7) << 3) | ((dst & 7) << 0))

    def Call(self, dest):
        self.c4((29 << 24) | ((dest & 65535) << 0))

    def Cell(self, cell):
        self.c4((6 << 24) | ((cell & 127) << 0))

    def ClearColorA(self, alpha):
        self.c4((15 << 24) | ((alpha & 255) << 0))

    def ClearColorRGB(self, red, green, blue):
        self.c4((2 << 24) | ((red & 255) << 16) | ((green & 255) << 8) | ((blue & 255) << 0))

    def Clear(self, c=1, s=1, t=1):
        self.c4((38 << 24) | ((c & 1) << 2) | ((s & 1) << 1) | ((t & 1) << 0))

    def ClearStencil(self, s):
        self.c4((17 << 24) | ((s & 255) << 0))

    def ClearTag(self, s):
        self.c4((18 << 24) | ((s & 255) << 0))

    def ColorA(self, alpha):
        self.c4((16 << 24) | ((alpha & 255) << 0))

    def ColorMask(self, r, g, b, a):
        self.c4((32 << 24) | ((r & 1) << 3) | ((g & 1) << 2) | ((b & 1) << 1) | ((a & 1) << 0))

    def ColorRGB(self, red, green, blue):
        self.c4((4 << 24) | ((red & 255) << 16) | ((green & 255) << 8) | ((blue & 255) << 0))

    def Display(self):
        self.c4((0 << 24))

    def End(self):
        self.c4((33 << 24))

    def Jump(self, dest):
        self.c4((30 << 24) | ((dest & 65535) << 0))

    def LineWidth(self, width):
        self.c4((14 << 24) | ((width & 4095) << 0))

    def Macro(self, m):
        self.c4((37 << 24) | ((m & 1) << 0))

    def PointSize(self, size):
        self.c4((13 << 24) | ((size & 8191) << 0))

    def RestoreContext(self):
        self.c4((35 << 24))

    def Return(self):
        self.c4((36 << 24))

    def SaveContext(self):
        self.c4((34 << 24))

    def ScissorSize(self, width, height):
        self.c4((28 << 24) | ((width & 4095) << 12) | ((height & 4095) << 0))

    def ScissorXY(self, x, y):
        self.c4((27 << 24) | ((x & 2047) << 11) | ((y & 2047) << 0))

    def StencilFunc(self, func, ref, mask):
        self.c4((10 << 24) | ((func & 7) << 16) | ((ref & 255) << 8) | ((mask & 255) << 0))

    def StencilMask(self, mask):
        self.c4((19 << 24) | ((mask & 255) << 0))

    def StencilOp(self, sfail, spass):
        self.c4((12 << 24) | ((sfail & 7) << 3) | ((spass & 7) << 0))

    def TagMask(self, mask):
        self.c4((20 << 24) | ((mask & 1) << 0))

    def Tag(self, s):
        self.c4((3 << 24) | ((s & 255) << 0))

    def Vertex2f(self, x, y):
        self.c4((1 << 30) | ((x & 32767) << 15) | ((y & 32767) << 0))

    def Vertex2ii(self, x, y, handle, cell):
        self.c4((2 << 30) | ((x & 511) << 21) | ((y & 511) << 12) | ((handle & 31) << 7) | ((cell & 127) << 0))

    def VertexFormat(self, frac):
        self.c4((39 << 24) | ((frac & 7) << 0))

    def BitmapLayoutH(self, linestride, height):
        self.c4((40 << 24) | ((linestride & 3) << 2) | ((height & 3) << 0))

    def BitmapSizeH(self, width, height):
        self.c4((41 << 24) | ((width & 3) << 2) | ((height & 3) << 0))

    def PaletteSource(self, addr):
        self.c4((42 << 24) | ((addr & 4194303) << 0))

    def VertexTranslateX(self, x):
        self.c4((43 << 24) | ((x & 131071) << 0))

    def VertexTranslateY(self, y):
        self.c4((44 << 24) | ((y & 131071) << 0))

    def Nop(self):
        self.c4((45 << 24))

    # Higher-level graphics commands

    def cmd_append(self, ptr, num):
        self.c(struct.pack("III", 0xffffff1e, ptr, num))

    def cmd_bgcolor(self, c):
        self.c(struct.pack("II", 0xffffff09, c))

    def cmd_bitmap_transform(self, x0, y0, x1, y1, x2, y2, tx0, ty0, tx1, ty1, tx2, ty2, result):
        self.c(struct.pack("IiiiiiiiiiiiiH", 0xffffff21, x0, y0, x1, y1, x2, y2, tx0, ty0, tx1, ty1, tx2, ty2, result))

    def cmd_button(self, x, y, w, h, font, options, s):
        self.c(struct.pack("IhhhhhH", 0xffffff0d, x, y, w, h, font, options) + self.packstring(s))

    def cmd_calibrate(self, result):
        self.c(struct.pack("II", 0xffffff15, result))

    def cmd_clock(self, x, y, r, options, h, m, s, ms):
        self.c(struct.pack("IhhhHHHHH", 0xffffff14, x, y, r, options, h, m, s, ms))

    def cmd_coldstart(self):
        self.c(struct.pack("I", 0xffffff32))

    def cmd_dial(self, x, y, r, options, val):
        self.c(struct.pack("IhhhHH", 0xffffff2d, x, y, r, options, val))

    def cmd_dlstart(self):
        self.c(struct.pack("I", 0xffffff00))

    def cmd_fgcolor(self, c):
        self.c(struct.pack("II", 0xffffff0a, c))

    def cmd_gauge(self, x, y, r, options, major, minor, val, range):
        self.c(struct.pack("IhhhHHHHH", 0xffffff13, x, y, r, options, major, minor, val, range))

    def cmd_getmatrix(self, a, b, c, d, e, f):
        self.c(struct.pack("Iiiiiii", 0xffffff33, a, b, c, d, e, f))

    def cmd_getprops(self, ptr, w, h):
        self.c(struct.pack("IIII", 0xffffff25, ptr, w, h))

    def cmd_getptr(self, result):
        self.c(struct.pack("II", 0xffffff23, result))

    def cmd_gradcolor(self, c):
        self.c(struct.pack("II", 0xffffff34, c))

    def cmd_gradient(self, x0, y0, rgb0, x1, y1, rgb1):
        self.c(struct.pack("IhhIhhI", 0xffffff0b, x0, y0, rgb0, x1, y1, rgb1))

    def cmd_inflate(self, ptr):
        self.c(struct.pack("II", 0xffffff22, ptr))

    def cmd_interrupt(self, ms):
        self.c(struct.pack("II", 0xffffff02, ms))

    def cmd_keys(self, x, y, w, h, font, options, s):
        self.c(struct.pack("IhhhhhH", 0xffffff0e, x, y, w, h, font, options) + self.packstring(s))

    def cmd_loadidentity(self):
        self.c(struct.pack("I", 0xffffff26))

    def cmd_loadimage(self, ptr, options):
        self.c(struct.pack("III", 0xffffff24, ptr, options))

    def cmd_logo(self):
        self.c(struct.pack("I", 0xffffff31))

    def cmd_memcpy(self, dest, src, num):
        self.c(struct.pack("IIII", 0xffffff1d, dest, src, num))

    def cmd_memcrc(self, ptr, num, result):
        self.c(struct.pack("IIII", 0xffffff18, ptr, num, result))

    def cmd_memset(self, ptr, value, num):
        self.c(struct.pack("IIII", 0xffffff1b, ptr, value, num))

    def cmd_memwrite(self, ptr, num):
        self.c(struct.pack("III", 0xffffff1a, ptr, num))

    def cmd_memzero(self, ptr, num):
        self.c(struct.pack("III", 0xffffff1c, ptr, num))

    def cmd_number(self, x, y, font, options, n):
        self.c(struct.pack("IhhhHi", 0xffffff2e, x, y, font, options, n))

    def cmd_progress(self, x, y, w, h, options, val, range):
        self.c(struct.pack("IhhhhHHH", 0xffffff0f, x, y, w, h, options, val, range))

    def cmd_regread(self, ptr, result):
        self.c(struct.pack("III", 0xffffff19, ptr, result))

    def cmd_rotate(self, a):
        self.c(struct.pack("Ii", 0xffffff29, a))

    def cmd_scale(self, sx, sy):
        self.c(struct.pack("Iii", 0xffffff28, f16(sx), f16(sy)))

    def cmd_screensaver(self):
        self.c(struct.pack("I", 0xffffff2f))

    def cmd_scrollbar(self, x, y, w, h, options, val, size, range):
        self.c(struct.pack("IhhhhHHHH", 0xffffff11, x, y, w, h, options, val, size, range))

    def cmd_setfont(self, font, ptr):
        self.c(struct.pack("III", 0xffffff2b, font, ptr))

    def cmd_setmatrix(self):
        self.c(struct.pack("I", 0xffffff2a))

    def cmd_sketch(self, x, y, w, h, ptr, format):
        self.c(struct.pack("IhhHHIH", 0xffffff30, x, y, w, h, ptr, format))

    def cmd_slider(self, x, y, w, h, options, val, range):
        self.c(struct.pack("IhhhhHHH", 0xffffff10, x, y, w, h, options, val, range))

    def cmd_snapshot(self, ptr):
        self.c(struct.pack("II", 0xffffff1f, ptr))

    def cmd_spinner(self, x, y, style, scale):
        self.c(struct.pack("IhhHH", 0xffffff16, x, y, style, scale))

    def cmd_stop(self):
        self.c(struct.pack("I", 0xffffff17))

    def cmd_swap(self):
        self.c(struct.pack("I", 0xffffff01))

    def cmd_text(self, x, y, font, options, s):
        self.c(struct.pack("IhhhH", 0xffffff0c, x, y, font, options) + self.packstring(s))

    def cmd_toggle(self, x, y, w, font, options, state, s):
        self.c(struct.pack("IhhhhHH", 0xffffff12, x, y, w, font, options, state) + self.packstring(s))

    def cmd_touch_transform(self, x0, y0, x1, y1, x2, y2, tx0, ty0, tx1, ty1, tx2, ty2, result):
        self.c(struct.pack("IiiiiiiiiiiiiH", 0xffffff20, x0, y0, x1, y1, x2, y2, tx0, ty0, tx1, ty1, tx2, ty2, result))

    def cmd_track(self, x, y, w, h, tag):
        self.c(struct.pack("Ihhhhh", 0xffffff2c, x, y, w, h, tag))

    def cmd_translate(self, tx, ty):
        self.c(struct.pack("Iii", 0xffffff27, f16(tx), f16(ty)))

    def cmd_romfont(self, dst, src):
        self.c(struct.pack("III", 0xffffff3f, dst, src))

    def cmd_mediafifo(self, ptr, size):
        self.c(struct.pack("III", 0xffffff39, ptr, size))

    def cmd_sync(self):
        self.c(struct.pack("I", 0xffffff42))

    # def cmd_snapshot2(self,
    # def cmd_setbase(self,
    # def cmd_playvideo(self,
    # def cmd_setfont2(self,
    # def cmd_setscratch(self,
    # def cmd_videostart(self,
    # def cmd_videoframe(self,
    # def cmd_sync(self,

    def cmd_setbitmap(self, source, fmt, w, h):
        self.c(struct.pack("IIhhhh", 0xffffff43, source, fmt, w, h, 0))

    def cmd_setrotate(self, r):
        self.c(struct.pack("II", 0xffffff36, r))

    # Management and utilities

    def cmd_regwrite(self, ptr, val):
        self.cmd_memwrite(ptr, 4)
        self.c4(val)

    def flush(self):
        pass

    def swap(self):
        self.Display()
        self.cmd_swap()
        self.cmd_dlstart()
        self.flush()


class Eve(Evebase, StreamingTransport):
    def __init__(self, spi_object):

        self.spi = spi_object

    def initialize(self):
        while True:
            print('Initialize display')

            self.host_cmd(self.ACTIVE, 0x00)  # Wake up
            self.host_cmd(self.CLKINT, 0x00)  # Use internal oscillator
            self.host_cmd(self.CORERST, 0x00)  # Core reset

            time.sleep(.150)
            attempts = 20
            while attempts > 0 and self.raw_read(self.REG_ID) != 0x7c:
                time.sleep(.10)
                attempts -= 1
            if attempts != 0:  # means that REG_ID is OK
                break

        self.getspace()
        self.stream()

        self.Clear()
        self.swap()
        self.cmd_regwrite(self.REG_PWM_DUTY, 0)
        self.cmd_regwrite(self.REG_SWIZZLE, 3)
        self.cmd_regwrite(self.REG_PCLK_POL, 1)
        self.cmd_regwrite(self.REG_PCLK, 6)
        self.cmd_setrotate(1)
        self.cmd_regwrite(self.REG_GPIO, 0x80)
        for i in range(12):
            self.cmd_sync()
        self.cmd_regwrite(self.REG_PWM_DUTY, 128)

    def getspace(self):
        self.space = self.raw_read(self.REG_CMDB_SPACE)
        if self.space & 1:
            raise CoprocessorException
        assert 0 <= self.space <= 4092, self.space

    def configure(self):

        print('Configure display')
        setup = [
            (self.REG_HSIZE, 800),
            (self.REG_HCYCLE, 952),
            (self.REG_HOFFSET, 46),
            (self.REG_HSYNC0, 0),
            (self.REG_HSYNC1, 10),
            (self.REG_VSIZE, 480),
            (self.REG_VCYCLE, 525),
            (self.REG_VOFFSET, 23),
            (self.REG_VSYNC0, 0),
            (self.REG_VSYNC1, 16),
            (self.REG_CSPREAD, 0),
            (self.REG_SWIZZLE, 0),
            (self.REG_PCLK_POL, 1),
            (self.REG_GPIO, 0x83),  # | self.raw_read(self.REG_GPIO)
            (self.REG_PWM_DUTY, 0),
        ]
        riverdi = [
            (self.REG_TOUCH_TRANSFORM_A, 65536 * 800 // 1770),
            (self.REG_TOUCH_TRANSFORM_E, 65536 * 480 // 1024),
        ]
        for (a, v) in setup + riverdi:
            self.cmd_regwrite(a, v)

        self.Clear()
        self.swap()
        self.finish()

        self.cmd_regwrite(self.REG_PCLK, 2)  # Enable display

    def startup(self):
        self.initialize()
        self.configure()

    def debug(self):
        print("REG_ID %x" % self.raw_read(self.REG_ID))
        print("REG_HCYCLE %d" % self.raw_read(self.REG_HCYCLE))
        print("REG_VCYCLE %d" % self.raw_read(self.REG_VCYCLE))
        print("REG_GPIO %d" % self.raw_read(self.REG_GPIO))
        print("REG_PWM_DUTY %d" % self.raw_read(self.REG_PWM_DUTY))
        while 0:
            print("REG_FRAMES %d" % self.raw_read(self.REG_FRAMES))
        # assert 0

    def tapcrc(self):
        """
        Return the 32-bit display tap CRC
        """
        self.finish()
        self.unstream()
        f0 = self.raw_read(self.REG_FRAMES)
        while (0xffffffff & (self.raw_read(self.REG_FRAMES) - f0)) < 2:
            pass
        r = self.raw_read(self.REG_TAP_CRC)
        self.stream()
        return r

    def write(self, s):
        self.spi.sel()
        self.spi.write(s)
        self.spi.unsel()

    def start(self, a):
        self.spi.sel()
        self.spi.write([
            0xff & (a >> 16),
            0xff & (a >> 8),
            0xff & a])

    def wr(self, a, s):
        self.start(a | 0x800000)
        self.spi.write(s)
        self.spi.unsel()

    def wr32(self, a, v):
        self.wr(a, struct.pack("<I", v))

    def raw_read(self, a):
        self.start(a)
        self.spi.write([0xff])
        (r,) = struct.unpack("I", self.spi.read(4))
        self.spi.unsel()
        return r

    def rd(self, a, size):
        self.spi.sel()
        r = self.spi.send_recv(bytearray([0xff & (a >> 16), 0xff & (a >> 8), 0xff & a, 0]) + bytearray(size))
        self.spi.unsel()
        return r[-size:]

    def host_cmd(self, the_cmd, value):
        """
        Send specific host commands to the display
        """
        self.write([the_cmd, value, 0x00])

    def screenshot(self, dest):
        REG_SCREENSHOT_EN = 0x302010  # Set to enable screenshot mode
        REG_SCREENSHOT_Y = 0x302014  # Y line register
        REG_SCREENSHOT_START = 0x302018  # Screenshot start trigger
        REG_SCREENSHOT_BUSY = 0x3020e8  # Screenshot ready flags
        REG_SCREENSHOT_READ = 0x302174  # Set to enable readout
        RAM_SCREENSHOT = 0x3c2000  # Screenshot readout buffer

        self.finish()
        self.unstream()
        w = self.raw_read(self.REG_HSIZE)
        h = self.raw_read(self.REG_VSIZE)

        f = open(dest, "wb")
        f.write(bytes("P6\n%d %d\n255\n" % (w, h), "utf-8"))
        self.wr32(REG_SCREENSHOT_EN, 1)
        self.wr32(0x0030201c, 32)

        for ly in range(h):
            print("line %d" % ly)
            self.wr32(REG_SCREENSHOT_Y, ly)
            self.wr32(REG_SCREENSHOT_START, 1)
            time.sleep_ms(2)
            while self.raw_read(REG_SCREENSHOT_BUSY) | self.raw_read(REG_SCREENSHOT_BUSY + 4):
                pass
            self.wr32(REG_SCREENSHOT_READ, 1)
            bgra = self.rd(RAM_SCREENSHOT, 4 * w)
            (b, g, r, a) = [bgra[i::4] for i in range(4)]
            f.write(bytes(sum(zip(r, g, b), ())))
            self.wr32(REG_SCREENSHOT_READ, 0)
        self.wr32(REG_SCREENSHOT_EN, 0)
        f.close()
        self.stream()

    def rd32(self, addr):
        self.unstream()
        r = self.raw_read(addr)
        self.stream()
        return r

    def rdbytes(self, addr, n):
        self.unstream()
        self.start(addr)
        self.spi.write(bytes(1))
        r = self.spi.read(n)
        self.spi.unsel()
        self.stream()
        return r

    def dl_start(self):
        self.finish()
        self.dl_ptr = self.rd32(self.REG_CMD_DL)

    def dl_finish(self, addr=None):
        if addr is None:
            addr = self.dl_addr
        self.finish()
        dl_end = self.rd32(self.REG_CMD_DL)
        size = dl_end - self.dl_ptr
        self.cmd_memcpy(addr, self.RAM_DL + self.dl_ptr, size)
        self.cmd_regwrite(self.REG_CMD_DL, self.dl_ptr)
        r = DisplayList(self, addr, size)
        self.dl_ptr = None
        self.dl_addr = addr + size
        assert self.dl_addr <= 0x100000
        return r

    def result(self, n=1):
        # Return the result field of the preceding command
        self.finish()
        self.unstream()
        wp = self.raw_read(self.REG_CMD_READ)
        r = self.raw_read(self.RAM_CMD + (4095 & (wp - 4 * n)))
        self.stream()
        return r
