with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

import re

new_task = """    async def self_healing_loop():
        while True:
            await asyncio.sleep(5.0)
            if len(state._strings) == 0:
                _log("Self-healing: No names received yet. Forcing Cubase refresh...")
                await request_cubase_state()

    asyncio.create_task(self_healing_loop())
    
    # 4. Background tasks"""

content = content.replace("    # 4. Background tasks", new_task)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
