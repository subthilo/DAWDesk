with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

import re
old = r"    def send_nudge\(self, direction: int\):"
new = """    def send_shift(self, direction: int):
        if not self.outport: return
        cc = 125 if direction > 0 else 124
        try:
            self.outport.send(mido.Message('control_change', channel=14, control=cc, value=127))
            import time
            time.sleep(0.05)
            self.outport.send(mido.Message('control_change', channel=14, control=cc, value=0))
        except Exception as e:
            pass

    def send_nudge(self, direction: int):"""

content = re.sub(old, new, content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(content)


with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    main_content = f.read()

main_old = r"            cubase_adapter\.send_nudge\(-1\)\s*await asyncio\.sleep\(0\.1\)\s*cubase_adapter\.send_nudge\(1\)\s*await asyncio\.sleep\(0\.4\)\s*cubase_adapter\.send_nudge\(-1\)"
main_new = """            cubase_adapter.send_shift(-1)
            await asyncio.sleep(0.1)
            cubase_adapter.send_shift(1)
            await asyncio.sleep(0.4)
            cubase_adapter.send_shift(-1)"""

main_content = re.sub(main_old, main_new, main_content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(main_content)
