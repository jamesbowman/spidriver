#ifndef SPIDRIVER_H
#define SPIDRIVER_H

#include <stdint.h>

#if defined(WIN32)
#include <windows.h>
#else
#define HANDLE int
#endif

typedef struct {
  HANDLE port;
  char model[16], serial[9];
  uint64_t uptime;
  float voltage_v, current_ma, temp_celsius;
  unsigned int a, b, cs;
  unsigned int debug;
} SPIDriver;

void spi_connect(SPIDriver *sd, const char* portname);
void spi_getstatus(SPIDriver *sd);
void spi_sel(SPIDriver *sd);
void spi_unsel(SPIDriver *sd);
void spi_seta(SPIDriver *sd, char v);
void spi_setb(SPIDriver *sd, char v);
void spi_write(SPIDriver *sd, const char bytes[], size_t nn);
void spi_read(SPIDriver *sd, char bytes[], size_t nn);
void spi_writeread(SPIDriver *sd, char bytes[], size_t nn);

#endif
