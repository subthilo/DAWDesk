import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/state.py', 'r') as f:
    content = f.read()

match = re.search(r'    def get_track_color', content)
if match:
    replacement = """    def get_project_size(self) -> int:
        max_idx = -1
        for idx, name in self.track_names.items():
            if name.strip():
                if idx > max_idx:
                    max_idx = idx
        return max_idx + 1

    def get_track_color"""
    content = content[:match.start()] + replacement + content[match.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/state.py', 'w') as f:
    f.write(content)
