/* USB descriptors: a single CDC-ACM serial port. */
#include <stdint.h>

#include "pico/bootrom.h"
#include "pico/unique_id.h"
#include "tusb.h" // IWYU pragma: keep

#define USBD_VID 0x2E8A /* Raspberry Pi */
#define USBD_PID 0x000A /* CDC serial */

#define USBD_STR_0 0x00
#define USBD_STR_MANUF 0x01
#define USBD_STR_PRODUCT 0x02
#define USBD_STR_SERIAL 0x03
#define USBD_STR_CDC 0x04

#define USBD_ITF_CDC 0
#define USBD_ITF_MAX 2 /* CDC control + data interfaces */

#define USBD_CDC_EP_CMD 0x81
#define USBD_CDC_EP_OUT 0x02
#define USBD_CDC_EP_IN 0x82
#define USBD_CDC_CMD_MAX_SIZE 8
#define USBD_CDC_IN_OUT_MAX_SIZE 64

static const tusb_desc_device_t usbd_desc_device = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = USBD_VID,
    .idProduct = USBD_PID,
    .bcdDevice = 0x0100,
    .iManufacturer = USBD_STR_MANUF,
    .iProduct = USBD_STR_PRODUCT,
    .iSerialNumber = USBD_STR_SERIAL,
    .bNumConfigurations = 1,
};

#define USBD_DESC_LEN \
    (TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN)

static const uint8_t usbd_desc_cfg[USBD_DESC_LEN] = {
    TUD_CONFIG_DESCRIPTOR(1, USBD_ITF_MAX, USBD_STR_0, USBD_DESC_LEN,
                          TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),
    TUD_CDC_DESCRIPTOR(USBD_ITF_CDC, USBD_STR_CDC, USBD_CDC_EP_CMD,
                       USBD_CDC_CMD_MAX_SIZE, USBD_CDC_EP_OUT, USBD_CDC_EP_IN,
                       USBD_CDC_IN_OUT_MAX_SIZE),
};

/* Serial string derived from the RP2040 unique board id. */
static char usbd_serial_str[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];

const char *spidriver_usb_serial(void) {
    if (usbd_serial_str[0] == '\0') {
        pico_unique_board_id_t id;
        pico_get_unique_board_id(&id);
        static const char hex[] = "0123456789ABCDEF";
        for (int i = 0; i < PICO_UNIQUE_BOARD_ID_SIZE_BYTES; i++) {
            usbd_serial_str[2 * i] = hex[id.id[i] >> 4];
            usbd_serial_str[2 * i + 1] = hex[id.id[i] & 0x0F];
        }
        usbd_serial_str[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES] = '\0';
    }
    return usbd_serial_str;
}

static const char *const usbd_desc_str[] = {
    [USBD_STR_MANUF] = "spidriver",
    [USBD_STR_PRODUCT] = "SPIDriver",
    [USBD_STR_SERIAL] = usbd_serial_str, /* filled by spidriver_usb_serial() */
    [USBD_STR_CDC] = "SPIDriver serial port",
};

const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&usbd_desc_device;
}

const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return usbd_desc_cfg;
}

/* Reboot into the RP2040 bootrom (BOOTSEL) when the host opens the port at
 * 1200 baud -- same convention as pico_stdio_usb/Arduino.  Lets a host
 * re-flash without touching the BOOTSEL button. */
void tud_cdc_line_coding_cb(uint8_t itf, cdc_line_coding_t const *line_coding) {
    (void)itf;
    if (line_coding->bit_rate == 1200) {
        reset_usb_boot(0, 0);
    }
}

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    static uint16_t strbuf[32];
    const char *s = NULL;

    if (index == USBD_STR_0) {
        strbuf[1] = 0x0409;
        return &strbuf[1];
    }
    if (index < sizeof(usbd_desc_str) / sizeof(usbd_desc_str[0])) {
        s = usbd_desc_str[index];
    }
    if (s == NULL) {
        return NULL;
    }
    if (index == USBD_STR_SERIAL) {
        s = spidriver_usb_serial();
    }

    unsigned len = 0;
    while (s[len] && len < 31) len++;
    for (unsigned i = 0; i < len; i++) {
        strbuf[1 + i] = s[i];
    }
    strbuf[0] = (uint16_t)((len * 2 + 2) | (3 << 8)); /* bLength, bDescriptorType */
    return strbuf;
}
