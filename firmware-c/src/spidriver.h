/* SPIDriver firmware -- portable core.
 *
 * A C port of the original MyForth firmware (EFM8BB10) that implements the
 * SPIDriver host protocol: UART command transport, hardware-SPI transfers,
 * a logic-analyzer style ST7735S display, ADC measurements and a CCITT-16 CRC
 * accumulator.
 *
 * The core is target-independent.  Everything that touches hardware goes
 * through the `spidriver_hal` function table below; implement that table for
 * a given MCU (see pico/hal_pico.c for the RP2040 port).
 */
#ifndef SPIDRIVER_H
#define SPIDRIVER_H

#include <stdbool.h>
#include <stdint.h>

/* ADC channel indices passed to hal->adc_read(). */
enum {
    ADC_TEMP = 0, /* MCU temperature sensor */
    ADC_VBUS = 1, /* USB bus voltage (through a divider) */
    ADC_CURR = 2, /* target current sense (ZXCT1110 on the original board) */
};

/* Hardware abstraction.  All callbacks must be provided (led/lcd_reset may be
 * NULL).  Calibration values are in "raw16" units, where raw16 = raw12 << 4
 * (i.e. a full-scale 12-bit ADC read left-shifted to 16 bits). */
typedef struct spidriver_hal {
    /* --- SPI bus toward the device under test --- */
    void (*spi_select)(void);       /* assert CS */
    void (*spi_unselect)(void);     /* deassert CS */
    void (*spi_attach)(void);       /* drive SCK/MOSI/CS/A/B (re-init pins) */
    void (*spi_detach)(void);       /* tri-state SCK/MOSI (command 'x') */
    uint8_t (*spi_xfer)(uint8_t b); /* clock out one byte, return MISO byte */

    /* --- auxiliary GPIO --- */
    void (*set_a)(bool v); /* signal A */
    void (*set_b)(bool v); /* signal B */
    void (*led)(bool v);   /* optional status LED */

    /* --- UART transport (USB CDC, hardware UART, ...) --- */
    int16_t (*uart_get)(void); /* next byte, or -1 if none pending */
    void (*uart_put)(uint8_t b);

    /* --- time --- */
    uint32_t (*now_ms)(void);
    void (*delay_ms)(uint32_t ms);

    /* --- ADC --- */
    uint16_t (*adc_read)(unsigned ch); /* 12-bit result */

    /* --- ST7735S LCD bus --- */
    void (*lcd_cs)(bool v);
    void (*lcd_dc)(bool v);
    void (*lcd_write)(uint8_t b);
    void (*lcd_reset)(bool v); /* optional */

    /* --- calibration (raw16 scale) --- */
    int32_t cal_vbus_mv;      /* mV per raw16 for the VBUS divider */
    int32_t cal_current_ma;   /* mA per raw16 for the current sense */
    int32_t cal_current_zero; /* raw16 subtracted before scaling */
    int32_t cal_temp_coef;    /* deci-C per raw16 (positive, subtracted) */
    int32_t cal_temp_offset;  /* deci-C at raw16 == 0 */

    /* --- identity --- */
    const char *product; /* e.g. "spidriver1" */
    const char *serial;  /* e.g. "A0B1C2D3" */
} spidriver_hal;

/* Initialise core state and the display. */
void spidriver_init(spidriver_hal *hal);

/* Process one inbound byte if available.  Returns 1 if a byte was consumed,
 * 0 otherwise.  Call repeatedly from the main loop. */
int spidriver_service(spidriver_hal *hal);

/* 1 ms tick.  Call from a timer ISR or a polled millisecond loop. */
void spidriver_tick(spidriver_hal *hal);

/* Main loop: services the transport, refreshes measurements and redraws the
 * waveform display when needed.  Never returns. */
void spidriver_mainloop(spidriver_hal *hal);

#endif /* SPIDRIVER_H */
