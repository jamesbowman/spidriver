![logo](/images/logo.png)

[![Build Status](https://travis-ci.org/jamesbowman/spidriver.svg?branch=master)](https://travis-ci.org/jamesbowman/spidriver)

SPIDriver is a tool for controlling any SPI device from your PC's USB port.
It connects as a standard USB serial device, so there are no drivers to install.
The serial protocol is so simple it fits on the [back of the PCB](/images/DSC_1315a.JPG),
and there are included drivers for

* Windows/Mac/Linux GUI
* Windows/Mac/Linux command-line
* Python 2 and 3
* Windows/Mac/Linux C/C++

![front](/images/DSC_1313a.JPG)

Features:

* live display shows you exactly what it's doing all the time
* sustained SPI transfers at 500 Kbps
* USB line voltage monitor to detect supply problems
* target device current measurement
* two auxiliary control lines, A and B
* dedicated power out lines. 2 each of GND, 3.3 V and 5 V. Up to 500 mA total
* signals color coded to match jumper colors
* all signals are 3.3 V, and are 5 V tolerant
* uses an FTDI USB serial adapter, and Silicon Labs automotive-grade microcontroller
* also reports uptime, temperature and running CRC of all traffic
* all sensors and signals controlled over serial

![flashexample](/images/DSC_1319a.JPG)

For example to read the 3-byte ID from this serial flash in Python:

    >>> s = SpiDriver()
    >>> s.sel()               # start command
    >>> s.write(b'\x9f')      # command 9F is READ JEDEC ID 
    >>> list(s.read(3))       # read next 3 bytes
    [239, 64, 24]
    >>> s.unsel()             # end command
    >>>

or using the command line:

    $ spi s t 0x9f r 3 u
    0xef,0x40,0x18
    $

![flashexample2](/images/DSC_1319b.JPG)
