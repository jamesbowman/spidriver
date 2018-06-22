#include <windows.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#define __STDC_FORMAT_MACROS
#include <inttypes.h>
#include <stdarg.h>

#include <commctrl.h>
#include "Globals.h"
#include "MainWindow.h"
#include "Resource.h"

#include "spidriver.h"

static SPIDriver sd;

#define MAX_TEXT 65536

static char last_good[MAX_TEXT];

int HandleCmdLine(char cl[])
{
  char *s = cl;

  while (1) {
    char *token = strtok(s, " ");
    s = NULL;
    if (token == NULL)
      break;
    // printf("token [%s]\n", token);
    if (strlen(token) != 1)
      goto badcommand;
    switch (token[0]) {

    case '?':
      spi_getstatus(&sd);
      printf("uptime %" SCNu64"  %.3f V  %.0f mA  %.1f C\n", sd.uptime, sd.voltage_v, sd.current_ma, sd.temp_celsius);
      break;

    case 's':
      spi_sel(&sd);
      break;

    case 'u':
      spi_unsel(&sd);
      break;

    case 'w':
    case 't':
      {
        token = strtok(s, " ");
        char bytes[8192], *endptr = token;
        size_t nn = 0;
        while (nn < sizeof(bytes)) {
          bytes[nn++] = strtol(endptr, &endptr, 0);
          if (*endptr == '\0')
            break;
          if (*endptr != ',') {
            fprintf(stderr, "Invalid bytes '%s'\n", token);
            return 1;
          }
          endptr++;
        }
        spi_write(&sd, bytes, nn);
      }
      break;

    case 'r':
      {
        token = strtok(s, " ");
        size_t nn = strtol(token, NULL, 0);
        char bytes[8192];
        spi_read(&sd, bytes, nn);
        for (size_t i = 0; i < nn; i++)
          printf("%02x ", bytes[i]);
        printf("\n");
      }
      break;

    case 'a':
      token = strtok(s, " ");
      if (token != NULL)
        spi_seta(&sd, token[0]);
      break;

    case 'b':
      token = strtok(s, " ");
      if (token != NULL)
        spi_setb(&sd, token[0]);
      break;

    default:
    badcommand:
      fprintf(stderr, "Bad command '%s'\n", token);
      return 1;
    }
  }

  return 0;
}

static void info(HWND hDlg, int id, const char *fmt, ...)
{
  va_list ap;
  char buf[80];

  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  SetWindowText(GetDlgItem(hDlg, id), buf);
}

static void update(HWND hDlg)
{
  spi_getstatus(&sd);
  info(hDlg, INF_V, "%.2f V", sd.voltage_v);
  info(hDlg, INF_C, "%.0f mA", sd.current_ma);
  info(hDlg, INF_T, "%.1f C", sd.temp_celsius);
  int days = sd.uptime / (24 * 3600);
  int rem = sd.uptime % (24 * 3600);
  int hh = rem / 3600, mm = (rem / 60) % 60, ss = rem % 60;
  info(hDlg, INF_U, "%d:%02d:%02d:%02d", days, hh, mm, ss);
}

/*
static int hexstring(char *dst, const char *instr)
{
  int n = 0;
  const char *s = instr;
  while (1) {
    bytes[n++] = strtol(s, &s, 16);
    if (*s == 0)
      return n;

  }
}
*/

