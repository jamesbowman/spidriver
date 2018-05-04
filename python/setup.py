from setuptools import setup

LONG="""\
SPIDriver is a tool for controlling any SPI device from your PC's USB port. It connects as a standard USB serial device, so there are no drivers to install."""

setup(name='spidriver',
      version='0.0.1',
      author='James Bowman',
      author_email='jamesb@excamera.com',
      url='http://spidriver.com',
      description='SPIDriver is a desktop SPI interface',
      long_description=LONG,
      license='GPL',
      py_modules=['spidriver'],
      install_requires=['pyserial']
)
