/* SPIDriver display rendering.  See display.h.
 *
 * The layout mirrors the original firmware (firmware/st7735.fs and
 * firmware/st7735s/mkfont.py): portrait 128x160, a top readings row, six
 * waveform rows whose labels sit on the right edge, hex annotation rows and
 * CS/A/B boxes.  Rendering is done in literal portrait coordinates
 * (ST7735_MADCTL), so no 90-degree window rotation is needed. */
#include "display.h"

#include <stdio.h>
#include <string.h>

#include "fonts.h"

/* ---- glyph lookup ----------------------------------------------------- */

static const big_glyph_t *big_lookup(char c) {
    for (unsigned i = 0; i < BIG_FONT_COUNT; i++) {
        if (big_font[i].ch == c) {
            return &big_font[i];
        }
    }
    return NULL;
}

static int text_width(const char *s) {
    int w = 0;
    for (; *s; s++) {
        if (*s == ' ') {
            w += 4;
        } else {
            const big_glyph_t *g = big_lookup(*s);
            if (g) {
                w += g->w;
            }
        }
    }
    return w;
}

static void draw_glyph(const st7735_bus *lcd, const big_glyph_t *g, int x,
                       int y, uint8_t r, uint8_t gr, uint8_t b) {
    st7735_set_window(lcd, (uint16_t)x, (uint16_t)y,
                      (uint16_t)(x + g->w - 1), (uint16_t)(y + g->h - 1));
    st7735_start_pixels(lcd);
    int npix = g->w * g->h;
    int nbytes = (npix + 1) / 2;
    for (int i = 0; i < nbytes; i++) {
        uint8_t px = g->bits[i];
        uint8_t hi = px >> 4;
        uint8_t lo = px & 0x0F;
        st7735_pixel(lcd, (uint8_t)(r * hi >> 4), (uint8_t)(gr * hi >> 4),
                     (uint8_t)(b * hi >> 4));
        if (i * 2 + 1 < npix) {
            st7735_pixel(lcd, (uint8_t)(r * lo >> 4), (uint8_t)(gr * lo >> 4),
                         (uint8_t)(b * lo >> 4));
        }
    }
    st7735_end_pixels(lcd);
}

static void draw_text(const st7735_bus *lcd, const char *s, int x, int y,
                      uint8_t r, uint8_t g, uint8_t b) {
    for (; *s; s++) {
        if (*s == ' ') {
            x += 4;
            continue;
        }
        const big_glyph_t *gl = big_lookup(*s);
        if (gl) {
            draw_glyph(lcd, gl, x, y, r, g, b);
            x += gl->w;
        }
    }
}

/* 4x5 micro font (hex digits), 2 px/byte. */
static void draw_micro(const st7735_bus *lcd, uint8_t nib, int x, int y,
                       uint8_t r, uint8_t g, uint8_t b) {
    const uint8_t *bits = micro_font[nib & 0x0F];
    st7735_set_window(lcd, (uint16_t)x, (uint16_t)y, (uint16_t)(x + 3),
                      (uint16_t)(y + 4));
    st7735_start_pixels(lcd);
    for (int i = 0; i < 10; i++) {
        uint8_t px = bits[i];
        st7735_pixel(lcd, (uint8_t)(r * (px >> 4) >> 4),
                     (uint8_t)(g * (px >> 4) >> 4),
                     (uint8_t)(b * (px >> 4) >> 4));
        st7735_pixel(lcd, (uint8_t)(r * (px & 0x0F) >> 4),
                     (uint8_t)(g * (px & 0x0F) >> 4),
                     (uint8_t)(b * (px & 0x0F) >> 4));
    }
    st7735_end_pixels(lcd);
}

/* ---- layout ------------------------------------------------------------ */

/* Waveform labels: name, y, color (r,g,b), x offset from 112-w/2. */
typedef struct {
    const char *name;
    int y;
    uint8_t r, g, b;
    int dx;
} label_t;

static const label_t labels[6] = {
    {"SCK", 39, 15, 9, 2, -2},
    {"MISO", 60, 15, 14, 2, 0},
    {"MOSI", 81, 8, 15, 2, 0},
    {"CS", 102, 1, 9, 15, -1},
    {"A", 123, 13, 7, 13, 0},
    {"B", 144, 8, 8, 6, 0},
};

#define WAVE_X 0
#define WAVE_W 90
#define WAVE_H 9

