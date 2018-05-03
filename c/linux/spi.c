#include <stdio.h>
#include <stdlib.h>

#include "spidriver.h"

int main(int argc, char *argv[])
{
  SPIDriver sd;
  spi_connect(&sd, "/dev/ttyUSB0");
  return spi_commands(&sd, argc - 1, argv + 1);
}
