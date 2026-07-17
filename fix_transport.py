import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

match = re.search(r'    def set_transport\(self, cmd_id: int, value: float\):\n(?:.*?\n){1,10}            self.outport.send\(mido.Message\(\'note_on\', channel=14, note=note, velocity=vel\)\)', content, re.MULTILINE | re.DOTALL)

if match:
    new_func = """    def set_transport(self, cmd_idx: int, value: float):
        if not self.outport: return
        import asyncio
        async def send_click(ch, note):
            self.outport.send(mido.Message('note_on', channel=ch, note=note, velocity=127))
            await asyncio.sleep(0.05)
            self.outport.send(mido.Message('note_off', channel=ch, note=note, velocity=0))

        if cmd_idx == 0:  # Play/Pause
            if value >= 0.5:
                asyncio.create_task(send_click(14, 104))
            else:
                asyncio.create_task(send_click(14, 105))
        elif cmd_idx == 1:  # Record
            asyncio.create_task(send_click(14, 106))
        elif cmd_idx == 2:  # Loop
            asyncio.create_task(send_click(14, 107))"""
    content = content[:match.start()] + new_func + content[match.end():]
    
    with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
        f.write(content)
