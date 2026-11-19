/* CRC-16/XMODEM (poly 0x1021, init 0x0000, MSB-first). */
#ifndef SPIDRIVER_CRC16_H
#define SPIDRIVER_CRC16_H

#include <stdint.h>

uint16_t crc16_xmodem_step(uint16_t crc, uint8_t byte);
uint16_t crc16_bitreverse(uint16_t v);

#endif
