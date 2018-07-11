#!/usr/bin/env python3
# coding=utf-8
import os
import random
import sys
import time

from spidriver import SPIDriver


def rnd(n):
    return random.randrange(n)


def pattern(n):
    return [rnd(256) for i in range(n)]


if __name__ == '__main__':
    if len(sys.argv) > 1:
        s = SPIDriver(sys.argv[1])
    else:
        s = SPIDriver()
    # print(s)
    # t1 = time.time() + float(sys.argv[2])
    while True:  # time.time() < t1:
        for i in range(50):
            random.choice([
                lambda: s.seta(rnd(2)),
                lambda: s.setb(rnd(2)),
                lambda: s.sel(),
                lambda: s.unsel(),
                lambda: s.writeread(pattern(1 + rnd(1))),
                # lambda: s.read(1 + rnd(12)),
                # lambda: s.getstatus()
            ])()
        os.system("outlet.py 8 on ; outlet.py 8 off")
        time.sleep(3)
    print(hex(s.debug))

    while 0:
        s.sel()
        s.write(b'ABCDEF')
        s.unsel()
        time.sleep(.050)
