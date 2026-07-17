import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

match = re.search(r'                if msg\.control == 115:   # Start Title\n(?:.*?\n){1,30}                        self\._callback\(0x04, self\._color_track, \(r, g, b\)\)\n                    return', content, re.MULTILINE | re.DOTALL)
if match:
    replacement = """                if msg.control == 114:   # Track Index MSB (for Strings)
                    self._str_track_msb = msg.value
                    return
                elif msg.control == 115: # Start Title & LSB
                    self._str_type = 0
                    self._str_track = (getattr(self, '_str_track_msb', 0) * 128) + msg.value
                    self._str_buf = []
                    return
                elif msg.control == 116: # Start Value & LSB
                    self._str_type = 1
                    self._str_track = (getattr(self, '_str_track_msb', 0) * 128) + msg.value
                    self._str_buf = []
                    return
                elif msg.control == 117: # Char Payload
                    self._str_buf.append(msg.value)
                    return
                elif msg.control == 118: # End String
                    parsed_str = bytes(self._str_buf).decode('ascii', errors='ignore')
                    if self._str_type == 0:
                        _log(f"  [Cubase] Track {self._str_track} Name: {parsed_str}")
                        if self._callback:
                            self._callback(0x03, self._str_track, parsed_str)
                    elif self._str_type == 1:
                        pass
                    self._str_buf = []
                    return
                
                # COLOR STREAM (CC 119-123)
                elif msg.control == 119: # Color Sync Track MSB
                    self._color_track_msb = msg.value
                    return
                elif msg.control == 120: # Color Sync Track LSB
                    self._color_track = (getattr(self, '_color_track_msb', 0) * 128) + msg.value
                    self._color_rgb = [0, 0, 0]
                    return
                elif msg.control == 121: # Red
                    self._color_rgb[0] = msg.value
                    return
                elif msg.control == 122: # Green
                    self._color_rgb[1] = msg.value
                    return
                elif msg.control == 123: # Blue
                    self._color_rgb[2] = msg.value
                    r = self._color_rgb[0] / 127.0
                    g = self._color_rgb[1] / 127.0
                    b = self._color_rgb[2] / 127.0
                    if r == 0.0 and g == 0.0 and b == 0.0:
                        r, g, b = 0.55, 0.62, 0.68
                    if self._callback:
                        self._callback(0x04, getattr(self, '_color_track', 0), (r, g, b))
                    return"""
    content = content[:match.start()] + replacement + content[match.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(content)
