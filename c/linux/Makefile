CFLAGS += -I common

all: build/spicl

install: all
	cp build/spi /usr/local/bin

build/spicl: linux/spi.c common/spidriver.c
	mkdir -p build/
	$(CC) -o $@ $(CPPFLAGS) $(CFLAGS) $^
