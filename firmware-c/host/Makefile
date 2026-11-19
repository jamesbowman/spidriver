# POSIX host build for testing the portable core on a PC.
# Run from the host/ directory:  make -C host
CC      ?= gcc
CFLAGS  ?= -std=c11 -Wall -Wextra -Werror -O2 -I../src
SRC     := ../src/crc16.c ../src/st7735.c ../src/display.c ../src/spidriver.c hal_host.c
OUT     := build/spidriver_host

all: $(OUT)

$(OUT): $(SRC) ../src/*.h
	@mkdir -p build
	# shellcheck disable=SC2068
	$(CC) $(CFLAGS) -o $@ $(SRC)

test: $(OUT)
	printf '?' | ./$(OUT)

clean:
	rm -rf build

.PHONY: all test clean
