with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

patch = """    async def initial_request():
        await asyncio.sleep(5.0)
        await request_cubase_state()"""

import re
content = re.sub(r"    async def initial_request\(\):\n        await asyncio\.sleep\(5\.0\)\n        if not _received_cubase_events:\n            await request_cubase_state\(\)", patch, content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
