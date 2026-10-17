#!/usr/bin/env python3
"""Native AppKit sample. Requires the activated PyObjC node environment."""
import AppKit as A
from Foundation import NSObject, NSMakeRect


class NotesActions(NSObject):
    def save_(self, sender):
        status.setStringValue_("Saved: " + entry.stringValue())


app = A.NSApplication.sharedApplication()
app.setActivationPolicy_(A.NSApplicationActivationPolicyRegular)
window = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    NSMakeRect(0, 0, 740, 510),
    A.NSWindowStyleMaskTitled | A.NSWindowStyleMaskClosable | A.NSWindowStyleMaskMiniaturizable,
    A.NSBackingStoreBuffered, False)
window.setTitle_("Prooflane Notes")
window.setReleasedWhenClosed_(False)
view = window.contentView()


def label(text, y, size=16):
    field = A.NSTextField.labelWithString_(text)
    field.setFrame_(NSMakeRect(40, y, 660, 32))
    field.setFont_(A.NSFont.systemFontOfSize_(size))
    view.addSubview_(field)
    return field


label("PROOFLANE / NOTES", 440)
label("A small note. A real macOS test.", 380, 25)
label("Write something below, then save it to this session.", 325)
entry = A.NSTextField.alloc().initWithFrame_(NSMakeRect(40, 235, 660, 48))
entry.setAccessibilityIdentifier_("noteInput")
entry.setAccessibilityLabel_("Note")
view.addSubview_(entry)
handler = NotesActions.alloc().init()
button = A.NSButton.alloc().initWithFrame_(NSMakeRect(40, 150, 160, 44))
button.setTitle_("Save note")
button.setBezelStyle_(A.NSBezelStyleRounded)
button.setAccessibilityIdentifier_("saveButton")
button.setTarget_(handler)
button.setAction_("save:")
view.addSubview_(button)
status = label("Ready to write", 70)
window.center()
window.makeKeyAndOrderFront_(None)
app.activateIgnoringOtherApps_(True)
app.run()
