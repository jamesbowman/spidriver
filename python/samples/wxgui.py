import wx
import time
import struct
import threading
from functools import partial

from spidriver import SPIDriver

import wx.lib.newevent as NE

MooEvent, EVT_PING = NE.NewEvent()

def ping_thr(win):
    while True:
        time.sleep(1)
        wx.PostEvent(win, MooEvent())

class HexTextCtrl(wx.TextCtrl):
    def __init__(self, *args, **kwargs):
        super(HexTextCtrl, self).__init__(*args, **kwargs)
        self.Bind(wx.EVT_TEXT, self.on_text)
    def on_text(self, event):
        event.Skip()
        selection = self.GetSelection()
        value = self.GetValue().upper()
        hex = "0123456789ABCDEF"
        value = "".join([c for c in value if c in hex])
        self.ChangeValue(value)
        self.SetSelection(*selection)

class Frame(wx.Frame):
    def __init__(self):

        self.sd = SPIDriver("/dev/ttyUSB0")

        def widepair(a, b):
            r = wx.BoxSizer(wx.HORIZONTAL)
            r.Add(a, 1, wx.LEFT)
            r.AddStretchSpacer(prop=1)
            r.Add(b, 1, wx.RIGHT)
            return r

        def pair(a, b):
            r = wx.BoxSizer(wx.HORIZONTAL)
            r.Add(a, 1, wx.LEFT)
            r.Add(b, 0, wx.RIGHT)
            return r

        def rpair(a, b):
            r = wx.BoxSizer(wx.HORIZONTAL)
            r.Add(a, 0, wx.LEFT)
            r.Add(b, 1, wx.RIGHT)
            return r

        def label(s):
            return wx.StaticText(self, label = s)

        def hbox(items):
            r = wx.BoxSizer(wx.HORIZONTAL)
            [r.Add(i, 0, wx.EXPAND) for i in items]
            return r

        def hcenter(i):
            r = wx.BoxSizer(wx.HORIZONTAL)
            r.AddStretchSpacer(prop=1)
            r.Add(i, 3, wx.CENTER)
            r.AddStretchSpacer(prop=1)
            return r

        def vbox(items):
            r = wx.BoxSizer(wx.VERTICAL)
            [r.Add(i, 0, wx.EXPAND) for i in items]
            return r

        wx.Frame.__init__(self, None, -1, "SPIDriver")

        self.label_serial = wx.StaticText(self, label = "-", style = wx.ALIGN_RIGHT)
        self.label_voltage = wx.StaticText(self, label = "-", style = wx.ALIGN_RIGHT)
        self.label_current = wx.StaticText(self, label = "-", style = wx.ALIGN_RIGHT)
        self.label_temp = wx.StaticText(self, label = "-", style = wx.ALIGN_RIGHT)
        self.label_uptime = wx.StaticText(self, label = "-", style = wx.ALIGN_RIGHT)

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

        self.txMISO = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_RIGHT | wx.TE_DONTWRAP)
        self.txMOSI = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_RIGHT | wx.TE_DONTWRAP)
        self.txMISO.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.txMOSI.SetBackgroundColour(wx.Colour(224, 224, 224))


        self.txVal = HexTextCtrl(self, size=wx.DefaultSize, style=0)
        self.txVal.SetMaxLength(2)
        self.txVal.SetFont(wx.Font(14,
                              wx.FONTFAMILY_TELETYPE,
                              wx.FONTSTYLE_NORMAL,
                              wx.FONTWEIGHT_BOLD))
        txButton = wx.Button(self, label = "Transfer")
        txButton.Bind(wx.EVT_BUTTON, partial(self.transfer, self.txVal))

        self.SetSizerAndFit(vbox([
            hcenter(vbox([
                widepair(label("Serial"), self.label_serial),
                widepair(label("Voltage"), self.label_voltage),
                widepair(label("Current"), self.label_current),
                widepair(label("Temp."), self.label_temp),
                widepair(label("Running"), self.label_uptime),
            ])),
            label(""),
            rpair(label("MISO"), self.txMISO),
            rpair(label("MOSI"), self.txMOSI),
            label(""),
            hcenter(pair(ckCS, hbox([ckA, ckB]))),
            hcenter(pair(self.txVal, txButton)),
            ]))
        self.SetAutoLayout(True)

        t = threading.Thread(target=ping_thr, args=(self, ))
        t.setDaemon(True)
        t.start()

    def on_ping(self, e):
        self.refresh()

    def refresh(self):
        self.sd.getstatus()
        self.label_serial.SetLabel(self.sd.serial)
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

    def transfer(self, htc, e):
        txb = int(htc.GetValue(), 16)
        rxb = struct.unpack("B", self.sd.writeread(struct.pack("B", txb)))[0]
        self.txMOSI.AppendText(" %02x" % txb)
        self.txMISO.AppendText(" %02x" % rxb)
        htc.ChangeValue("")

if __name__ == '__main__':
    app = wx.App(0)
    f = Frame()
    f.Show(True)
    app.MainLoop()
