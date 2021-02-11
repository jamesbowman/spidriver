# coding=utf-8
from setuptools import setup

LONG = """\
SPIDriver is a tool for controlling any SPI device from your PC's USB port. It connects as a standard USB serial device, so there are no drivers to install."""

for l in open("spidriver.py", "rt"):
    if l.startswith("__version__"):
        exec(l)

setup(name='spidriver',
      version=__version__,
      author='James Bowman',
      author_email='jamesb@excamera.com',
      url='https://spidriver.com',
      description='SPIDriver is a desktop SPI interface',
      long_description=LONG,
      license='GPL',
      py_modules=['spidriver'],
      install_requires=['pyserial'],
      project_urls={
        'Documentation': 'https://spidriver.readthedocs.io/en/latest/',
      }
      )
