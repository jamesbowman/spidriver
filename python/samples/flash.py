#!/usr/bin/env python3

from spidriver import SPIDriver
import struct
import time
import sys
import getopt

def hexdump(s):
    def toprint(c):
        if 32 <= c < 127:
            return chr(c)
        else:
            return "."
    def hexline(s):
        bb = struct.unpack("16B", s)
        return (" ".join(["%02x" % c for c in bb]).ljust(49) +
                "|" + "".join([toprint(c) for c in bb]).ljust(16) + "|")
    return "\n".join([hexline(s[i:i+16]) for i in range(0, len(s), 16)])

if __name__ == '__main__':
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "h:r:w:s:")
    except getopt.GetoptError as reason:
        print()
        print('usage: flash [ -h device ] [ -r file ] [ -w file ] [-s size]')
        print()
        print()
        sys.exit(1)
    optdict = dict(optlist)

    s = SPIDriver(optdict.get('-h', "/dev/ttyUSB0"))
    s.seta(0)
    s.unsel()

    size = int(optdict.get('-s', "0"))

                                # Some primitives for generic flash
    def command(b):
        s.unsel()
        s.sel()
        s.writeread(b)

    def idcode():
        command([0x9f])
        return s.read(3)

    def write_enable():
        command([0x06])

    def status():
        command([0x05])
        (r,) = struct.unpack("B", s.read(1))
        return r

    def wait_ready():
        while True:
            r = status()
            if (r & 1) == 0:
                break

    def addr24(a):
        return [(a >> 16) & 0xff, (a >> 8) & 0xff, a & 0xff]

    def page_program(a, b256):
        # print('page_program', a)
        write_enable()
        command([0x02] + addr24(a))
        s.writeread(b256)
        wait_ready()

    def erase_sector(a):
        # print('erase sector', a)
        write_enable()
        command([0xd8] + addr24(a))
        wait_ready()

    def read(a):
        command([0x03] + addr24(a))

    while True:
        ids = struct.unpack("BBB", idcode())
        print("Got JEDEC ID: %02x %02x %02x" % ids)
        if size > 0:
            break
        if ids[0] not in (0x00, 0xff) and (1 <= ids[2] < 22):
            break
    if size == 0:
        size = 1 << ids[2]
    print("Flash size is %d bytes" % size)

    print("Status is %02x" % status())

    if '-r' in optdict:
        read(0)
        chunk = 8 * 1024
        size,chunk = 128,128
        with open(optdict['-r'], "wb") as f:
            for a in range(0, size, chunk):
                d = s.read(chunk)
                print(d)
                f.write(d)
                print("%d/%d KBytes" % (a / 1024, size / 1024))
    if '-w' in optdict:
        write_enable()
        command([0xc7])
        wait_ready()
        with open(optdict['-w'], "rb") as f:
            for a in range(0, size, 256):
                d = f.read(256)
                if len(d) == 0:
                    break
                page_program(a, d)
                print("%d/%d KBytes" % (a / 1024, size / 1024))
    write_enable()

    s.unsel()
    s.seta(1)
    s.detach()
