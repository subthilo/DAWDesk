import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/osc_server.py', 'r') as f:
    content = f.read()

match = re.search(r'                    max_offset = max\(0, 400 - displayable_channels\)', content)
if match:
    replacement = """                    project_size = state.get_project_size()
                    if project_size <= 0:
                        project_size = 400  # Fallback
                    max_offset = max(0, project_size - displayable_channels)"""
    content = content[:match.start()] + replacement + content[match.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/osc_server.py', 'w') as f:
    f.write(content)
