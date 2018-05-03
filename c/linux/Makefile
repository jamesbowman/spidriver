CFLAGS += -I common

all: build/spi

install: all
	cp build/spi /usr/local/bin

build/spi: linux/spi.c common/spidriver.c
	mkdir -p build/
	$(CC) -o $@ $(CPPFLAGS) $(CFLAGS) $^
