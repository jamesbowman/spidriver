/* POSIX host HAL: compiles the portable core on a PC for testing.  UART maps
 * to stdin/stdout (binary), SPI is a no-op, the LCD is discarded.  Intended
 * for CI/functional checks, not hardware use. */
#define _POSIX_C_SOURCE 200809L // NOLINT(bugprone-reserved-identifier): POSIX feature-test macro
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

#include "../src/spidriver.h"

/* ---- time ---- */
static uint32_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

static void delay_ms(uint32_t ms) {
    struct timespec ts = {(time_t)(ms / 1000), (long)(ms % 1000) * 1000000L};
    nanosleep(&ts, NULL);
}

/* ---- UART: stdin/stdout ---- */
static int16_t uart_get(void) {
    unsigned char c;
    ssize_t r = read(STDIN_FILENO, &c, 1);
    return r == 1 ? (int16_t)c : -1;
}

static void uart_put(uint8_t b) {
    unsigned char c = b;
    (void)write(STDOUT_FILENO, &c, 1);
}

/* ---- SPI: no-op ---- */
static void spi_select(void) {}
static void spi_unselect(void) {}
static void spi_attach(void) {}
static void spi_detach(void) {}
static uint8_t spi_xfer(uint8_t b) {
    (void)b;
    return 0x00; /* loopback of zeros */
}

static void set_a(bool v) { (void)v; }
static void set_b(bool v) { (void)v; }
static void led(bool v) { (void)v; }

/* ---- ADC: fixed realistic values (27 C temp, ~2.0 V VBUS, ~43 mA) ---- */
static uint16_t adc_read(unsigned ch) {
    switch (ch) {
        case ADC_TEMP: return 876;  /* ~0.706 V -> 27 C */
        case ADC_VBUS: return 1986; /* ~1.6 V after divider -> ~4.0 V */
        case ADC_CURR: return 155;  /* ~125 mV -> ~43 mA */
        default:       return 0;
    }
}

/* ---- LCD: discard ---- */
static void lcd_cs(bool v) { (void)v; }
static void lcd_dc(bool v) { (void)v; }
static void lcd_write(uint8_t b) { (void)b; }
static void lcd_reset(bool v) { (void)v; }

static spidriver_hal hal = {
    .spi_select = spi_select,
    .spi_unselect = spi_unselect,
    .spi_attach = spi_attach,
    .spi_detach = spi_detach,
    .spi_xfer = spi_xfer,
    .set_a = set_a,
    .set_b = set_b,
    .led = led,
    .uart_get = uart_get,
    .uart_put = uart_put,
    .now_ms = now_ms,
    .delay_ms = delay_ms,
    .adc_read = adc_read,
    .lcd_cs = lcd_cs,
    .lcd_dc = lcd_dc,
    .lcd_write = lcd_write,
    .lcd_reset = lcd_reset,
    .cal_vbus_mv = 8250,
    .cal_current_ma = 1375,
    .cal_current_zero = 0,
    .cal_temp_coef = 19173,
    .cal_temp_offset = 4372,
    .product = "spidriver1",
    .serial = "00000000",
};

int main(void) {
    /* binary stdin/stdout */
    (void)freopen(NULL, "rb", stdin);
    (void)freopen(NULL, "wb", stdout);

    spidriver_init(&hal);
    spidriver_mainloop(&hal);
    return 0;
}
