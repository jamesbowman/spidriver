# SPIDriver Linux GUI (GTK4 port of win32gui).
#
#   cmake -B build-gtk4 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
#   cmake --build build-gtk4
#   ./build-gtk4/spidriver-gui
#
# Reuses the portable c/common/spidriver.c (POSIX termios serial path).

cmake_minimum_required(VERSION 3.16)
project(spidriver_gtk4 C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK4 REQUIRED IMPORTED_TARGET gtk4)

add_executable(spidriver-gui
    linuxgui/main.c
    common/spidriver.c
)

target_include_directories(spidriver-gui PRIVATE common)
target_link_libraries(spidriver-gui PRIVATE PkgConfig::GTK4)
