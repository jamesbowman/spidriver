import time
import struct
import sys
import os
import re
import threading
from functools import partial

import wx
import wx.lib.newevent as NE

from spidriver import SPIDriver

PingEvent, EVT_PING = NE.NewEvent()

def ping_thr(win):
    while True:
        wx.PostEvent(win, PingEvent())
        time.sleep(1)

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

        self.sd = None
        print self.devices()

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

        self.Bind(EVT_PING, self.refresh)

        self.ckCS = wx.CheckBox(self, label = "CS")
        self.ckA = wx.CheckBox(self, label = "A")
        self.ckB = wx.CheckBox(self, label = "B")
        self.ckCS.Bind(wx.EVT_CHECKBOX, self.check_cs)
        self.ckA.Bind(wx.EVT_CHECKBOX, self.check_a)
        self.ckB.Bind(wx.EVT_CHECKBOX, self.check_b)

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

        self.allw = [self.ckCS, self.ckA, self.ckB, self.txVal, txButton, self.txMISO, self.txMOSI]
        [w.Enable(False) for w in self.allw]
        self.devs = self.devices()
        cb = wx.ComboBox(self, choices = sorted(self.devs.keys()))
        cb.Bind(wx.EVT_COMBOBOX, self.choose_device)
        vb = vbox([
            label(""),
            hcenter(cb),
            label(""),
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
            hcenter(pair(self.ckCS, hbox([self.ckA, self.ckB]))),
            hcenter(pair(self.txVal, txButton)),
            label(""),
            ])
        self.SetSizerAndFit(vb)
        self.SetAutoLayout(True)

        if len(self.devs) > 0:
            d1 = min(self.devs)
            self.connect(self.devs[d1])
            cb.SetValue(d1)

        t = threading.Thread(target=ping_thr, args=(self, ))
        t.setDaemon(True)
        t.start()

    def devices(self):
        if sys.platform == 'darwin':
            devdir = "/dev/"
            pattern = "^tty.usbserial-(........)-"
        else:
            devdir = "/dev/serial/by-id/"
            pattern = "^usb-FTDI_FT230X_Basic_UART_(........)-"

        devs = os.listdir(devdir)
        print(devs)
        def filter(d):
            m = re.match(pattern, d)
            if m:
                return (m.group(1), devdir + d)
        seldev = [filter(d) for d in devs]
        return dict([d for d in seldev if d])

    def connect(self, dev):
        self.sd = SPIDriver("/dev/ttyUSB0")
        [w.Enable(True) for w in self.allw]
        self.ckCS.SetValue(not self.sd.cs)
        self.ckA.SetValue(self.sd.a)
        self.ckB.SetValue(self.sd.b)
        self.refresh(None)

    def refresh(self, e):
        if self.sd:
            self.sd.getstatus()
            self.label_serial.SetLabel(self.sd.serial)
            self.label_voltage.SetLabel("%.2f V" % self.sd.voltage)
            self.label_current.SetLabel("%d mA" % self.sd.current)
            self.label_temp.SetLabel("%.1f C" % self.sd.temp)
            days = self.sd.uptime // (24 * 3600)
            rem = self.sd.uptime % (24 * 3600)
            hh = rem // 3600
            mm = (rem / 60) % 60
            ss = rem % 60;
            self.label_uptime.SetLabel("%d:%02d:%02d:%02d" % (days, hh, mm, ss))

    def choose_device(self, e):
        self.connect(self.devs[e.EventObject.GetValue()])

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
        if htc.GetValue():
            txb = int(htc.GetValue(), 16)
            rxb = struct.unpack("B", self.sd.writeread(struct.pack("B", txb)))[0]
            self.txMOSI.AppendText(" %02X" % txb)
            self.txMISO.AppendText(" %02X" % rxb)
            htc.ChangeValue("")

if __name__ == '__main__':
    app = wx.App(0)
    f = Frame()
    f.Show(True)
    app.MainLoop()
