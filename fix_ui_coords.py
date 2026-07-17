with open("daw_scripts/cubase/DAWDesk_Cubase.js", "r") as f:
    code = f.read()

# We need to wrap the coordinates so they don't exceed the width, or just stack them!
# We can just put them on rows!
# Let's say max width is 60 elements (x = 0 to 118).
# So row = Math.floor(i / 60)
# x = (i % 60) * 2
# y_fader = 2 + row * 10
# etc...

import re
code = code.replace("deviceSurface.makeFader(i * 2, 2, 2, 4)", "deviceSurface.makeFader((i % 60) * 2, 2 + Math.floor(i / 60) * 15, 2, 4)")
code = code.replace("deviceSurface.makeKnob(i * 2, 0, 2, 2)", "deviceSurface.makeKnob((i % 60) * 2, 0 + Math.floor(i / 60) * 15, 2, 2)")
code = code.replace("deviceSurface.makeButton(i * 2, 7, 1, 1)", "deviceSurface.makeButton((i % 60) * 2, 7 + Math.floor(i / 60) * 15, 1, 1)")
code = code.replace("deviceSurface.makeButton(i * 2 + 1, 7, 1, 1)", "deviceSurface.makeButton((i % 60) * 2 + 1, 7 + Math.floor(i / 60) * 15, 1, 1)")
code = code.replace("deviceSurface.makeKnob(i * 2, 10, 1, 1)", "deviceSurface.makeKnob((i % 60) * 2, 10 + Math.floor(i / 60) * 15, 1, 1)")
code = code.replace("deviceSurface.makeLabelField(i * 2, 6, 2, 1)", "deviceSurface.makeLabelField((i % 60) * 2, 6 + Math.floor(i / 60) * 15, 2, 1)")

with open("daw_scripts/cubase/DAWDesk_Cubase.js", "w") as f:
    f.write(code)

