#!/usr/bin/env python3

from spidriver import SPIDriver
import struct
import time
import sys
import getopt

if __name__ == '__main__':
    try:
        optlist, args = getopt.getopt(sys.argv[1:], "h:")
    except getopt.GetoptError as reason:
        print()
        print('usage: iceprog [ -h device ] bitstream...')
        print()
        print()
        sys.exit(1)
    optdict = dict(optlist)

    s = SPIDriver(optdict.get('-h', "/dev/ttyUSB0"))

    s.sel()                     # Hold FPGA in reset
    s.seta(0)
                                # Some primitives for the N25Q flash
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
            (r,) = struct.unpack("B", s.read(1))
            if (r & 1) == 0:
                break

    def addr24(a):
        return [(a >> 16) & 0xff, (a >> 8) & 0xff, a & 0xff]

    def page_program(a, b256):
        # print('page_program', a)
        write_enable()
        command([0x02] + addr24(a))
        s.write(b256)
        wait_ready()

    def erase_sector(a):
        # print('erase sector', a)
        write_enable()
        command([0xd8] + addr24(a))
        wait_ready()

    ids = struct.unpack("BBB", idcode())
    if ids != (0x20, 0xba, 0x16):
        print ("Unexpected JEDEC ID: %02x %02x %02x" % ids)
        sys.exit(1)

    bin = open(sys.argv[1], "rb").read()
    t0 = time.time()
    for a in range(0, len(bin), 256):
        if (a & 0xffff) == 0:
            erase_sector(a)
        page_program(a, bin[a:a+256])
    print("flash load took %.2f s" % (time.time() - t0))

    s.unsel()
    s.seta(1)       # Let the FPGA boot
    s.detach()      # Release the SPI signals
