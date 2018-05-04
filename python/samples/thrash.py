#!/usr/bin/env python3

from spidriver import SPIDriver
import random
import time
import sys

def rnd(n):
    return random.randrange(n)


def pattern(n):
    return bytes([rnd(256) for i in range(n)])

if __name__ == '__main__':
    s = SPIDriver()
    print(hex(s.debug))
    # print(s)
    t1 = time.time() + float(sys.argv[1])
    while time.time() < t1:
        random.choice([
            lambda: s.seta(rnd(2)),
            lambda: s.setb(rnd(2)),
            lambda: s.sel(),
            lambda: s.unsel(),
            lambda: s.write(pattern(1 + rnd(1))),
            lambda: s.read(1 + rnd(12)),
            lambda: s.getstatus()
            ])()
        # time.sleep(.020)
    print(hex(s.debug))

    while 0:
        s.sel()
        s.write(b'ABCDEF')
        s.unsel()
        time.sleep(.050)
