#!/usr/bin/env python

from spidriver import SPIDriver
import random
import time
import sys
import array
from crc16pure import crc16xmodem

import spidriver
# print(hex(crc16xmodem(bytes([0xaa, 0xbb, 0xcc]), 0xffff)))

def rnd(n):
    return random.randrange(n)

if __name__ == '__main__':
    s = SPIDriver()
    t1 = time.time() + float(sys.argv[1])
    i = 0
    random.seed(7)
    while time.time() < t1:
        expected = s.ccitt_crc
        s.unsel()
        l = 1 + rnd(100)
        db = [rnd(256) for j in range(l)]
        s.write(db)
        expected = crc16xmodem(db, expected)
        s.unsel()

        db = [rnd(256) for j in range(64)]
        r = list(array.array('B', s.writeread(db)))
        expected = crc16xmodem(db, expected)
        expected = crc16xmodem(r, expected)

        s.getstatus()
        print("expected=%04x actual=%04x" % (expected, s.ccitt_crc))
        assert expected == s.ccitt_crc, "pass %d with %d bytes %s, expected=%04x actual=%04x" % (i, len(db), list(db), expected, s.ccitt_crc)
        i += 1
    for i in range(20):
        s.seta(0)
        s.setb(0)
        s.seta(1)
        s.setb(1)
