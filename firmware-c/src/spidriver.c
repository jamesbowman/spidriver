/* SPIDriver firmware -- portable core.
 *
 * Implements the host protocol and measurement/display logic.  All hardware
 * access goes through the `spidriver_hal` table.  See spidriver.h.
 */
#include "spidriver.h"

#include <stdio.h>
#include <string.h>

#include "crc16.h"
#include "display.h"
#include "st7735.h"

/* ---- state ------------------------------------------------------------- */

#define HISTORY_N 14 /* waveform history depth (matches original 42-byte ring) */

static struct {
    uint16_t crc;          /* CCITT-16 accumulator (XMODEM) */
    uint32_t ms;           /* millisecond counter */
    uint32_t uptime;       /* seconds since boot */
    uint8_t slowc;         /* slow-refresh down-counter */
    bool dirty;            /* waveform needs redraw */

    uint8_t port;          /* bit3 = CS, bit6 = A, bit7 = B */
    bool attached;         /* SPI pins driven (false after 'x') */

    uint16_t ema_temp;     /* EMA of raw16 ADC samples */
    uint16_t ema_vbus;
    uint16_t ema_curr;

    int32_t vbus_mv;       /* computed measurements */
    int32_t cur_ma;
    int32_t temp_deciC;

    wave_entry_t history[HISTORY_N]; /* oldest -> newest */
    int hist_count;

    st7735_bus lcd;
} st;

/* ---- helpers ----------------------------------------------------------- */

static void log_entry(uint8_t code, uint8_t v0, uint8_t v1) {
    if (st.hist_count < HISTORY_N) {
        st.hist_count++;
    } else {
        memmove(&st.history[0], &st.history[1],
                (HISTORY_N - 1) * sizeof(wave_entry_t));
    }
    st.history[st.hist_count - 1].code = code;
    st.history[st.hist_count - 1].v0 = v0;
    st.history[st.hist_count - 1].v1 = v1;
    st.dirty = true;
}

/* Blocking receive (the original firmware's `key` blocks the same way). */
static uint8_t rx_wait(spidriver_hal *hal) {
    int16_t b;
    while ((b = hal->uart_get()) < 0) {
    }
    return (uint8_t)b;
}

static void tx(spidriver_hal *hal, uint8_t b) { hal->uart_put(b); }

static void connect(spidriver_hal *hal) {
    if (!st.attached) {
        hal->spi_attach();
        st.attached = true;
    }
    /* restore driven levels after a detach */
    hal->set_a((st.port >> 6) & 1);
    hal->set_b((st.port >> 7) & 1);
    if (st.port & 0x08) {
        hal->spi_unselect();
    } else {
        hal->spi_select();
    }
}

static void disconnect(spidriver_hal *hal) {
    hal->spi_detach();
    st.attached = false;
}

/* ---- measurements ------------------------------------------------------- */

static void read_adc(spidriver_hal *hal) {
    /* small box average per channel, then EMA with alpha=1/8 (replicating the
     * original `ema` word: new = (7*old + sample) / 8) */
    uint32_t s;

    s = 0;
    for (int i = 0; i < 4; i++) s += hal->adc_read(ADC_TEMP);
    uint16_t t = (uint16_t)((s / 4) << 4);
    st.ema_temp = (uint16_t)(((uint32_t)st.ema_temp * 7 + t) >> 3);

    s = 0;
    for (int i = 0; i < 4; i++) s += hal->adc_read(ADC_VBUS);
    uint16_t v = (uint16_t)((s / 4) << 4);
    st.ema_vbus = (uint16_t)(((uint32_t)st.ema_vbus * 7 + v) >> 3);

    s = 0;
    for (int i = 0; i < 4; i++) s += hal->adc_read(ADC_CURR);
    uint16_t c = (uint16_t)((s / 4) << 4);
    st.ema_curr = (uint16_t)(((uint32_t)st.ema_curr * 7 + c) >> 3);
}

static void conversions(spidriver_hal *hal) {
    read_adc(hal);

    st.vbus_mv = (int32_t)(((uint32_t)st.ema_vbus * (uint32_t)hal->cal_vbus_mv) >> 16);

    int32_t c = (int32_t)st.ema_curr - hal->cal_current_zero;
    if (c < 0) c = 0;
    st.cur_ma = (int32_t)(((uint32_t)c * (uint32_t)hal->cal_current_ma) >> 16);

    st.temp_deciC = hal->cal_temp_offset -
                    (int32_t)(((uint32_t)st.ema_temp *
                               (uint32_t)hal->cal_temp_coef) >> 16);
}

/* ---- status line -------------------------------------------------------- */

