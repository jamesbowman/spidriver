# SPIDriver firmware -- Raspberry Pi Pico (RP2040) build.
#
# Build:
#   export PICO_SDK_PATH=/path/to/pico-sdk
#   cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
#   cmake --build build
#
# The portable core (src/) is shared with the POSIX host HAL in host/.
cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(spidriver_firmware C CXX ASM)

pico_sdk_init()

add_executable(spidriver_pico
    src/spidriver.c
    src/crc16.c
    src/st7735.c
    src/display.c
    pico/hal_pico.c
    pico/usb_descriptors.c
)

target_include_directories(spidriver_pico PRIVATE
    src
    pico
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(spidriver_pico PRIVATE
    pico_stdlib
    pico_unique_id
    pico_bootrom
    tinyusb_device
    tinyusb_board
    hardware_adc
    hardware_spi
    hardware_gpio
    hardware_timer
)

# we use raw USB CDC, not stdio
pico_enable_stdio_uart(spidriver_pico 0)
pico_enable_stdio_usb(spidriver_pico 0)

pico_add_extra_outputs(spidriver_pico)
