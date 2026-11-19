/* Portable ST7735S driver.  Init sequence ported verbatim from the original
 * firmware's `coldregs` table (firmware/st7735.fs). */
#include "st7735.h"

/* 12-bit pixel packing state (2 pixels -> 3 bytes) */
static uint8_t px_nib;
static bool px_half;

/* ST7735 command codes (subset). */
enum {
    NOP = 0x00, SWRESET = 0x01, SLPOUT = 0x11, NORON = 0x13, INVOFF = 0x20,
    INVON = 0x21, DISPOFF = 0x28, DISPON = 0x29, CASET = 0x2A, RASET = 0x2B,
    RAMWR = 0x2C, MADCTL = 0x36, COLMOD = 0x3A, FRMCTR1 = 0xB1,
    FRMCTR2 = 0xB2, FRMCTR3 = 0xB3, INVCTR = 0xB4, PWCTR1 = 0xC0,
    PWCTR2 = 0xC1, PWCTR3 = 0xC2, PWCTR4 = 0xC3, PWCTR5 = 0xC4,
    VMCTR1 = 0xC5, GMCTRP1 = 0xE0, GMCTRN1 = 0xE1,
};

static void cmd(const st7735_bus *bus, uint8_t c) {
    bus->dc(false);
    bus->cs(false);
    bus->write(c);
    bus->cs(true);
}

static void data(const st7735_bus *bus, uint8_t d) {
    bus->dc(true);
    bus->cs(false);
    bus->write(d);
    bus->cs(true);
}

void st7735_set_window(const st7735_bus *bus, uint16_t x0, uint16_t y0,
                       uint16_t x1, uint16_t y1) {
    cmd(bus, CASET);
    data(bus, 0x00);
    data(bus, (uint8_t)x0);
    data(bus, 0x00);
    data(bus, (uint8_t)x1);
    cmd(bus, RASET);
    data(bus, 0x00);
    data(bus, (uint8_t)y0);
    data(bus, 0x00);
    data(bus, (uint8_t)y1);
}

void st7735_init(const st7735_bus *bus) {
    cmd(bus, SWRESET);
    bus->delay_ms(120);
    cmd(bus, SLPOUT);
    bus->delay_ms(120);

    static const uint8_t fr1[] = {0x01, 0x2C, 0x2D};
    static const uint8_t fr2[] = {0x01, 0x2C, 0x2D};
    static const uint8_t fr3[] = {0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D};
    static const uint8_t pw1[] = {0xA2, 0x02, 0x84};
    static const uint8_t pw2[] = {0xC5};
    static const uint8_t pw3[] = {0x0A, 0x00};
    static const uint8_t pw4[] = {0x8A, 0x2A};
    static const uint8_t pw5[] = {0x8A, 0xEE};
    static const uint8_t vm1[] = {0x0E};
    static const uint8_t gp1[] = {0x02, 0x1C, 0x07, 0x12, 0x37, 0x32, 0x29,
                                  0x2D, 0x29, 0x25, 0x2B, 0x39, 0x00, 0x01,
                                  0x03, 0x10};
    static const uint8_t gn1[] = {0x03, 0x1D, 0x07, 0x06, 0x2E, 0x2C, 0x29,
                                  0x2D, 0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00,
                                  0x02, 0x10};

    struct { uint8_t c; const uint8_t *a; uint8_t n; } seq[] = {
        {FRMCTR1, fr1, 3}, {FRMCTR2, fr2, 3}, {FRMCTR3, fr3, 6},
        {PWCTR1, pw1, 3},   {PWCTR2, pw2, 1}, {PWCTR3, pw3, 2},
        {PWCTR4, pw4, 2},   {PWCTR5, pw5, 2}, {VMCTR1, vm1, 1},
    };
    for (unsigned i = 0; i < sizeof(seq) / sizeof(seq[0]); i++) {
        cmd(bus, seq[i].c);
        for (uint8_t j = 0; j < seq[i].n; j++) {
            data(bus, seq[i].a[j]);
        }
    }

    cmd(bus, MADCTL);
    data(bus, ST7735_MADCTL);
    cmd(bus, COLMOD);
    data(bus, 0x03); /* 12-bit color */

    cmd(bus, GMCTRP1);
    for (unsigned i = 0; i < 16; i++) data(bus, gp1[i]);
    cmd(bus, GMCTRN1);
    for (unsigned i = 0; i < 16; i++) data(bus, gn1[i]);

    cmd(bus, NORON);
    cmd(bus, DISPON);
}

void st7735_start_pixels(const st7735_bus *bus) {
    cmd(bus, RAMWR);
    bus->dc(true);
    bus->cs(false);
    px_half = false;
}

/* 12-bit color: the panel consumes exactly 12 bits per pixel (b4 g4 r4),
 * matching the original firmware's bit-banged nibble order.  Two pixels are
 * therefore packed into three bytes. */
void st7735_pixel(const st7735_bus *bus, uint8_t r4, uint8_t g4, uint8_t b4) {
    if (!px_half) {
        bus->write((uint8_t)((b4 << 4) | g4));
        px_nib = r4 & 0x0F;
        px_half = true;
    } else {
        bus->write((uint8_t)((px_nib << 4) | (b4 & 0x0F)));
        bus->write((uint8_t)((g4 << 4) | (r4 & 0x0F)));
        px_half = false;
    }
}

void st7735_end_pixels(const st7735_bus *bus) {
    if (px_half) {
        /* flush a trailing odd pixel: its last nibble + 4 pad bits */
        bus->write((uint8_t)(px_nib << 4));
        px_half = false;
    }
    bus->cs(true);
}

void st7735_fill_rect(const st7735_bus *bus, uint16_t x, uint16_t y,
                      uint16_t w, uint16_t h, uint8_t r4, uint8_t g4,
                      uint8_t b4) {
    st7735_set_window(bus, x, y, (uint16_t)(x + w - 1), (uint16_t)(y + h - 1));
    st7735_start_pixels(bus);
    uint32_t n = (uint32_t)w * h;
    for (uint32_t i = 0; i < n; i++) {
        st7735_pixel(bus, r4, g4, b4);
    }
    st7735_end_pixels(bus);
}