static void status(spidriver_hal *hal) {
    char buf[80];
    int n;

    uint16_t crc = crc16_bitreverse(st.crc);
    unsigned uptime = st.uptime > 99999 ? 99999 : (unsigned)st.uptime;
    int a = (st.port >> 6) & 1;
    int b = (st.port >> 7) & 1;
    int cs = (st.port >> 3) & 1;

    /* voltage as millivolts ("4.985"), current as mA ("43"), temp deci-C */
    int vmv = (int)st.vbus_mv;
    int vint = vmv / 1000;
    int vfrac = vmv % 1000;
    if (vfrac < 0) vfrac = -vfrac;
    int tint = (int)(st.temp_deciC / 10);
    int tfrac = (int)(st.temp_deciC % 10);
    if (tfrac < 0) tfrac = -tfrac;

    n = snprintf(buf, sizeof(buf), "[%s %s %5u %d.%03d %d %d.%d %d %d %d %04x",
                 hal->product, hal->serial, uptime, vint, vfrac, (int)st.cur_ma,
                 tint, tfrac, a, b, cs, crc);

    /* pad body to 78 chars, then closing bracket -> exactly 80 bytes */
    while (n < 79) {
        buf[n++] = ' ';
    }
    buf[n++] = ']';
    for (int i = 0; i < n; i++) {
        tx(hal, (uint8_t)buf[i]);
    }
}

/* ---- transport service -------------------------------------------------- */

int spidriver_service(spidriver_hal *hal) {
    int16_t b = hal->uart_get();
    if (b < 0) {
        return 0;
    }
    uint8_t cmd = (uint8_t)b;

    if (cmd & 0x80) {
        /* SPI transfer: 0x80-0xBF read/write, 0xC0-0xFF write-only */
        connect(hal);
        int n = (cmd & 0x3F) + 1;
        if (cmd & 0x40) {
            /* write-only */
            for (int i = 0; i < n; i++) {
                uint8_t w = rx_wait(hal);
                st.crc = crc16_xmodem_step(st.crc, w);
                hal->spi_xfer(w);
                log_entry('b', w, 0xFF);
            }
        } else {
            /* duplex: send, capture MISO, echo back */
            for (int i = 0; i < n; i++) {
                uint8_t w = rx_wait(hal);
                st.crc = crc16_xmodem_step(st.crc, w);
                uint8_t r = hal->spi_xfer(w);
                st.crc = crc16_xmodem_step(st.crc, r);
                tx(hal, r);
                log_entry('c', w, r);
            }
        }
        return 1;
    }

    switch (cmd) {
        case '?':
            status(hal);
            break;
        case 'e': {
            uint8_t c = rx_wait(hal);
            tx(hal, c);
            break;
        }
        case 's':
            connect(hal);
            log_entry('a', st.port, st.port);
            st.port &= ~0x08; /* CS asserted (low) */
            hal->spi_select();
            break;
        case 'u':
            connect(hal);
            log_entry('a', st.port, st.port);
            st.port |= 0x08; /* CS deasserted (high) */
            hal->spi_unselect();
            break;
        case 'a': {
            uint8_t v = rx_wait(hal);
            connect(hal);
            log_entry('a', st.port, st.port);
            if (v & 1) {
                st.port |= 0x40;
            } else {
                st.port &= ~0x40;
            }
            hal->set_a((v & 1) != 0);
            break;
        }
        case 'b': {
            uint8_t v = rx_wait(hal);
            connect(hal);
            log_entry('a', st.port, st.port);
            if (v & 1) {
                st.port |= 0x80;
            } else {
                st.port &= ~0x80;
            }
            hal->set_b((v & 1) != 0);
            break;
        }
        case 'x':
            log_entry('d', st.port, st.port);
            disconnect(hal);
            break;
        default:
            /* unknown bytes ('@', ...) are silently dropped, like the
             * original `service` */
            break;
    }
    return 1;
}

/* ---- tick --------------------------------------------------------------- */

void spidriver_tick(spidriver_hal *hal) {
    (void)hal;
    st.ms++;
    if (st.ms >= 1000) {
        st.ms = 0;
        st.uptime++;
    }
    if (st.slowc) {
        st.slowc--;
    }
}

/* ---- init & main loop ---------------------------------------------------- */

void spidriver_init(spidriver_hal *hal) {
    memset(&st, 0, sizeof(st));
    st.attached = true;
    st.port = 0x08; /* CS deasserted, A/B low */

    st.lcd.cs = hal->lcd_cs;
    st.lcd.dc = hal->lcd_dc;
    st.lcd.write = hal->lcd_write;
    st.lcd.delay_ms = hal->delay_ms;

    /* float/drive pins from a clean state */
    connect(hal);

    display_init(&st.lcd);

    /* boot self-test: show the colorbar briefly, then the normal screen */
    display_colorbar(&st.lcd);
    hal->delay_ms(1500);
    st7735_fill_rect(&st.lcd, 0, 0, ST7735_W, ST7735_H, 0, 0, 0);
    display_labels(&st.lcd);

    /* pre-converge the EMA filters so the first status read is sensible */
    for (int i = 0; i < 32; i++) {
        read_adc(hal);
    }
}

void spidriver_mainloop(spidriver_hal *hal) {
    for (;;) {
        /* measurements first (mirrors the original's parallel ADC thread) */
        conversions(hal);

        /* drain up to 64 commands, then refresh the display */
        for (int i = 0; i < 64; i++) {
            if (!spidriver_service(hal)) {
                break;
            }
        }

        if (st.dirty) {
            st.dirty = false;
            display_waves(&st.lcd, st.history, st.hist_count, st.port);
        }

        if (st.slowc == 0) {
            st.slowc = 250;
            display_results(&st.lcd, st.vbus_mv, st.cur_ma);
        }
    }
}
