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

static HFONT monoBold, monoRegular;

static char mosi[4096], miso[4096];

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
  if (sd.connected) {
    spi_getstatus(&sd);
    info(hDlg, INF_S, "%s", sd.serial);
    info(hDlg, INF_V, "%.2f V", sd.voltage_v);
    info(hDlg, INF_C, "%.0f mA", sd.current_ma);
    info(hDlg, INF_T, "%.1f C", sd.temp_celsius);
    int days = sd.uptime / (24 * 3600);
    int rem = sd.uptime % (24 * 3600);
    int hh = rem / 3600, mm = (rem / 60) % 60, ss = rem % 60;
    info(hDlg, INF_U, "%d:%02d:%02d:%02d", days, hh, mm, ss);
  }
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

static void is_disconnected(HWND hDlg)
{
  EnableWindow(GetDlgItem(hDlg, BTN_A), FALSE);
  EnableWindow(GetDlgItem(hDlg, BTN_B), FALSE);
  EnableWindow(GetDlgItem(hDlg, BTN_CS), FALSE);
  EnableWindow(GetDlgItem(hDlg, BTN_TX), FALSE);
}

static void is_connected(HWND hDlg)
{
  EnableWindow(GetDlgItem(hDlg, BTN_A), TRUE);
  EnableWindow(GetDlgItem(hDlg, BTN_B), TRUE);
  EnableWindow(GetDlgItem(hDlg, BTN_CS), TRUE);
  EnableWindow(GetDlgItem(hDlg, BTN_TX), TRUE);

  CheckDlgButton(hDlg, BTN_A,   sd.a ? BST_CHECKED : BST_UNCHECKED);
  CheckDlgButton(hDlg, BTN_B,   sd.b ? BST_CHECKED : BST_UNCHECKED);
  CheckDlgButton(hDlg, BTN_CS, sd.cs ? BST_UNCHECKED : BST_CHECKED);
}

static void scan_ports(HWND cb)
{
  TCHAR lpTargetPath[5000];
  int count = 0;

  for(int i=1; i<255; i++) {
    char ComName[10];
    sprintf(ComName, "COM%d", i);
    if (QueryDosDevice(ComName, (LPSTR)lpTargetPath, 10000) != 0) {
      SendMessage(cb, CB_ADDSTRING, 0, (WPARAM)ComName);
      ++count;
    }
  }

  if (count == 1)
    SendMessage(cb, CB_SETCURSEL, -1, 0);
}

static void newdevice(HWND hDlg)
{
  char dev[10] = "";
  GetDlgItemText(hDlg, COMBO_DEV, dev, 9);
  if (strlen(dev) != 0) {
    spi_connect(&sd, dev);
    is_connected(hDlg);
    update(hDlg);
  } else {
    is_disconnected(hDlg);
  }
}

static void load_fonts(HWND hDlg)
{
  HDC hdc = GetDC(hDlg);

  LOGFONT logFont = {0};

  strcpy(logFont.lfFaceName, "Courier New");

  logFont.lfHeight = -MulDiv(8, GetDeviceCaps(hdc, LOGPIXELSY), 72);
  monoRegular = CreateFontIndirect(&logFont);

  logFont.lfHeight = -MulDiv(20, GetDeviceCaps(hdc, LOGPIXELSY), 72);
  logFont.lfWeight = FW_BOLD;
  monoBold = CreateFontIndirect(&logFont);


  ReleaseDC(hDlg, hdc);
}

INT_PTR CALLBACK DialogProc(HWND hDlg, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
  switch(uMsg)
  {
  case WM_INITDIALOG:
    {


      load_fonts(hDlg);

      scan_ports(GetDlgItem(hDlg, COMBO_DEV));

      SendMessage(GetDlgItem(hDlg, EDIT_TX), WM_SETFONT, (WPARAM)monoBold, (LPARAM)MAKELONG(TRUE, 0));
      SendMessage(GetDlgItem(hDlg, MISO_LOG), WM_SETFONT, (WPARAM)monoRegular, (LPARAM)MAKELONG(TRUE, 0));
      SendMessage(GetDlgItem(hDlg, MOSI_LOG), WM_SETFONT, (WPARAM)monoRegular, (LPARAM)MAKELONG(TRUE, 0));

      newdevice(hDlg);

      SetTimer(hDlg, EVT_T, 1000, NULL);
    }
    break;

  case WM_COMMAND:
    // printf("wParam = %d\n", LOWORD(wParam));
    SetTimer(hDlg, EVT_T, 1000, NULL);
    switch(LOWORD(wParam))
    {
    case IDCANCEL:
      SendMessage(hDlg, WM_CLOSE, 0, 0);
      return TRUE;

    case BTN_A:
      if (sd.connected)
        spi_seta(&sd, IsDlgButtonChecked(hDlg, BTN_A));
      return TRUE;

    case BTN_B:
      if (sd.connected)
        spi_setb(&sd, IsDlgButtonChecked(hDlg, BTN_B));
      return TRUE;

    case BTN_CS:
      if (sd.connected) {
        if (IsDlgButtonChecked(hDlg, BTN_CS))
          spi_sel(&sd);
        else
          spi_unsel(&sd);
      }
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
        int legal;
        unsigned value;
        size_t l = strlen(pszMem);
        legal = (l < 3);
        for (char *pc = pszMem; *pc; pc++)
          legal &= (strchr("0123456789ABCDEF", *pc) != NULL);
        if (legal)
          strcpy(last_good, pszMem);
        else
          SetWindowText(HWND(lParam), last_good);
        VirtualFree(pszMem, 0, MEM_RELEASE);
        return TRUE;
      }
      return FALSE;
#endif

    case BTN_TX:
      if (sd.connected) {
        char buf[4096];
        HWND tc = GetDlgItem(hDlg, EDIT_TX);
        GetWindowText(tc, buf, 4096);

        if (strlen(buf) == 0)
          return TRUE;

        unsigned int value;
        sscanf(buf, "%x", &value);
        char byte[1] = {value};
        spi_writeread(&sd, byte, 1);

        SetWindowText(tc, "");
        SendMessage(tc, EM_SETSEL, -1, -1);
        strcpy(last_good, "");

        sprintf(miso + strlen(miso), "%02x ", byte[0] & 0xff);
        sprintf(mosi + strlen(mosi), "%02x ", value);

        tc = GetDlgItem(hDlg, MISO_LOG);
        SetWindowText(tc, miso);
        SendMessage(tc, EM_SETSEL, strlen(miso), strlen(miso));

        tc = GetDlgItem(hDlg, MOSI_LOG);
        SetWindowText(tc, mosi);
        SendMessage(tc, EM_SETSEL, strlen(mosi), strlen(mosi));
      }
      return TRUE;

    case COMBO_DEV:
      if (CBN_SELCHANGE == HIWORD(wParam))
        newdevice(hDlg);
      return TRUE;

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

  AttachConsole(ATTACH_PARENT_PROCESS);
  freopen("CONIN$", "r",stdin); 
  freopen("CONOUT$","w",stdout); 
  freopen("CONOUT$","w",stderr); 
  // spi_connect(&sd, "COM4");

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
