spidriver
=========

.. image:: /images/spidriver-main-600.jpg
   :target: https://spidriver.com

`SPIDriver <https:spidriver.com>`_
is an easy-to-use, open source tool for controlling SPI devices over USB.
It works with Windows, Mac, and Linux, and has a built-in color screen
that shows a live "dashboard" of all the SPI activity.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

The SPIDriver User Guide has complete information on the hardware:

https://spidriver.com/spidriver.pdf

System Requirements
===================

Because it is a pure Python module, ``spidriver`` can run on any system supported by ``pyserial``.
This includes:

- Windows 7 or 10
- Mac OS
- Linux, including all Ubuntu distributions

Both Python 2.7 and 3.x are supported.

Installation
============

The ``spidriver`` package can be installed from PyPI using ``pip``::

    $ pip install spidriver

Quick start
===========

To connect to an SPI flash and read its JEDEC id:

    >>> from spidriver import SPIDriver
    >>> s = SPIDriver("/dev/ttyUSB0") # change for your port
    >>> s.sel() # start command
    >>> s.write([0x9f]) # command 9F is READ JEDEC ID
    >>> list(s.read(3)) # read next 3 bytes
    [239, 64, 24]
    >>> s.unsel() # end command

The User Guide at https://spidriver.com/spidriver.pdf has more examples,
as does the
`SPIDriver repo on github <https://github.com/jamesbowman/spidriver/tree/master/python/samples>`_.

Module Contents
===============

.. autoclass:: spidriver.SPIDriver
   :member-order: bysource
   :members:
      sel,
      unsel,
      detach,
      read,
      write,
      writeread,
      seta,
      setb,
      setmode,
      getstatus

