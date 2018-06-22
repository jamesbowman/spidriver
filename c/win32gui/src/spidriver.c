#include <stdio.h>
#include <assert.h>
#include <memory.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#define __STDC_FORMAT_MACROS
#include <inttypes.h>

#include "spidriver.h"

// ****************************   Serial port  ********************************

#if defined(WIN32)  // {

#include <windows.h>

void ErrorExit(LPTSTR lpszFunction) 
{ 
    // Retrieve the system error message for the last-error code

    LPVOID lpMsgBuf;
    LPVOID lpDisplayBuf;
    DWORD dw = GetLastError(); 

    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | 
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPTSTR) &lpMsgBuf,
        0, NULL );

    // Display the error message and exit the process

    lpDisplayBuf = (LPVOID)LocalAlloc(LMEM_ZEROINIT, 
        (lstrlen((LPCTSTR)lpMsgBuf) + lstrlen((LPCTSTR)lpszFunction) + 40) * sizeof(TCHAR)); 
    sprintf((LPTSTR)lpDisplayBuf, TEXT("%s failed with error %d:\n%s"), lpszFunction, dw, lpMsgBuf); 
    MessageBox(NULL, (LPCTSTR)lpDisplayBuf, TEXT("Error"), MB_OK); 

    LocalFree(lpMsgBuf);
    LocalFree(lpDisplayBuf);
    ExitProcess(dw); 
}

HANDLE openSerialPort(LPCSTR portname)
{
    DWORD  accessdirection = GENERIC_READ | GENERIC_WRITE;
    HANDLE hSerial = CreateFile(portname,
        accessdirection,
        0,
        0,
        OPEN_EXISTING,
        0,
        0);
    if (hSerial == INVALID_HANDLE_VALUE) {
        ErrorExit("CreateFile");
    }
    DCB dcbSerialParams = {0};
    dcbSerialParams.DCBlength=sizeof(dcbSerialParams);
    if (!GetCommState(hSerial, &dcbSerialParams)) {
         ErrorExit("GetCommState");
    }
    dcbSerialParams.BaudRate = 460800;
    dcbSerialParams.ByteSize = 8;
    dcbSerialParams.StopBits = ONESTOPBIT;
    dcbSerialParams.Parity = NOPARITY;
    if (!SetCommState(hSerial, &dcbSerialParams)) {
         ErrorExit("SetCommState");
    }
    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    timeouts.WriteTotalTimeoutConstant = 50;
    timeouts.WriteTotalTimeoutMultiplier = 10;
    if (!SetCommTimeouts(hSerial, &timeouts)) {
        ErrorExit("SetCommTimeouts");
    }
    return hSerial;
}

DWORD readFromSerialPort(HANDLE hSerial, char * buffer, int buffersize)
{
    DWORD dwBytesRead = 0;
    if (!ReadFile(hSerial, buffer, buffersize, &dwBytesRead, NULL)) {
        ErrorExit("ReadFile");
    }
    return dwBytesRead;
}

DWORD writeToSerialPort(HANDLE hSerial, const char * data, int length)
{
    DWORD dwBytesRead = 0;
    if (!WriteFile(hSerial, data, length, &dwBytesRead, NULL)) {
        ErrorExit("WriteFile");
    }
    return dwBytesRead;
}

void closeSerialPort(HANDLE hSerial)
{
    CloseHandle(hSerial);
}

#else               // }{

#include <termios.h>

int openSerialPort(const char *portname)
{
  int fd = open(portname, O_RDWR | O_NOCTTY);
  if (fd == -1)
    perror(portname);

  struct termios Settings;

  tcgetattr(fd, &Settings);

  cfsetispeed(&Settings, B460800);
  cfsetospeed(&Settings, B460800);

  Settings.c_cflag &= ~PARENB;
  Settings.c_cflag &= ~CSTOPB;
  Settings.c_cflag &= ~CSIZE;
  Settings.c_cflag &= ~CRTSCTS;
  Settings.c_cflag |=  CS8;
  Settings.c_cflag |=  CREAD | CLOCAL;

  Settings.c_iflag &= ~(IXON | IXOFF | IXANY);
  Settings.c_iflag &= ~(ICANON | ECHO | ECHOE | ISIG);

  Settings.c_oflag &= ~OPOST;

  Settings.c_cc[VMIN] = 1;

  if (tcsetattr(fd, TCSANOW, &Settings) != 0)
    perror("Serial settings");

  return fd;
}

