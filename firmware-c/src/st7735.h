/* Portable ST7735S driver (128x160, 12-bit color), driven through a byte
 * write callback so any SPI/bit-bang transport can back it. */
#ifndef SPIDRIVER_ST7735_H
#define SPIDRIVER_ST7735_H

#include <stdbool.h>
#include <stdint.h>

#define ST7735_W 128
#define ST7735_H 160

/* Panel orientation.  The original firmware used MADCTL 0xC8 for the static
 * text and 0xA8 for the (90-deg rotated) waveform strips.  This port draws
 * everything in plain portrait coordinates with one orientation value.
 * 0x08 = portrait, BGR color order.  If your panel is mounted the other way
 * up, change this to 0xC8 (or 0x68 / 0xE8). */
#ifndef ST7735_MADCTL
#define ST7735_MADCTL 0x08
#endif

typedef struct st7735_bus {
    void (*cs)(bool v);
    void (*dc)(bool v);  /* 0 = command, 1 = data */
    void (*write)(uint8_t b);
    void (*delay_ms)(uint32_t ms);
} st7735_bus;

void st7735_init(const st7735_bus *bus);

/* Set the write window.  Coordinates are literal screen pixels. */
void st7735_set_window(const st7735_bus *bus, uint16_t x0, uint16_t y0,
                       uint16_t x1, uint16_t y1);

/* Begin streaming raw pixels into the current window; call
 * st7735_pixel() N times (w*h) then st7735_end_pixels().  Pixels are 12-bit
 * (b4 g4 r4), packed two-per-three-bytes like the original firmware. */
void st7735_start_pixels(const st7735_bus *bus);
void st7735_pixel(const st7735_bus *bus, uint8_t r4, uint8_t g4, uint8_t b4);
void st7735_end_pixels(const st7735_bus *bus);

/* Fill a rectangle with a 12-bit color. */
void st7735_fill_rect(const st7735_bus *bus, uint16_t x, uint16_t y,
                      uint16_t w, uint16_t h, uint8_t r4, uint8_t g4,
                      uint8_t b4);

#endif
