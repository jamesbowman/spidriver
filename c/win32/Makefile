CC = /usr/bin/i686-w64-mingw32-g++
CFLAGS += -I common -static-libgcc -static-libstdc++

all: build/spicl.exe

build/spicl.exe: win32/spi.c common/spidriver.c
	mkdir -p build/
	$(CC) -o $@ $(CPPFLAGS) $(CFLAGS) $^
