#include "AboutDialog.h"
#include "Globals.h"
#include "MainWindow.h"
#include "Resource.h"

#include <stdio.h>

#include "spidriver.h"

/* Main window class and title */
static LPCTSTR MainWndClass = TEXT("SPIDriver control");

static SPIDriver sd;

#define BTN_SEL     100
#define BTN_UNSEL   101

/* Window procedure for our main window */
LRESULT CALLBACK MainWndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
  switch (msg)
  {
    case WM_COMMAND:
    {
      WORD id = LOWORD(wParam);

      switch (id)
      {
        case IDCANCEL:
          SendMessage(hWnd, WM_CLOSE, 0, 0);
          return TRUE;

        case ID_HELP_ABOUT:
        {
          ShowAboutDialog(hWnd);
          return 0;
        }

        case ID_FILE_EXIT:
        {
          DestroyWindow(hWnd);
          return 0;
        }

        case BTN_SEL:
          spi_sel(&sd);
          break;
      
        case BTN_UNSEL:
          spi_unsel(&sd);
          break;
      }
      break;
    }

    case WM_GETMINMAXINFO:
    {
      /* Prevent our window from being sized too small */
      MINMAXINFO *minMax = (MINMAXINFO*)lParam;
      minMax->ptMinTrackSize.x = 220;
      minMax->ptMinTrackSize.y = 110;

      return 0;
    }

    /* Item from system menu has been invoked */
    case WM_SYSCOMMAND:
    {
      WORD id = LOWORD(wParam);

      switch (id)
      {
        /* Show "about" dialog on about system menu item */
        case ID_HELP_ABOUT:
        {
          ShowAboutDialog(hWnd);
          return 0;
        }
      }
      break;
    }

    case WM_CLOSE:
      DestroyWindow(hWnd);
      return TRUE;

    case WM_DESTROY:
      PostQuitMessage(0);
      return TRUE;
  }

  return DefWindowProc(hWnd, msg, wParam, lParam);
}

/* Register a class for our main window */
BOOL RegisterMainWindowClass()
{
  WNDCLASSEX wc;

  /* Class for our main window */
  wc.cbSize        = sizeof(wc);
  wc.style         = 0;
  wc.lpfnWndProc   = &MainWndProc;
  wc.cbClsExtra    = 0;
  wc.cbWndExtra    = 0;
  wc.hInstance     = g_hInstance;
  wc.hIcon         = (HICON)LoadImage(g_hInstance, MAKEINTRESOURCE(IDI_APPICON), IMAGE_ICON, 0, 0, LR_DEFAULTSIZE |
                                      LR_DEFAULTCOLOR | LR_SHARED);
  wc.hCursor       = (HCURSOR)LoadImage(NULL, IDC_ARROW, IMAGE_CURSOR, 0, 0, LR_SHARED);
  wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1);
  wc.lpszMenuName  = MAKEINTRESOURCE(IDR_MAINMENU);
  wc.lpszClassName = MainWndClass;
  wc.hIconSm       = (HICON)LoadImage(g_hInstance, MAKEINTRESOURCE(IDI_APPICON), IMAGE_ICON, 16, 16, LR_DEFAULTCOLOR);

  return (RegisterClassEx(&wc)) ? TRUE : FALSE;
}

/* Create an instance of our main window */
HWND CreateMainWindow()
{
  /* Create instance of main window */
  HWND hWnd = CreateWindowEx(0, MainWndClass, MainWndClass, WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 640, 480,
                             NULL, NULL, g_hInstance, NULL);

  if (hWnd)
  {
    /* Add "about" to the system menu */
    HMENU hSysMenu = GetSystemMenu(hWnd, FALSE);
    InsertMenu(hSysMenu, 5, MF_BYPOSITION | MF_SEPARATOR, 0, NULL);
    InsertMenu(hSysMenu, 6, MF_BYPOSITION, ID_HELP_ABOUT, TEXT("About"));


    HWND hwndButton;
    hwndButton = CreateWindow(
      "BUTTON",   // Predefined class; Unicode assumed 
      "Select",   // Button text 
      WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON,  // Styles 
      10,         // x position 
      10,         // y position 
      100,        // Button width
      30,         // Button height
      hWnd,       // Parent window
      (HMENU)BTN_SEL,       // No menu.
      (HINSTANCE)GetWindowLong(hWnd, GWL_HINSTANCE), 
      NULL);      // Pointer not needed.

    hwndButton = CreateWindow(
      "BUTTON",   // Predefined class; Unicode assumed 
      "Unselect", // Button text 
      WS_TABSTOP | WS_VISIBLE | WS_CHILD | BS_DEFPUSHBUTTON,  // Styles 
      10,         // x position 
      60,         // y position 
      100,        // Button width
      30,         // Button height
      hWnd,       // Parent window
      (HMENU)BTN_UNSEL,       // No menu.
      (HINSTANCE)GetWindowLong(hWnd, GWL_HINSTANCE), 
      NULL);
  }

  return hWnd;
}