/* entry width in waveform columns (matches original `width` table) */
static int entry_width(uint8_t code) {
    switch (code) {
        case 'x':
            return 7;
        case 'a':
            return 18;
        case 'b':
            return 18;
        case 'c':
            return 18; /* duplex bytes get the same 18-col waveform as 'b' */
        default:
            return 8;
    }
}

/* ---- init & static text ------------------------------------------------ */

void display_labels(const st7735_bus *lcd) {
    for (int i = 0; i < 6; i++) {
        int x = 112 - text_width(labels[i].name) / 2 + labels[i].dx;
        draw_text(lcd, labels[i].name, x, labels[i].y, labels[i].r, labels[i].g,
                  labels[i].b);
    }
    draw_text(lcd, "V", 45, 12, 15, 15, 15);
    draw_text(lcd, "mA", 98, 12, 15, 15, 15);
}

void display_init(const st7735_bus *lcd) {
    st7735_init(lcd);
    st7735_fill_rect(lcd, 0, 0, ST7735_W, ST7735_H, 0, 0, 0);
    display_labels(lcd);
}

/* Boot self-test: eight 16-px vertical bars (black, red, green, blue,
 * yellow, magenta, cyan, white).  Correct colors = panel wired + packed
 * right; scrambled channels = color-order/packing problem. */
void display_colorbar(const st7735_bus *lcd) {
    static const uint8_t bars[8][3] = {
        {0, 0, 0},     {15, 0, 0},    {0, 15, 0},   {0, 0, 15},
        {15, 15, 0},   {15, 0, 15},   {0, 15, 15},  {15, 15, 15},
    };
    for (int i = 0; i < 8; i++) {
        st7735_fill_rect(lcd, (uint16_t)(i * 16), 0, 16, ST7735_H, bars[i][0],
                         bars[i][1], bars[i][2]);
    }
}

/* ---- top readings ------------------------------------------------------- */

/* Render "x.yz" (millivolts) and a 3-column right-aligned milliamp value. */
static void draw_number(const st7735_bus *lcd, int x, int y, const char *s) {
    draw_text(lcd, s, x, y, 15, 15, 15);
}

void display_results(const st7735_bus *lcd, int32_t vbus_mv, int32_t cur_ma) {
    char buf[16];

    /* voltage: "%d.%02d" from centivolts */
    int32_t cv = vbus_mv / 10;
    int iv = (int)(cv / 100);
    int fv = (int)(cv % 100);
    if (fv < 0) fv = -fv;
    if (iv < 0) iv = -iv;

    /* clear exactly the previous text extent, then draw (the fixed-width
     * clear rect used to clip the neighbouring V/mA labels) */
    int len = snprintf(buf, sizeof(buf), "%d.%02d", iv, fv);
    (void)len;
    int w = text_width(buf);
    st7735_fill_rect(lcd, 12, 12, (uint16_t)w, 9, 0, 0, 0);
    draw_number(lcd, 12, 12, buf);

    len = snprintf(buf, sizeof(buf), "%3d", (int)cur_ma);
    (void)len;
    w = text_width(buf);
    st7735_fill_rect(lcd, 70, 12, (uint16_t)w, 9, 0, 0, 0);
    draw_number(lcd, 70, 12, buf);
}

/* ---- waveform rendering ------------------------------------------------- */

/* 90x9 strip framebuffer: intensity 0..15 per pixel. */
static uint8_t strip[WAVE_W * WAVE_H];

static void strip_clear(void) { memset(strip, 0, sizeof(strip)); }

/* horizontal line helper into the framebuffer */
static void hline(int x0, int x1, int y, uint8_t v) {
    if (y < 0 || y >= WAVE_H) return;
    if (x0 > x1) { int t = x0; x0 = x1; x1 = t; }
    if (x0 < 0) x0 = 0;
    if (x1 >= WAVE_W) x1 = WAVE_W - 1;
    for (int x = x0; x <= x1; x++) {
        strip[y * WAVE_W + x] = v;
    }
}

static void vline(int x, int y0, int y1, uint8_t v) {
    if (x < 0 || x >= WAVE_W) return;
    if (y0 > y1) { int t = y0; y0 = y1; y1 = t; }
    if (y0 < 0) y0 = 0;
    if (y1 >= WAVE_H) y1 = WAVE_H - 1;
    for (int y = y0; y <= y1; y++) {
        strip[y * WAVE_W + x] = v;
    }
}

