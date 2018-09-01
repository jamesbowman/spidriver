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
                "|" +
                "".join([toprint(c) for c in bb]).ljust(16) +
                "|")
    return "\n".join([hexline(s[i:i+16]) for i in range(0, len(s), 16)])

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

    def reset():
        s.seta(0)
        s.seta(1)
    s.sel()
    # reset()
    s.unsel()
    s.seta(0)

    while True:
        s.sel()               # start command
        s.write(b'\x9f')      # command 9F is READ JEDEC ID 
        ids = s.read(3)
        (id1, id2, id3) = struct.unpack("BBB", ids)
        print ("JEDEC ID: %02x %02x %02x" % (id1, id2, id3))
        s.unsel()             # end command
        if id1 not in (0x00, 0xff):
            break
        time.sleep(.02)

    """
    for c in (0x66, 0x99):
        s.sel()               # start command
        s.write(bytes([c]))
        s.unsel()
        time.sleep(.2)
    """

    def dump(a):
        s.unsel()
        s.sel()               # start command
        s.write([0x03, 0x00, 0x00, 0x00])
        for i in range(2):
            page = s.read(256)
            print(hexdump(page))
            print()
        s.unsel()             # end command
        time.sleep(.02)

    def command(b):
        s.unsel()
        s.sel()
        s.write(b)

    def idcode():
        command([0x9f])
        return s.read(3)

    def write_enable():
        command([0x06])

    def wait_ready():
        while True:
            command([0x05])
            r = s.read(1)
            if (r[0] & 1) == 0:
                break

    def read_all():
        s.sel()               # start command
        s.write([0x03, 0x00, 0x00, 0x00])
        f = open("contents", "wb")
        SIZE = 2 ** 22
        SIZE = 104090
        for p in range(0, SIZE, 1024):
            print(p, "/", SIZE)
            b1k = s.read(1024)
            f.write(b1k)
        s.unsel()             # end command
        f.close()

    def page_program(a, b256):
        print('page_program', a)
        write_enable()
        assert (a & 0xff) == 0x00
        command([0x02, (a >> 16) & 0xff, (a >> 8) & 0xff, 0x00])
        s.write(b256)
        wait_ready()

    def release():
        s.seta(1)
        s.unsel()
        s.seta(0)
        s.seta(1)
        s.detach()

    def erase():
        write_enable()
        command([0xc7])
        wait_ready()

    def erase_sector(a):
        print('erase sector', a)
        write_enable()
        command([0xd8, (a >> 16) & 0xff, 0x00, 0x00])
        wait_ready()

    if 1:
        dump(0)
        # erase()
        bin = open("rgb.bin", "rb").read()
        bin = open("/home/james/tmp/rgb.bin", "rb").read()
        bin = open("RGB_slow.bin", "rb").read()

        t0 = time.time()
        bin = open("RGB_LED_BLINK_fast.bin", "rb").read()
        for a in range(0, len(bin), 256):
            if (a & 0xffff) == 0:
                erase_sector(a)
            page_program(a, bin[a:a+256])
        print("took", time.time() - t0)
        dump(0)

    release()
