import sys
import serial

PYTHON2 = (sys.version_info < (3, 0))

class SPIDriver:
    """
    SPIDriver interface.

    The following variables are available:

        product     product code e.g. 'spidriver1'
        serial      serial string of SPIDriver
        uptime      time since SPIDriver boot, in seconds
        voltage     USB voltage, in V
        current     current used by attached device, in mA
        temp        temperature, in degrees C
        cs          state of CS pin
        a           state of A pin
        b           state of B pin
        debug       CCITT-16 CRC of all transmitted and received bytes

    """
    def __init__(self, port = "/dev/ttyUSB0"):
        self.ser = serial.Serial(port, 460800, timeout = 1)

        self.ser.write(b'@' * 64)
        while self.ser.inWaiting():
            self.ser.read(1)

        for c in [0x55, 0x00, 0xff, 0xaa]:
            r = self.__echo(c)
            if r != c:
                print('Echo test failed - not attached?')
                print('Expected %r but received %r' % (c, r))
                raise IOError
        self.getstatus()

    if PYTHON2:
        def __ser_w(self, s):
            if isinstance(s, list):
                s = "".join([chr(c) for c in s])
            self.ser.write(s)
    else:
        def __ser_w(self, s):
            if isinstance(s, list):
                s = bytes(s)
            self.ser.write(s)

    def __echo(self, c):
        self.__ser_w([ord('e'), c])
        r = self.ser.read(1)
        if PYTHON2:
            return ord(r[0])
        else:
            return r[0]

    def sel(self):
        """ Select the SPI device by asserting CS """
        self.ser.write(b's')

    def unsel(self):
        """ Unselect the SPI device by deasserting CS """
        self.ser.write(b'u')

    def read(self, l):
        """ Read l bytes from the SPI device """
        r = []
        for i in range(0, l, 64):
            rem = min(l - i, 64)
            self.__ser_w([0x80 + rem - 1] + [0xff] * rem)
            r.append(self.ser.read(rem))
        return b''.join(r)

    def write(self, bb):
        """ Write bb to the SPI device """
        for i in range(0, len(bb), 64):
            sub = bb[i:i + 64]
            self.__ser_w([0xc0 + len(sub) - 1])
            self.__ser_w(sub)

    def seta(self, v):
        """ Set the A signal to 0 or 1 """
        self.__ser_w([ord('a'), v])

    def setb(self, v):
        """ Set the B signal to 0 or 1 """
        self.__ser_w([ord('b'), v])

    def getstatus(self):
        """ Update all status variables """
        self.ser.write(b'?')
        r = self.ser.read(80)
        body = r[1:-1].decode() # remove [ and ]
        (self.product, self.serial, uptime, voltage, current, temp, a, b, cs, debug) = body.split()
        self.uptime = int(uptime)
        self.voltage = float(voltage)
        self.current = float(current)
        self.temp = float(temp)
        self.debug = int(debug, 16)

    def __repr__(self):
        return "<%s serial=%s uptime=%d>" % (
            self.product,
            self.serial,
            self.uptime)
