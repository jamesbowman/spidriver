import wx
import time
import threading

import wx.lib.newevent as NE

MooEvent, EVT_MOO = NE.NewEvent()
GooEvent, EVT_GOO = NE.NewCommandEvent()

DELAY = 0.7

def evt_thr(win):
    time.sleep(DELAY)
    wx.PostEvent(win, MooEvent(moo=1))

def cmd_thr(win, id):
    time.sleep(DELAY)
    wx.PostEvent(win, GooEvent(id, goo=id))

ID_CMD1 = 100
ID_CMD2 = 101

class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "MOO")
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.Bind(EVT_MOO, self.on_moo)
        b = wx.Button(self, -1, "Generate MOO")
        sizer.Add(b, 1, wx.EXPAND)
        b.Bind(wx.EVT_BUTTON, self.on_evt_click)
        b = wx.Button(self, ID_CMD1, "Generate GOO with %d" % ID_CMD1)
        sizer.Add(b, 1, wx.EXPAND)
        b.Bind(wx.EVT_BUTTON, self.on_cmd_click)
        b = wx.Button(self, ID_CMD2, "Generate GOO with %d" % ID_CMD2)
        sizer.Add(b, 1, wx.EXPAND)
        b.Bind(wx.EVT_BUTTON, self.on_cmd_click)

        self.Bind(EVT_GOO, self.on_cmd1, id=ID_CMD1)
        self.Bind(EVT_GOO, self.on_cmd2, id=ID_CMD2)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        sizer.Fit(self)

    def on_evt_click(self, e):
        t = threading.Thread(target=evt_thr, args=(self, ))
        t.setDaemon(True)
        t.start()

    def on_cmd_click(self, e):
        t = threading.Thread(target=cmd_thr, args=(self, e.GetId()))
        t.setDaemon(True)
        t.start()

    def show(self, msg, title):
        dlg = wx.MessageDialog(self, msg, title, wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def on_moo(self, e):
        self.show("MOO = %s" % e.moo, "Got Moo")

    def on_cmd1(self, e):
        self.show("goo = %s" % e.goo, "Got Goo (cmd1)")

    def on_cmd2(self, e):
        self.show("goo = %s" % e.goo, "Got Goo (cmd2)")


app = wx.App(0)
f = Frame()
f.Show(True)
app.MainLoop()
