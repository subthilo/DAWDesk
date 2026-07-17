with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

import re
old = r"            self\.outport\.send\(mido\.Message\('control_change', channel=14, control=cc, value=127\)\)\n            self\.outport\.send\(mido\.Message\('control_change', channel=14, control=cc, value=0\)\)"
new = """            self.outport.send(mido.Message('control_change', channel=14, control=cc, value=127))
            import time
            time.sleep(0.05)
            self.outport.send(mido.Message('control_change', channel=14, control=cc, value=0))"""

content = re.sub(old, new, content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(content)
