/* CRC-16/XMODEM (CCITT-FALSE), matching the EFM8 hardware CRC unit in the
 * original firmware (CRC0CN0 = 0b1100: poly 0x1021, MSB-first input, init 0).
 *
 * The original firmware reports `crc16_bitreverse(accumulator)` in its status
 * line, because the EFM8 CRCPNT=11 field bit-and-byte-reverses the result.
 */
#include "crc16.h"

uint16_t crc16_xmodem_step(uint16_t crc, uint8_t byte) {
    crc ^= (uint16_t)byte << 8;
    for (int i = 0; i < 8; i++) {
        if (crc & 0x8000) {
            crc = (uint16_t)((crc << 1) ^ 0x1021);
        } else {
            crc = (uint16_t)(crc << 1);
        }
    }
    return crc;
}

uint16_t crc16_bitreverse(uint16_t v) {
    uint16_t r = 0;
    for (int i = 0; i < 16; i++) {
        r = (uint16_t)((r << 1) | (v & 1));
        v >>= 1;
    }
    return r;
}
