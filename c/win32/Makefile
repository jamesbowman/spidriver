CC = /usr/bin/i686-w64-mingw32-g++
CFLAGS += -I common

all: build/spi.exe

build/spi.exe: win32/spi.c common/spidriver.c
	mkdir -p build/
	$(CC) -o $@ $(CPPFLAGS) $(CFLAGS) $^
