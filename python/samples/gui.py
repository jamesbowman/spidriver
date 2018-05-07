import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from spidriver import SPIDriver

def ison(button): return button.get_state() == Gtk.StateType.ACTIVE

class ButtonWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="SPIDriver")
        self.set_border_width(10)

        self.sd = SPIDriver()
        # help(self.sd)

        hbox = Gtk.Box(spacing=6)

        def pair(a, b):
            r = Gtk.HBox(spacing=6)
            a.set_justify(Gtk.Justification.LEFT)
            b.set_justify(Gtk.Justification.RIGHT)
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
            [r.pack_start(i, True, True, 0) for i in items]
            return r

        def checkbutton(name, state, click):
            r = Gtk.CheckButton(name)
            r.set_active(state)
            r.connect("clicked", click)
            return r

        self.label_voltage = Gtk.Label()
        self.label_current = Gtk.Label()
        self.label_temp    = Gtk.Label()
        self.add(vbox([
            pair(label("Voltage"), self.label_voltage),
            pair(label("Current"), self.label_current),
            pair(label("Temp"), self.label_temp),
            hbox([
                checkbutton("CS", 1 - self.sd.cs, self.click_cs),
                checkbutton("A", self.sd.a, self.click_a),
                checkbutton("B", self.sd.b, self.click_b),
            ])
        ]))
        self.refresh()

        """
        self.add(hbox)

        button = Gtk.Button.new_with_label("Click Me")
        button.connect("clicked", self.on_click_me_clicked)
        hbox.pack_start(button, True, True, 0)

        button = Gtk.Button.new_with_mnemonic("_Open")
        button.connect("clicked", self.on_open_clicked)
        hbox.pack_start(button, True, True, 0)

        button = Gtk.Button.new_with_mnemonic("_Close")
        button.connect("clicked", self.on_close_clicked)
        hbox.pack_start(button, True, True, 0)

        hbox.pack_start(self.hbox([self.checkbutton("A"), self.checkbutton("b")]), True, True, 0)

        label = Gtk.Label()
        label.set_text("This is a left-justified label.\nWith multiple lines.")
        label.set_justify(Gtk.Justification.LEFT)
        hbox.pack_start(label, True, True, 0)
        self.label_voltage = label
        """
        GLib.timeout_add(1000, self.refresh)
    def refresh(self):
        self.sd.getstatus()
        self.label_voltage.set_text("%.2f V" % self.sd.voltage)
        self.label_current.set_text("%d mA" % self.sd.current)
        self.label_temp.set_text("%d C" % self.sd.temp)
        return True

    def click_cs(self, button):
        print 'CS state', button.get_state(), Gtk.StateType.ACTIVE
        [self.sd.unsel, self.sd.sel][ison(button)]()

    def click_a(self, button):
        self.sd.seta(int(button.get_state()))

    def click_b(self, button):
        self.sd.setb(int(button.get_state()))

    def on_click_me_clicked(self, button):
        print("\"Click me\" button was clicked")

    def on_open_clicked(self, button):
        print("\"Open\" button was clicked")

    def on_close_clicked(self, button):
        print("Closing application")
        Gtk.main_quit()

win = ButtonWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