size_t readFromSerialPort(int fd, char *b, size_t s)
{
  size_t n, t;
  t = 0;
  while (t < s) {
    n = read(fd, b + t, s);
    t += n;
  }
#ifdef VERBOSE
  printf(" READ %d %d: ", (int)s, int(n));
  for (int i = 0; i < s; i++)
    printf("%02x ", 0xff & b[i]);
  printf("\n");
#endif
  return s;
}

void writeToSerialPort(int fd, const char *b, size_t s)
{
  write(fd, b, s);
#ifdef VERBOSE
  printf("WRITE %u: ", (int)s);
  for (int i = 0; i < s; i++)
    printf("%02x ", 0xff & b[i]);
  printf("\n");
#endif
}
#endif              // }

// ******************************  SPIDriver  *********************************

void spi_connect(SPIDriver *sd, const char* portname)
{
  sd->port = openSerialPort(portname);
  writeToSerialPort(sd->port, "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", 64);

  const char tests[] = "A\r\n\0xff";
  for (int i = 0; i < 4; i++) {
    char tx[2] = {'e', tests[i]};
    writeToSerialPort(sd->port, tx, 2);
    char rx[1];
    int n = readFromSerialPort(sd->port, rx, 1);
    if (rx[0] != tests[i])
      assert(0);
  }

  printf("\n");
  spi_getstatus(sd);
}

void spi_getstatus(SPIDriver *sd)
{
  char readbuffer[100];
  int bytesRead;

  writeToSerialPort(sd->port, "?", 1);
  bytesRead = readFromSerialPort(sd->port, readbuffer, 80);
  readbuffer[bytesRead] = 0;
  // printf("%d Bytes were read: %.*s\n", bytesRead, bytesRead, readbuffer);
  sscanf(readbuffer, "[%15s %8s %" SCNu64 " %f %f %f %d %d %d %x ]",
    sd->model,
    sd->serial,
    &sd->uptime,
    &sd->voltage_v,
    &sd->current_ma,
    &sd->temp_celsius,
    &sd->a,
    &sd->b,
    &sd->cs,
    &sd->debug
    );
}

void spi_sel(SPIDriver *sd)
{
  writeToSerialPort(sd->port, "s", 1);
  sd->cs = 0;
}

void spi_unsel(SPIDriver *sd)
{
  writeToSerialPort(sd->port, "u", 1);
  sd->cs = 1;
}

void spi_seta(SPIDriver *sd, char v)
{
  char cmd[2] = {'a', v};
  writeToSerialPort(sd->port, cmd, 2);
  sd->a = v;
}

void spi_setb(SPIDriver *sd, char v)
{
  char cmd[2] = {'b', v};
  writeToSerialPort(sd->port, cmd, 2);
  sd->b = v;
}

void spi_write(SPIDriver *sd, const char bytes[], size_t nn)
{
  for (size_t i = 0; i < nn; i += 64) {
    size_t len = ((nn - i) < 64) ? (nn - i) : 64;
    char cmd[65] = {(char)(0xc0 + len - 1)};
    memcpy(cmd + 1, bytes + i, len);
    writeToSerialPort(sd->port, cmd, 1 + len);
  }
}

void spi_read(SPIDriver *sd, char bytes[], size_t nn)
{
  for (size_t i = 0; i < nn; i += 64) {
    size_t len = ((nn - i) < 64) ? (nn - i) : 64;
    char cmd[65] = {(char)(0x80 + len - 1), 0};
    writeToSerialPort(sd->port, cmd, 1 + len);
    readFromSerialPort(sd->port, bytes + i, len);
  }
}

void spi_writeread(SPIDriver *sd, char bytes[], size_t nn)
{
  for (size_t i = 0; i < nn; i += 64) {
    size_t len = ((nn - i) < 64) ? (nn - i) : 64;
    char cmd[65] = {(char)(0x80 + len - 1)};
    memcpy(cmd + 1, bytes + i, len);
    writeToSerialPort(sd->port, cmd, 1 + len);
    readFromSerialPort(sd->port, bytes + i, len);
  }
}

