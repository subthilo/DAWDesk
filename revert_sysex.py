import re

# FIX DAWDesk_Cubase.js
with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'r') as f:
    js_content = f.read()

# Replace the SysEx String block
old_title_block = r"""        channelBankItem\.mValue\.mVolume\.mOnTitleChange = function\(activeDevice, activeMapping, objectTitle\) \{
            var str = objectTitle \? objectTitle\.toString\(\) : "";
            if \(str === lastTitle\[index\]\) return; // No change → skip
            lastTitle\[index\] = str;
            var maxLen = Math\.min\(str\.length, 20\);
            var track_msb = Math\.floor\(index / 128\);
            var track_lsb = index % 128;
            
            var msg = \[0xF0, 0x7D, 0x01, track_msb, track_lsb\];
            for \(var j = 0; j < maxLen; j\+\+\) \{
                msg\.push\(str\.charCodeAt\(j\) & 0x7F\);
            \}
            msg\.push\(0xF7\);
            midiOutput\.sendMidi\(activeDevice, msg\);
        \};"""

new_title_block = """        channelBankItem.mValue.mVolume.mOnTitleChange = function(activeDevice, activeMapping, objectTitle) {
            var str = objectTitle ? objectTitle.toString() : "";
            if (str === lastTitle[index]) return; // No change → skip
            lastTitle[index] = str;
            var maxLen = Math.min(str.length, 20);
            var track_msb = Math.floor(index / 128);
            var track_lsb = index % 128;
            midiOutput.sendMidi(activeDevice, [0xBF, 110, track_msb]);
            midiOutput.sendMidi(activeDevice, [0xBF, 111, track_lsb]);
            for (var j = 0; j < maxLen; j++) {
                midiOutput.sendMidi(activeDevice, [0xBF, 112, str.charCodeAt(j) & 0x7F]);
            }
            midiOutput.sendMidi(activeDevice, [0xBF, 113, 0]); 
        };"""

js_content = re.sub(old_title_block, new_title_block, js_content)


# Replace the SysEx Color block
old_color_block = r"""        faderElements\[index\]\.mSurfaceValue\.mOnColorChange = function\(activeDevice, r, g, b, a, isActive\) \{
            var ri = r \? Math\.round\(r \* 127\) : 0;
            var gi = g \? Math\.round\(g \* 127\) : 0;
            var bi = b \? Math\.round\(b \* 127\) : 0;
            var track_msb = Math\.floor\(index / 128\);
            var track_lsb = index % 128;
            
            var msg = \[0xF0, 0x7D, 0x02, track_msb, track_lsb, ri, gi, bi, 0xF7\];
            midiOutput\.sendMidi\(activeDevice, msg\);
        \};"""

new_color_block = """        faderElements[index].mSurfaceValue.mOnColorChange = function(activeDevice, r, g, b, a, isActive) {
            var ri = r ? Math.round(r * 127) : 0;
            var gi = g ? Math.round(g * 127) : 0;
            var bi = b ? Math.round(b * 127) : 0;
            var track_msb = Math.floor(index / 128);
            var track_lsb = index % 128;
            midiOutput.sendMidi(activeDevice, [0xBF, 114, track_msb]);
            midiOutput.sendMidi(activeDevice, [0xBF, 115, track_lsb]);
            midiOutput.sendMidi(activeDevice, [0xBF, 116, ri]);
            midiOutput.sendMidi(activeDevice, [0xBF, 117, gi]);
            midiOutput.sendMidi(activeDevice, [0xBF, 118, bi]);
        };"""

js_content = re.sub(old_color_block, new_color_block, js_content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'w') as f:
    f.write(js_content)


# FIX cubase_adapter.py
with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    py_content = f.read()

# Remove the SysEx block
old_sysex_block = r"""        # Track Name & Color via SysEx \(DAWDesk Custom 7D\)
        if msg\.type == 'sysex':
(?:.*?\n){1,25}            return"""

new_sysex_block = """        # Track Name via SysEx (DAWDesk Custom 7D)
        if msg.type == 'sysex':
            return"""
py_content = re.sub(old_sysex_block, new_sysex_block, py_content)


# Add the CC 110-118 block to channel 15 handling!
cc_block_insert = r"""        if msg.type == 'control_change':"""

new_cc_block = """        if msg.type == 'control_change':
            
            # Handle DAWDesk CC-ASCII Stream (Channel 16 -> msg.channel == 15)
            if msg.channel == 15:
                if msg.control == 110:   # Track Index MSB (for Strings)
                    self._str_track_msb = msg.value
                    return
                elif msg.control == 111: # Start Title & LSB
                    self._str_type = 0
                    self._str_track = (getattr(self, '_str_track_msb', 0) * 128) + msg.value
                    self._str_buf = []
                    return
                elif msg.control == 112: # Char Payload
                    self._str_buf.append(msg.value)
                    return
                elif msg.control == 113: # End String
                    parsed_str = bytes(self._str_buf).decode('ascii', errors='ignore')
                    if self._str_type == 0:
                        _log(f"  [Cubase] Track {self._str_track} Name: {parsed_str}")
                        if self._callback:
                            self._callback(0x03, self._str_track, parsed_str)
                    self._str_buf = []
                    return
                
                # COLOR STREAM (CC 114-118)
                elif msg.control == 114: # Color Sync Track MSB
                    self._color_track_msb = msg.value
                    return
                elif msg.control == 115: # Color Sync Track LSB
                    self._color_track = (getattr(self, '_color_track_msb', 0) * 128) + msg.value
                    self._color_rgb = [0, 0, 0]
                    return
                elif msg.control == 116: # Red
                    self._color_rgb[0] = msg.value
                    return
                elif msg.control == 117: # Green
                    self._color_rgb[1] = msg.value
                    return
                elif msg.control == 118: # Blue
                    self._color_rgb[2] = msg.value
                    r = self._color_rgb[0] / 127.0
                    g = self._color_rgb[1] / 127.0
                    b = self._color_rgb[2] / 127.0
                    if r == 0.0 and g == 0.0 and b == 0.0:
                        r, g, b = 0.55, 0.62, 0.68
                    if self._callback:
                        self._callback(0x04, getattr(self, '_color_track', 0), (r, g, b))
                    return"""

py_content = py_content.replace("        if msg.type == 'control_change':", new_cc_block)

# Fix VU Meters Channel Range!
py_content = py_content.replace("if msg.channel in range(8, 15) and 64 <= msg.control <= 119:", "if msg.channel in range(8, 16) and 64 <= msg.control <= 119:")

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(py_content)