#define TOP 0
#define BOT 8
#define FULL 15
#define DIM 7

/* Draw a byte as a bit waveform across [x0, x0+w).  level high/low.
 * prev_level: the signal level just before this byte (TOP/BOT, or -1).
 * Returns the level at the end of the byte. */
static int draw_byte_wave(int x0, int w, uint8_t byte, bool invert,
                         int prev_level) {
    /* transition from previous byte's tail to this byte's first bit */
    int first_b = (byte >> 7) & 1;
    if (invert) first_b = 1 - first_b;
    int first_y = first_b ? TOP : BOT;
    if (prev_level >= 0 && first_y != prev_level) {
        vline(x0, TOP, BOT, FULL);
    }

    int x = x0;
    for (int bit = 0; bit < 8; bit++) {
        int b = (byte >> (7 - bit)) & 1;
        if (invert) b = 1 - b;
        int y = b ? TOP : BOT;
        int nx = x + 2;
        if (nx > x0 + w) nx = x0 + w;
        hline(x, nx - 1, y, FULL);
        x = nx;
    }
    /* fill trailing columns at idle (BOT); draw a falling edge if the
     * last bit was high */
    if (x < x0 + w) {
        int b = byte & 1;
        if (invert) b = 1 - b;
        if (b) {
            vline(x, TOP, BOT, FULL);
            if (x + 1 < x0 + w) {
                hline(x + 1, x0 + w - 1, BOT, FULL);
            }
        } else {
            hline(x, x0 + w - 1, BOT, FULL);
        }
    }
    /* vertical transitions between bit levels */
    x = x0;
    int prev = -1;
    for (int bit = 0; bit < 8; bit++) {
        int b = (byte >> (7 - bit)) & 1;
        if (invert) b = 1 - b;
        int y = b ? TOP : BOT;
        if (prev >= 0 && y != prev) {
            vline(x, TOP, BOT, FULL);
        }
        prev = y;
        x += 2;
    }
    int last_b = byte & 1;
    if (invert) last_b = 1 - last_b;
    (void)last_b;
    return BOT; /* trailing edge always returns to idle */
}

/* Render one strip row. */
static void render_row(const st7735_bus *lcd, const wave_entry_t *entries, int n,
                       uint8_t port, int row, uint8_t r, uint8_t g, uint8_t b) {
    (void)lcd;
    strip_clear();

    /* walk entries newest-first, place right-to-left */
    int x = WAVE_W;
    int prev_level = BOT;   /* idle line level, tracked across byte entries */
    uint8_t hist_port = port; /* port state, walks backward through history */
    for (int i = n - 1; i >= 0 && x > 0; i--) {
        const wave_entry_t *e = &entries[i];
        int w = entry_width(e->code);
        x -= w;
        if (x < 0) {
            x = 0;
            w = WAVE_W; /* clamp trailing entry */
        }

        switch (row) {
            case 0: /* SCK: 8 clock pulses per byte, dim on disconnect */
                if (e->code == 'x') {
                    hline(x, x + w - 1, TOP, DIM);
                    hline(x, x + w - 1, BOT, DIM);
                } else if (e->code == 'b' || e->code == 'c') {
                    hline(x, x + w - 1, BOT, FULL); /* baseline */
                    for (int bit = 0; bit < 8; bit++) {
                        int px = x + 1 + bit * 2;
                        if (px >= x + w) break;
                        vline(px, TOP, BOT, FULL);
                    }
                } else if (e->code == 'a') {
                    hline(x, x + w - 1, BOT, FULL);
                }
                break;
            case 1: /* MISO: 'c' entries */
                if (e->code == 'x') {
                    hline(x, x + w - 1, TOP, DIM);
                    hline(x, x + w - 1, BOT, DIM);
                } else if (e->code == 'c') {
                    prev_level = draw_byte_wave(x, w, e->v1, false, prev_level);
                } else if (e->code == 'a') {
                    hline(x, x + w - 1, BOT, FULL);
                }
                break;
            case 2: /* MOSI: write-only ('b') AND duplex ('c') clock data
                       out -- the original matches entry-type bit 1 */
                if (e->code == 'x') {
                    hline(x, x + w - 1, TOP, DIM);
                    hline(x, x + w - 1, BOT, DIM);
                } else if (e->code == 'b' || e->code == 'c') {
                    prev_level = draw_byte_wave(x, w, e->v0, false, prev_level);
                } else if (e->code == 'a') {
                    hline(x, x + w - 1, BOT, FULL);
                }
                break;
            default: { /* CS/A/B: port bits, mask per row */
                uint8_t mask = (row == 3) ? 0x08 : (row == 4) ? 0x40 : 0x80;
                if (e->code == 'x') {
                    hline(x, x + w - 1, TOP, DIM);
                    hline(x, x + w - 1, BOT, DIM);
                } else if (e->code == 'a') {
                    /* v0 = port state BEFORE this change; hist_port is the
                     * state AFTER (to the right).  Draw new state, then a
                     * transition edge at the left boundary to the old state. */
                    bool new_bit = (hist_port & mask) != 0;
                    bool old_bit = (e->v0 & mask) != 0;
                    int new_y = new_bit ? TOP : BOT;
                    hline(x, x + w - 1, new_y, FULL);
                    if (old_bit != new_bit) {
                        vline(x, TOP, BOT, FULL);
                    }
                    hist_port = e->v0; /* state before, for entries to the left */
                } else {
                    int y = (hist_port & mask) ? TOP : BOT;
                    hline(x, x + w - 1, y, FULL);
                }
                break;
            }
        }
    }

    /* blit */
    int ytop = labels[row].y;
    st7735_set_window(lcd, WAVE_X, (uint16_t)ytop, WAVE_X + WAVE_W - 1,
                      (uint16_t)(ytop + WAVE_H - 1));
    st7735_start_pixels(lcd);
    for (int y = 0; y < WAVE_H; y++) {
        for (int xx = 0; xx < WAVE_W; xx++) {
            uint8_t v = strip[y * WAVE_W + xx];
            st7735_pixel(lcd, (uint8_t)(r * v >> 4), (uint8_t)(g * v >> 4),
                         (uint8_t)(b * v >> 4));
        }
    }
    st7735_end_pixels(lcd);
}

