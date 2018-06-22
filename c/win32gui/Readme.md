# MinGW Win32 Application

## Table of Contents

- [Introduction](#introduction)
- [Terms of Use](#terms-of-use)
- [Problems?](#problems)
- [Changelog](#changelog)

## Introduction

This application is an example Windows GUI application, written to demonstrate
how this can be done using MinGW. It accompanies the
[Win32 Apps with MinGW](http://www.transmissionzero.co.uk/computing/win32-apps-with-mingw/)
article on [Transmission Zero](http://www.transmissionzero.co.uk/).

To build the application on a Windows machine, open a command prompt, change to
the directory containing the Makefile, and type "mingw32-make". The application
should be compiled, linked, and output as "Win32App.exe".

To compile an ANSI build (i.e. if you want the application to run under Windows
9x), run "mingw32-make CHARSET=ANSI" from the command prompt.

To build under another operating system, the Makefile will probably require
some small changes. For example, under Fedora the C compiler and resource
compiler are named "i686-pc-mingw32-gcc" and "i686-pc-mingw32-windres". Also,
your version of the make utility may be named differently--please check the
documentation which came with your MinGW packages.

It should also be possible to build the application using any C or C++ compiler
which supports targeting Windows, for example Microsoft Visual C++ and Open
Watcom. You will of course need to set the projects up for yourself if you do
that. No source code modifications are required if you want to build a 64 bit
version of the application.

## Terms of Use

Refer to "License.txt" for terms of use.

## Problems?

If you have any problems or questions, please ensure you have read this readme
file and the
[Win32 Apps with MinGW](http://www.transmissionzero.co.uk/computing/win32-apps-with-mingw/)
article. If you are still having trouble, you can
[get in contact](http://www.transmissionzero.co.uk/contact/).

## Changelog

5. 2016-08-27: Version 1.4
  - Added "supportedOS" to application manifest to indicate compatibility with
    Windows Vista to Windows 10.

4. 2013-12-15: Version 1.3
  - Added CHARSET variable to makefile so that an ANSI build can be compiled if
    required.
  - Updated image loading code for window class so that the correct small icon
    is loaded on Windows 9x.

3. 2013-08-26: Version 1.2
  - Minor tweaks to the VERSIONINFO resource so that it uses constants rather
    than magic numbers.
  - Modified "processorArchitecture" for common controls library in manifest, to
    avoid errors when the application is built for and run on a 64 bit OS.

2. 2011-07-02: Version 1.1
  - Minor tweaks to the code for consistency between Win16 and Win32 versions.
  - Minor tweaks to the Makefile for consistency.

1. 2011-04-13: Version 1.0
  - Initial release.

Transmission Zero
2016-08-27
