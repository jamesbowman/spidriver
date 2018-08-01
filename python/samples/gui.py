# coding=utf-8
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import re
import struct

from spidriver import SPIDriver

def ison(button): return button.get_state() == Gtk.StateType.ACTIVE
def ishex(s): return re.match("[0-9a-fA-F]{2}$", s) is not None

class SPIDriverWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="SPIDriver")
        self.set_border_width(10)

        self.sd = SPIDriver()

        def pair(a, b):
            r = Gtk.HBox(spacing=6)
            r.pack_start(a, False, True, 0)
            r.pack_end(b, False, True, 0)
            return r

        def label(s):
            r = Gtk.Label()
            r.set_text(s)
            return r

        def vbox(items):
            r = Gtk.VBox(spacing=6)
            [r.pack_start(i, True, True, 0) for i in items]
            return r

        def hbox(items):
            r = Gtk.HBox(spacing=6)
            [r.pack_start(i, False, True, 0) for i in items]
            return r

        def checkbutton(name, state, click):
            r = Gtk.CheckButton(name)
            r.set_active(state)
            r.connect("clicked", click)
            return r

        def button(name, click):
            r = Gtk.Button(name)
            r.connect("clicked", click)
            return r

        self.label_voltage = Gtk.Label()
        self.label_current = Gtk.Label()
        self.label_temp = Gtk.Label()

        self.tx = Gtk.Entry()
        self.tx.set_width_chars(20)
        self.tx.connect('changed', self.edit)

        self.rx = Gtk.Entry()
        self.rx.set_width_chars(20)
        self.rx.connect('button-press-event', lambda a,b: True)
        self.rx.set_property('editable', False)

        self.button_send = button("Send", self.send)
        self.button_send.set_sensitive(False)

        self.add(vbox([
            pair(label("Voltage"),      self.label_voltage),
            pair(label("Current"),      self.label_current),
            pair(label("Temp"),         self.label_temp),
            Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
            hbox([
                checkbutton("CS", 1 - self.sd.cs, self.click_cs),
                checkbutton("A", self.sd.a, self.click_a),
                checkbutton("B", self.sd.b, self.click_b),
            ]),
            pair(self.tx,               self.button_send),
            pair(self.rx,               button("Recv", self.recv)),
        ]))

        self.refresh()
        GLib.timeout_add(1000, self.refresh)

    def refresh(self):
        self.sd.getstatus()
        self.label_voltage.set_text("%.2f V" % self.sd.voltage)
        self.label_current.set_text("%d mA" % self.sd.current)
        self.label_temp.set_text("%.1f C" % self.sd.temp)
        return True

    def click_cs(self, button):
        [self.sd.unsel, self.sd.sel][ison(button)]()

    def click_a(self, button):
        self.sd.seta(ison(button))

    def click_b(self, button):
        self.sd.setb(ison(button))

    def edit(self, _):
        b = self.tx.get_buffer()
        valid = all([ishex(w) for w in b.get_text().split()])
        self.button_send.set_sensitive(valid)

    def transfer(self, byte):
        byte = struct.unpack("B", self.sd.writeread(struct.pack("B", byte)))[0]
        txb = self.tx.get_buffer()
        txb.delete_text(0, -1)
        rxb = self.rx.get_buffer()
        rxb.set_text(rxb.get_text()[-17:] + " %02x" % byte, -1)

    def send(self, _):
        b = self.tx.get_buffer()
        for w in b.get_text().split():
            self.transfer(int(w, 16))

    def recv(self, _):
        self.transfer(0xff)

if __name__ == '__main__':
    win = SPIDriverWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
