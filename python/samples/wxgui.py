import wx
import time
import threading
from functools import partial

from spidriver import SPIDriver

import wx.lib.newevent as NE

MooEvent, EVT_PING = NE.NewEvent()

def ping_thr(win):
    while True:
        time.sleep(1)
        wx.PostEvent(win, MooEvent())

class Frame(wx.Frame):
    def __init__(self):

        self.sd = SPIDriver("/dev/ttyUSB0")

        def pair(a, b):
            r = wx.BoxSizer(wx.HORIZONTAL)
            r.Add(a, 1, wx.LEFT, border = 1)
            r.Add(b, 0, wx.RIGHT, border = 1)
            return r

        def label(s):
            return wx.StaticText(self, label = s)

        def hbox(items):
            r = wx.BoxSizer(wx.HORIZONTAL)
            [r.Add(i) for i in items]
            return r

        def vbox(items):
            r = wx.BoxSizer(wx.VERTICAL)
            [r.Add(i, 0, wx.EXPAND) for i in items]
            return r

        wx.Frame.__init__(self, None, -1, "SPIDriver")

        self.label_voltage = wx.StaticText(self, label = "-")
        self.label_current = wx.StaticText(self, label = "-")
        self.label_temp = wx.StaticText(self, label = "-")
        self.label_uptime = wx.StaticText(self, label = "-")

        self.refresh()

        self.Bind(EVT_PING, self.on_ping)

        ckCS = wx.CheckBox(self, label = "CS")
        ckA = wx.CheckBox(self, label = "A")
        ckB = wx.CheckBox(self, label = "B")
        ckCS.SetValue(not self.sd.cs)
        ckA.SetValue(self.sd.a)
        ckB.SetValue(self.sd.b)
        ckCS.Bind(wx.EVT_CHECKBOX, self.check_cs)
        ckA.Bind(wx.EVT_CHECKBOX, self.check_a)
        ckB.Bind(wx.EVT_CHECKBOX, self.check_b)

        self.SetSizerAndFit(vbox([
            pair(label("Voltage"), self.label_voltage),
            pair(label("Current"), self.label_current),
            pair(label("Temp."), self.label_temp),
            pair(label("Running"), self.label_uptime),
            hbox([ckCS, ckA, ckB]),
            ]))
        self.SetAutoLayout(True)

        t = threading.Thread(target=ping_thr, args=(self, ))
        t.setDaemon(True)
        t.start()

    def on_ping(self, e):
        self.refresh()

    def refresh(self):
        self.sd.getstatus()
        self.label_voltage.SetLabel("%.2f V" % self.sd.voltage)
        self.label_current.SetLabel("%d mA" % self.sd.current)
        self.label_temp.SetLabel("%.1f C" % self.sd.temp)
        self.label_uptime.SetLabel("%d" % self.sd.uptime)

    def check_cs(self, e):
        if e.EventObject.GetValue():
            self.sd.sel()
        else:
            self.sd.unsel()

    def check_a(self, e):
        self.sd.seta(e.EventObject.GetValue())

    def check_b(self, e):
        self.sd.setb(e.EventObject.GetValue())

app = wx.App(0)
f = Frame()
f.Show(True)
app.MainLoop()
