/* SPIDriver display: ST7735S logic-analyzer view.
 *
 * Re-implements the visual layout of the original firmware: a status line
 * (voltage/current), six labelled waveform strips (SCK, MISO, MOSI, CS, A, B),
 * hexadecimal annotation rows, and CS/A/B indicator boxes.
 */
#ifndef SPIDRIVER_DISPLAY_H
#define SPIDRIVER_DISPLAY_H

#include <stdint.h>

#include "st7735.h"

/* One waveform record: code 'b' = MOSI byte, 'c' = MISO byte, 'a' = port
 * change, 'd' = disconnect; v0/v1 are payload depending on code. */
typedef struct {
    uint8_t code;
    uint8_t v0;
    uint8_t v1;
} wave_entry_t;

void display_init(const st7735_bus *lcd); /* init panel + static labels */
void display_labels(const st7735_bus *lcd); /* redraw the static text */
void display_colorbar(const st7735_bus *lcd); /* boot self-test pattern */
void display_results(const st7735_bus *lcd, int32_t vbus_mv, int32_t cur_ma);

/* Render the waveform strips.  `entries` is newest-last (entries[0] oldest,
 * entries[n-1] newest).  `port` carries the CS/A/B bits: bit3 = CS, bit6 = A,
 * bit7 = B (same layout as the original firmware's P0 port). */
void display_waves(const st7735_bus *lcd, const wave_entry_t *entries, int n,
                   uint8_t port);

#endif
