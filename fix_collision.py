import re

# FIX DAWDesk_Cubase.js
with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'r') as f:
    js_content = f.read()

# Replace String CCs
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 10, track_msb]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 50, track_msb]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 11, track_lsb]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 51, track_lsb]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 13, str.charCodeAt(j) & 0x7F]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 53, str.charCodeAt(j) & 0x7F]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 14, 0]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 54, 0]);')

# Replace Color CCs
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 15, track_msb]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 55, track_msb]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 16, track_lsb]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 56, track_lsb]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 17, ri]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 57, ri]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 18, gi]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 58, gi]);')
js_content = js_content.replace('midiOutput.sendMidi(activeDevice, [0xBE, 19, bi]);', 'midiOutput.sendMidi(activeDevice, [0xBE, 59, bi]);')

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'w') as f:
    f.write(js_content)


# FIX cubase_adapter.py
with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    py_content = f.read()

match = re.search(r'                if msg\.control == 10:   # Track Index MSB \(for Strings\)\n(?:.*?\n){1,30}                        self\._callback\(0x04, getattr\(self, \'_color_track\', 0\), \(r, g, b\)\)\n                    return', py_content, re.MULTILINE | re.DOTALL)

if match:
    replacement = """                if msg.control == 50:   # Track Index MSB (for Strings)
                    self._str_track_msb = msg.value
                    return
                elif msg.control == 51: # Start Title & LSB
                    self._str_type = 0
                    self._str_track = (getattr(self, '_str_track_msb', 0) * 128) + msg.value
                    self._str_buf = []
                    return
                elif msg.control == 52: # Start Value & LSB
                    self._str_type = 1
                    self._str_track = (getattr(self, '_str_track_msb', 0) * 128) + msg.value
                    self._str_buf = []
                    return
                elif msg.control == 53: # Char Payload
                    self._str_buf.append(msg.value)
                    return
                elif msg.control == 54: # End String
                    parsed_str = bytes(self._str_buf).decode('ascii', errors='ignore')
                    if self._str_type == 0:
                        _log(f"  [Cubase] Track {self._str_track} Name: {parsed_str}")
                        if self._callback:
                            self._callback(0x03, self._str_track, parsed_str)
                    elif self._str_type == 1:
                        pass
                    self._str_buf = []
                    return
                
                # COLOR STREAM (CC 55-59)
                elif msg.control == 55: # Color Sync Track MSB
                    self._color_track_msb = msg.value
                    return
                elif msg.control == 56: # Color Sync Track LSB
                    self._color_track = (getattr(self, '_color_track_msb', 0) * 128) + msg.value
                    self._color_rgb = [0, 0, 0]
                    return
                elif msg.control == 57: # Red
                    self._color_rgb[0] = msg.value
                    return
                elif msg.control == 58: # Green
                    self._color_rgb[1] = msg.value
                    return
                elif msg.control == 59: # Blue
                    self._color_rgb[2] = msg.value
                    r = self._color_rgb[0] / 127.0
                    g = self._color_rgb[1] / 127.0
                    b = self._color_rgb[2] / 127.0
                    if r == 0.0 and g == 0.0 and b == 0.0:
                        r, g, b = 0.55, 0.62, 0.68
                    if self._callback:
                        self._callback(0x04, getattr(self, '_color_track', 0), (r, g, b))
                    return"""
    py_content = py_content[:match.start()] + replacement + py_content[match.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(py_content)

