with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

import re
old = r"        if direction > 0:\n            msg = mido\.Message\('note_on', channel=15, note=127, velocity=127\) # Next Bank\n        else:\n            msg = mido\.Message\('note_on', channel=15, note=126, velocity=127\) # Prev Bank"
new = """        if direction > 0:
            msg = mido.Message('control_change', channel=14, control=127, value=127) # Next Bank
        else:
            msg = mido.Message('control_change', channel=14, control=126, value=127) # Prev Bank"""

content = re.sub(old, new, content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(content)
