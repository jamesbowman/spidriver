#include <stdio.h>
#include <stdlib.h>

#include "spidriver.h"

int main(int argc, char *argv[])
{
  SPIDriver sd;
  if (argc < 2) {
    printf("Usage: spicl <PORTNAME> <commands>\n");
    exit(1);
  } else {
    spi_connect(&sd, argv[1]);
    if (!sd.connected)
      exit(1);
    return spi_commands(&sd, argc - 2, argv + 2);
  }
}
