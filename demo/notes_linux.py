#!/usr/bin/env python3
"""Native GTK sample. Requires an activated node environment and GTK 3."""
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

window = Gtk.Window(title="Prooflane Notes")
window.set_default_size(740, 510)
window.set_border_width(40)
window.connect("destroy", Gtk.main_quit)
layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
window.add(layout)
for text in ("PROOFLANE / NOTES", "A small note. A real Linux test.",
             "Write something below, then save it to this session."):
    layout.pack_start(Gtk.Label(label=text, xalign=0), False, False, 0)
entry = Gtk.Entry()
entry.get_accessible().set_name("Note")
layout.pack_start(entry, False, False, 0)
button = Gtk.Button(label="Save note")
button.get_accessible().set_name("Save note")
layout.pack_start(button, False, False, 0)
status = Gtk.Label(label="Ready to write", xalign=0)
layout.pack_start(status, False, False, 0)
button.connect("clicked", lambda _: status.set_text("Saved: " + entry.get_text()))
window.show_all()
Gtk.main()
