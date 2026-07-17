with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

import re

# Remove the initial_request task
content = re.sub(r"    async def initial_request\(\):\n        await asyncio\.sleep\(5\.0\)\n        await request_cubase_state\(\)\n    \n    asyncio\.create_task\(initial_request\(\)\)\n", "", content)

# Modify on_cubase_event to trigger sync
old_event = r"    def on_cubase_event\(cmd, track_index, value\):"
new_event = """    def on_cubase_event(cmd, track_index, value):
        nonlocal _received_cubase_events
        if not _received_cubase_events:
            _received_cubase_events = True
            async def delayed_sync():
                await asyncio.sleep(2.0)
                await request_cubase_state()
            asyncio.create_task(delayed_sync())
"""
content = content.replace(old_event, new_event)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
