#!/usr/bin/env python3

from spidriver import SPIDriver
import struct
import time
import sys
import getopt

def hexdump(s):
    def toprint(c):
        if 32 <= ord(c) < 127:
            return c
        else:
            return "."
    def hexline(s):
        return (" ".join(["%02x" % ord(c) for c in s]).ljust(49) +
                "|" +
                "".join([toprint(c) for c in s]).ljust(16) +
                "|")
    return "\n".join([hexline(s[i:i+16]) for i in range(0, len(s), 16)])

def rnd(n):
    return random.randrange(n)


def pattern(n):
    return [rnd(256) for i in range(n)]

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

    while True:
        s.sel()               # start command
        s.write(b'\x9f')      # command 9F is READ JEDEC ID 
        ids = s.read(3)
        (id1, id2, id3) = struct.unpack("BBB", ids)
        print ("JEDEC ID: %02x %02x %02x" % (id1, id2, id3))
        s.unsel()             # end command
        time.sleep(.02)
        if id1 not in (0x00, 0xff):
            break

    for c in (0x66, 0x99):
        s.sel()               # start command
        s.write(bytes([c]))
        s.unsel()
        time.sleep(.2)

    s.sel()               # start command
    s.write([0x03, 0x00, 0x00, 0x00])
    page = s.read(256)
    print(hexdump(page))
    s.unsel()             # end command
    time.sleep(.02)
