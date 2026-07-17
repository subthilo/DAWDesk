with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

import re

old_queue = r"        while not _midi_queue\.empty\(\):"
new_queue = """        if not _midi_queue.empty() and not _received_cubase_events:
            _received_cubase_events = True
            async def delayed_sync():
                await asyncio.sleep(2.0)
                await request_cubase_state()
            asyncio.create_task(delayed_sync())

        while not _midi_queue.empty():"""

content = content.replace("        while not _midi_queue.empty():", new_queue)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
