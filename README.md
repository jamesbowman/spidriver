# SPIDriver

SPIDriver is a tool for controlling any SPI device from yout PC's USB port.
It connects as a standard USB serial device, so there are no drivers to install.
The serial protocol is so simple it,
amd there are included drivers for:

* Windows/Mac/Linux GUI
* Windows/Mac/Linux command-line
* Python 2 and 3
* Windows/Mac/Linux C/C++

SPIDriver's live display shows you exactly what it's doing all the time.

![flashexample](/images/DSC_1319a.JPG)

For example to read the 3-byte ID from this serial flash:

    >>> s = SpiDriver()
    >>> s.sel()
    >>> s.write(b'\x9f')
    >>> list(s.read(3))
    [239, 64, 24]
    >>>
