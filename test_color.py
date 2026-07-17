import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

match = re.search(r'            elif cmd == 0x04:\n                state\.update_track_color\(track, val\)', content)
if match:
    replacement = """            elif cmd == 0x04:
                _log(f"  [Cubase] Track {track} Color: {val}")
                state.update_track_color(track, val)"""
    content = content[:match.start()] + replacement + content[match.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
