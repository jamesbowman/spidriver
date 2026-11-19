/* SPIDriver firmware -- Raspberry Pi Pico (RP2040) port.
 *
 * Pin map (all configurable below; both SPI buses are hardware SPI):
 *
 *   GPIO2  SCK      LCD (SPI0)          GPIO10 SCK      target SPI (SPI1)
 *   GPIO3  MOSI     LCD                 GPIO11 MOSI     target SPI
 *   GPIO4  DC       LCD                 GPIO8  MISO     target SPI
 *   GPIO5  CS       LCD                 GPIO9  CS       target SPI
 *   GPIO6  A        signal output
 *   GPIO7  B        signal output
 *   GPIO26 VBUS sense (ADC0)            GPIO27 current sense (ADC1)
 *   internal ADC4  temperature sensor
 *
 * LCD RESET is not wired; tie it to 3V3 (as on the original board).
 * Note: RP2040 hardware SPI pins are fixed sets, so the target MOSI cannot
 * sit on physical pins 9-13; GP11 (pin 15) is the closest SPI1 TX option.
 *
 * The transport is USB CDC (TinyUSB); the original board's FTDI UART is not
 * needed because the RP2040 has a native USB controller.
 */
#include <stdbool.h>
#include <stdint.h>

#include "bsp/board.h"
#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "hardware/spi.h"
#include "hardware/timer.h"
#include "pico/stdlib.h"
#include "tusb.h"

#include "../src/spidriver.h"
#include "usb_descriptors.h"

/* ---- pin map ---- */
/* LCD on SPI0 (physical pins 4-7); target on SPI1 (pins 9-13 where possible) */
#define PIN_LCD_SCK 2
#define PIN_LCD_MOSI 3
#define PIN_LCD_DC 4
#define PIN_LCD_CS 5

#define PIN_T_SCK 10
#define PIN_T_MOSI 11
#define PIN_T_MISO 8
#define PIN_T_CS 9
#define PIN_A 6
#define PIN_B 7

#define PIN_VBUS_ADC 26
#define PIN_CURR_ADC 27

/* target SPI clock; the original EFM8 ran ~490 kHz */
#ifndef SPI_TARGET_HZ
#define SPI_TARGET_HZ 500000
#endif
#define SPI_LCD_HZ 16000000

static spidriver_hal g_hal;

/* ---- SPI target bus ---- */

static void spi_target_pins_drive(void) {
    gpio_set_function(PIN_T_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_T_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_T_MISO, GPIO_FUNC_SPI);
    gpio_init(PIN_T_CS);
    gpio_set_dir(PIN_T_CS, GPIO_OUT);
    gpio_init(PIN_A);
    gpio_set_dir(PIN_A, GPIO_OUT);
    gpio_init(PIN_B);
    gpio_set_dir(PIN_B, GPIO_OUT);
}

static void spi_target_pins_float(void) {
    gpio_set_function(PIN_T_SCK, GPIO_FUNC_NULL);
    gpio_set_dir(PIN_T_SCK, GPIO_IN);
    gpio_set_function(PIN_T_MOSI, GPIO_FUNC_NULL);
    gpio_set_dir(PIN_T_MOSI, GPIO_IN);
    gpio_set_function(PIN_T_MISO, GPIO_FUNC_NULL);
    gpio_set_dir(PIN_T_MISO, GPIO_IN);
    gpio_set_dir(PIN_T_CS, GPIO_IN);
    gpio_set_dir(PIN_A, GPIO_IN);
    gpio_set_dir(PIN_B, GPIO_IN);
}

static void spi_select(void) { gpio_put(PIN_T_CS, 0); }
static void spi_unselect(void) { gpio_put(PIN_T_CS, 1); }
static void spi_attach(void) { spi_target_pins_drive(); }
static void spi_detach(void) { spi_target_pins_float(); }

static uint8_t spi_xfer(uint8_t b) {
    uint8_t r = 0;
    spi_write_read_blocking(spi1, &b, &r, 1);
    return r;
}

/* ---- GPIO ---- */
static void set_a(bool v) { gpio_put(PIN_A, v ? 1 : 0); }
static void set_b(bool v) { gpio_put(PIN_B, v ? 1 : 0); }
static void led(bool v) {
#ifdef PICO_DEFAULT_LED_PIN
    gpio_put(PICO_DEFAULT_LED_PIN, v ? 1 : 0);
#else
    (void)v;
#endif
}

