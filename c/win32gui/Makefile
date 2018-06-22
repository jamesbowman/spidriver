# This Makefile will build the MinGW Win32 application.

# Object files to create for the executable
OBJS = obj/AboutDialog.o obj/MainWindow.o obj/Resource.o obj/WinMain.o obj/spidriver.o

# Warnings to be raised by the C compiler
WARNS = -Wall

# Names of tools to use when building
CC = /usr/bin/i686-w64-mingw32-g++
RC = /usr/bin/i686-w64-mingw32-windres
EXE = Win32App.exe

# Compiler flags. Compile ANSI build only if CHARSET=ANSI.
ifeq (${CHARSET}, ANSI)
  CFLAGS = -O2 -D _WIN32_IE=0x0500 -D WINVER=0x0500 ${WARNS} -Iinclude -I../common
else
  CFLAGS = -O2 -D UNICODE -D _UNICODE -D _WIN32_IE=0x0500 -D WINVER=0x0500 ${WARNS} -Iinclude -I../common
endif

# Linker flags
LDFLAGS = -s -lcomctl32 -mwindows -static-libgcc -static-libstdc++

.PHONY: all clean

# Build executable by default
all: bin/${EXE}

# Create build output directories if they don't exist
bin obj:
	mkdir -p "$@"

# Compile object files for executable
obj/%.o: src/%.c | obj
	${CC} ${CFLAGS} -c "$<" -o "$@"

obj/spidriver.o: ../common/spidriver.c | obj
	${CC} ${CFLAGS} -c "$<" -o "$@"

# Build the resources
obj/Resource.o: res/Resource.rc res/Application.manifest res/Application.ico include/Resource.h | obj
	${RC} -I./include -I./res -i "$<" -o "$@"

# Build the exectuable
bin/${EXE}: ${OBJS} | bin
	${CC} -o "$@" ${OBJS} ${LDFLAGS}

# C header dependencies
obj/AboutDialog.o: include/AboutDialog.h include/Globals.h include/Resource.h
obj/MainWindow.o:  include/AboutDialog.h include/Globals.h include/MainWindow.h include/Resource.h
obj/WinMain.o:     include/Globals.h include/MainWindow.h include/Resource.h
