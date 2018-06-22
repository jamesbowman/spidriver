#include "AboutDialog.h"
#include "Globals.h"
#include "Resource.h"

/* Dialog procedure for our "about" dialog */
INT_PTR CALLBACK AboutDialogProc(HWND hwndDlg, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
  switch (uMsg)
  {
    case WM_COMMAND:
    {
      WORD id = LOWORD(wParam);

      switch (id)
      {
        case IDOK:
        case IDCANCEL:
        {
          EndDialog(hwndDlg, (INT_PTR)id);
          return (INT_PTR)TRUE;
        }
      }
      break;
    }

    case WM_INITDIALOG:
    {
      return (INT_PTR)TRUE;
    }
  }

  return (INT_PTR)FALSE;
}

/* Show our "about" dialog */
void ShowAboutDialog(HWND owner)
{
  DialogBox(g_hInstance, MAKEINTRESOURCE(IDD_ABOUTDIALOG), owner, &AboutDialogProc);
}