/* ---- UART (USB CDC) ---- */
static int16_t uart_get(void) {
    tud_task();
    if (tud_cdc_available()) {
        uint8_t c;
        if (tud_cdc_read(&c, 1) == 1) {
            return (int16_t)c;
        }
    }
    return -1;
}

static void uart_put(uint8_t b) {
    while (!tud_cdc_write(&b, 1)) {
        tud_task();
    }
    /* this TinyUSB version only auto-flushes at >=64 queued bytes; small
     * packets (echo replies) would otherwise sit in the FIFO forever */
    tud_cdc_write_flush();
}

/* ---- time ---- */
static uint32_t now_ms(void) {
    return (uint32_t)to_ms_since_boot(get_absolute_time());
}

static void delay_ms(uint32_t ms) { sleep_ms(ms); }

/* ---- ADC ---- */
static uint16_t hal_adc_read(unsigned ch) {
    switch (ch) {
        case ADC_TEMP:
            adc_select_input(4); /* internal temperature sensor */
            break;
        case ADC_VBUS:
            adc_select_input(0); /* GPIO26 */
            break;
        case ADC_CURR:
            adc_select_input(1); /* GPIO27 */
            break;
        default:
            return 0;
    }
    return (uint16_t)adc_read();
}

/* ---- LCD bus (SPI0) ---- */
static void lcd_cs(bool v) { gpio_put(PIN_LCD_CS, v ? 1 : 0); }
static void lcd_dc(bool v) { gpio_put(PIN_LCD_DC, v ? 1 : 0); }

static void lcd_write(uint8_t b) {
    spi_write_blocking(spi0, &b, 1);
}

/* ---- tick ---- */
static bool tick_cb(struct repeating_timer *t) {
    (void)t;
    spidriver_tick(&g_hal);
    return true;
}

/* ---- init ---- */
static void hw_init(void) {
    /* LCD SPI (SPI0); no reset pin, LCD RESET tied to 3V3 externally */
    spi_init(spi0, SPI_LCD_HZ);
    gpio_set_function(PIN_LCD_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_LCD_MOSI, GPIO_FUNC_SPI);
    gpio_init(PIN_LCD_CS);
    gpio_set_dir(PIN_LCD_CS, GPIO_OUT);
    gpio_init(PIN_LCD_DC);
    gpio_set_dir(PIN_LCD_DC, GPIO_OUT);

    /* target SPI (SPI1) */
    spi_init(spi1, SPI_TARGET_HZ);
    spi_target_pins_drive();
    gpio_put(PIN_T_CS, 1);

    /* ADC */
    adc_init();
    adc_gpio_init(PIN_VBUS_ADC);
    adc_gpio_init(PIN_CURR_ADC);
    adc_set_temp_sensor_enabled(true);

    /* LED */
#ifdef PICO_DEFAULT_LED_PIN
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
#endif
}

int main(void) {
    board_init();
    hw_init();
    tud_init(BOARD_TUD_RHPORT);

    g_hal.spi_select = spi_select;
    g_hal.spi_unselect = spi_unselect;
    g_hal.spi_attach = spi_attach;
    g_hal.spi_detach = spi_detach;
    g_hal.spi_xfer = spi_xfer;
    g_hal.set_a = set_a;
    g_hal.set_b = set_b;
    g_hal.led = led;
    g_hal.uart_get = uart_get;
    g_hal.uart_put = uart_put;
    g_hal.now_ms = now_ms;
    g_hal.delay_ms = delay_ms;
    g_hal.adc_read = hal_adc_read;
    g_hal.lcd_cs = lcd_cs;
    g_hal.lcd_dc = lcd_dc;
    g_hal.lcd_write = lcd_write;
    g_hal.lcd_reset = NULL;

    /* Calibration (raw16 scale = raw12 << 4).  See README for derivation. */
    g_hal.cal_vbus_mv = 8250;      /* 3.3 V ref, divider Vbus = 2.5 x Vpin */
    g_hal.cal_current_ma = 1375;   /* ZXCT1110, Rs=0.1, Rg=2.4k -> 2.4 V/A */
    g_hal.cal_current_zero = 0;
    g_hal.cal_temp_coef = 19173;   /* RP2040 temp sensor slope */
    g_hal.cal_temp_offset = 4372;  /* deci-C at raw16 == 0 */

    g_hal.product = "spidriver1";
    g_hal.serial = spidriver_usb_serial();

    struct repeating_timer tick_timer;
    add_repeating_timer_ms(1, tick_cb, NULL, &tick_timer);

    spidriver_init(&g_hal);
    spidriver_mainloop(&g_hal); /* never returns */
    return 0;
}