INT_PTR CALLBACK DialogProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
  switch(uMsg)
  {
  case WM_INITDIALOG:
    {
      HWND cb = GetDlgItem(hDlg, 777);
      SendMessage(cb, CB_ADDSTRING, 0, (LPARAM)"Hex");
      SendMessage(cb, CB_ADDSTRING, 0, (LPARAM)"Text");
      SendMessage(cb, CB_SETCURSEL, 0, 0);

      CheckDlgButton(hDlg, BTN_A,   sd.a ? BST_CHECKED : BST_UNCHECKED);
      CheckDlgButton(hDlg, BTN_B,   sd.b ? BST_CHECKED : BST_UNCHECKED);
      CheckDlgButton(hDlg, BTN_CS, sd.cs ? BST_UNCHECKED : BST_CHECKED);

      update(hDlg);

      SetTimer(hDlg, EVT_T, 1000, NULL);
    }
    break;

  case WM_COMMAND:
    printf("wParam = %d\n", LOWORD(wParam));
    SetTimer(hDlg, EVT_T, 1000, NULL);
    switch(LOWORD(wParam))
    {
    case IDCANCEL:
      SendMessage(hDlg, WM_CLOSE, 0, 0);
      return TRUE;

    case BTN_A:
      spi_seta(&sd, IsDlgButtonChecked(hDlg, BTN_A));
      return TRUE;

    case BTN_B:
      spi_setb(&sd, IsDlgButtonChecked(hDlg, BTN_B));
      return TRUE;

    case BTN_CS:
      if (IsDlgButtonChecked(hDlg, BTN_CS))
        spi_sel(&sd);
      else
        spi_unsel(&sd);
      return TRUE;

#if 1
    case EDIT_TX:
      if (HIWORD(wParam) == EN_UPDATE) {
        int cTxtLen; 
        PSTR pszMem;

        cTxtLen = GetWindowTextLength(HWND(lParam));
        pszMem = (PSTR) VirtualAlloc((LPVOID) NULL, 
            (DWORD) (cTxtLen + 1), MEM_COMMIT, 
            PAGE_READWRITE); 
        GetWindowText(HWND(lParam), pszMem, 
            cTxtLen + 1);
        printf("XXX '%s'\n", pszMem);
        int legal = 1;
        VirtualFree(pszMem, 0, MEM_RELEASE);
        return TRUE;
      }
      return FALSE;
#endif

    case BTN_TX:
      {
        char buf[4096];
        HWND tc = GetDlgItem(hDlg, EDIT_TX);
        GetWindowText(tc, buf, 4096);
        printf("Transmitting %d bytes", strlen(buf));
        spi_write(&sd, buf, strlen(buf));
        SetWindowText(tc, "");
        SendMessage(tc, EM_SETSEL, -1, -1);
        strcpy(last_good, "");
        return TRUE;
      }

    case BTN_RX:
      {
        char buf[1];
        spi_read(&sd, buf, 1);
        info(hDlg, EDIT_RX, "%02x", buf[0]);
        return TRUE;
      }
    }
    break;

  case WM_TIMER:
    {
      update(hDlg);
      return TRUE;
    }

  case WM_CLOSE:
    DestroyWindow(hDlg);
    return TRUE;

  case WM_DESTROY:
    PostQuitMessage(0);
    return TRUE;
  }

  return FALSE;
}

/* Global instance handle */
HINSTANCE g_hInstance = NULL;

/* Our application entry point */
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow)
{
  INITCOMMONCONTROLSEX icc;
  HWND hWnd;
  HACCEL hAccelerators;
  MSG msg;

  /* Assign global HINSTANCE */
  g_hInstance = hInstance;

  // AllocConsole();
  AttachConsole(ATTACH_PARENT_PROCESS);
  freopen("CONIN$", "r",stdin); 
  freopen("CONOUT$","w",stdout); 
  freopen("CONOUT$","w",stderr); 

  spi_connect(&sd, "COM4");
  spi_getstatus(&sd);

  if (strlen(lpCmdLine) != 0) {
    char cl[1024] = {0};
    strncpy(cl, lpCmdLine, sizeof(cl) - 1);
    return HandleCmdLine(cl);
  }

  /* Initialise common controls */
  icc.dwSize = sizeof(icc);
  icc.dwICC = ICC_WIN95_CLASSES;
  InitCommonControlsEx(&icc);

#if 0
  /* Register our main window class, or error */
  if (!RegisterMainWindowClass())
  {
    MessageBox(NULL, TEXT("Error registering main window class."), TEXT("Error"), MB_ICONERROR | MB_OK);
    return 0;
  }

  /* Create our main window, or error */
  if (!(hWnd = CreateMainWindow()))
  {
    MessageBox(NULL, TEXT("Error creating main window."), TEXT("Error"), MB_ICONERROR | MB_OK);
    return 0;
  }
#else
  hWnd = CreateDialogParam(hInstance, MAKEINTRESOURCE(IDD_DIALOG1), 0, DialogProc, 0);
#endif

  /* Load accelerators */
  hAccelerators = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDR_ACCELERATOR));

  /* Show main window and force a paint */
  ShowWindow(hWnd, nCmdShow);
  UpdateWindow(hWnd);

  /* Main message loop */
  while (GetMessage(&msg, NULL, 0, 0) > 0)
  {
    // if (!TranslateAccelerator(hWnd, hAccelerators, &msg))
    if(!IsDialogMessage(hWnd, &msg))
    {
      TranslateMessage(&msg);
      DispatchMessage(&msg);
    }
  }

  return (int)msg.wParam;
}
