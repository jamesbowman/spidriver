#ifndef SPIDRIVER_H
#define SPIDRIVER_H

#include <stdint.h>

#if defined(WIN32)
#include <windows.h>
#else
#define HANDLE int
#endif

typedef struct {
  int connected;          // Set to 1 when connected
  HANDLE port;
  char      model[16],
            serial[9];    // Serial number of USB device
  uint64_t  uptime;       // time since boot (seconds)
  float     voltage_v,    // USB voltage (Volts)
            current_ma,   // device current (mA)
            temp_celsius; // temperature (C)
  unsigned int a, b, cs;  // state of three output lines
  unsigned int
            ccitt_crc,    // Hardware CCITT CRC
            e_ccitt_crc;  // Host CCITT CRC, should match
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

int spi_commands(SPIDriver *sd, int argc, char *argv[]);

#endif