/* hexadecimal annotation row (matches original `annotate`) */
static void annotate(const st7735_bus *lcd, const wave_entry_t *entries, int n,
                     int y, bool mosi) {
    st7735_fill_rect(lcd, 0, (uint16_t)y, 90, 5, 0, 0, 0);
    int x = WAVE_W;
    for (int i = n - 1; i >= 0 && x > 0; i--) {
        const wave_entry_t *e = &entries[i];
        int w = entry_width(e->code);
        x -= w;
        if (x < 0) break;
        bool match = mosi ? (e->code == 'b' || e->code == 'c')
                          : (e->code == 'c');
        if (match) {
            uint8_t byte = mosi ? e->v0 : e->v1;
            draw_micro(lcd, byte >> 4, x, y, 15, 15, 15);
            draw_micro(lcd, byte & 0x0F, x + 5, y, 15, 15, 15);
        }
    }
}

/* CS/A/B state boxes (outline only, bright when the signal is high) */
static void boxes(const st7735_bus *lcd, uint8_t port) {
    for (int i = 3; i < 6; i++) {
        uint8_t mask = (i == 3) ? 0x08 : (i == 4) ? 0x40 : 0x80;
        bool on = (port & mask) != 0;
        uint8_t r = labels[i].r, g = labels[i].g, b = labels[i].b;
        if (!on) { r = g = b = 0; }
        int bx = 97, by = labels[i].y - 3;
        st7735_fill_rect(lcd, (uint16_t)bx, (uint16_t)by, 30, 1, r, g, b);
        st7735_fill_rect(lcd, (uint16_t)bx, (uint16_t)(by + 14), 30, 1, r, g,
                         b);
        st7735_fill_rect(lcd, (uint16_t)bx, (uint16_t)by, 1, 15, r, g, b);
        st7735_fill_rect(lcd, (uint16_t)(bx + 29), (uint16_t)by, 1, 15, r, g,
                         b);
    }
}

void display_waves(const st7735_bus *lcd, const wave_entry_t *entries, int n,
                   uint8_t port) {
    for (int i = 0; i < 6; i++) {
        render_row(lcd, entries, n, port, i, labels[i].r, labels[i].g,
                   labels[i].b);
    }
    annotate(lcd, entries, n, 70, false); /* MISO */
    annotate(lcd, entries, n, 91, true);  /* MOSI */
    boxes(lcd, port);
}
