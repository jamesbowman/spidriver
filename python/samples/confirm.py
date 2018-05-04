#!/usr/bin/env python

from spidriver import SPIDriver
import random
import time
import sys
from crc16pure import crc16xmodem

# print(hex(crc16xmodem(bytes([0xaa, 0xbb, 0xcc]), 0xffff)))

def rnd(n):
    return random.randrange(n)

if __name__ == '__main__':
    s = SPIDriver()
    t1 = time.time() + float(sys.argv[1])
    i = 0
    while time.time() < t1:
        expected = s.debug
        s.unsel()
        l = 1 + rnd(100)
        db = [rnd(256) for j in range(l)]
        s.write(db)
        expected = crc16xmodem(db, expected)
        s.unsel()

        s.getstatus()
        assert expected == s.debug, "pass %d with %d bytes %s" % (i, len(db), list(db))
        i += 1
    for i in range(20):
        s.seta(0)
        s.setb(0)
        s.seta(1)
        s.setb(1)
