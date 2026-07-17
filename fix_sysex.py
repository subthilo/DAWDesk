import re

# FIX DAWDesk_Cubase.js
with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'r') as f:
    js_content = f.read()

# Replace the mOnTitleChange block
old_title_block = r"""        channelBankItem\.mValue\.mVolume\.mOnTitleChange = function\(activeDevice, activeMapping, objectTitle\) \{
            var str = objectTitle \? objectTitle\.toString\(\) : "";
            if \(str === lastTitle\[index\]\) return; // No change → skip
            lastTitle\[index\] = str;
            var maxLen = Math\.min\(str\.length, 20\);
            var track_msb = Math\.floor\(index / 128\);
            var track_lsb = index % 128;
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 50, track_msb\]\);
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 51, track_lsb\]\);
            for \(var j = 0; j < maxLen; j\+\+\) \{
                midiOutput\.sendMidi\(activeDevice, \[0xBE, 53, str\.charCodeAt\(j\) & 0x7F\]\);
            \}
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 54, 0\]\); 
        \};"""

new_title_block = """        channelBankItem.mValue.mVolume.mOnTitleChange = function(activeDevice, activeMapping, objectTitle) {
            var str = objectTitle ? objectTitle.toString() : "";
            if (str === lastTitle[index]) return; // No change → skip
            lastTitle[index] = str;
            var maxLen = Math.min(str.length, 20);
            var track_msb = Math.floor(index / 128);
            var track_lsb = index % 128;
            
            var msg = [0xF0, 0x7D, 0x01, track_msb, track_lsb];
            for (var j = 0; j < maxLen; j++) {
                msg.push(str.charCodeAt(j) & 0x7F);
            }
            msg.push(0xF7);
            midiOutput.sendMidi(activeDevice, msg);
        };"""

js_content = re.sub(old_title_block, new_title_block, js_content)


# Replace the mOnColorChange block
old_color_block = r"""        faderElements\[index\]\.mSurfaceValue\.mOnColorChange = function\(activeDevice, r, g, b, a, isActive\) \{
            var ri = r \? Math\.round\(r \* 127\) : 0;
            var gi = g \? Math\.round\(g \* 127\) : 0;
            var bi = b \? Math\.round\(b \* 127\) : 0;
            var track_msb = Math\.floor\(index / 128\);
            var track_lsb = index % 128;
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 55, track_msb\]\);
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 56, track_lsb\]\);
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 57, ri\]\);
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 58, gi\]\);
            midiOutput\.sendMidi\(activeDevice, \[0xBE, 59, bi\]\);
        \};"""

new_color_block = """        faderElements[index].mSurfaceValue.mOnColorChange = function(activeDevice, r, g, b, a, isActive) {
            var ri = r ? Math.round(r * 127) : 0;
            var gi = g ? Math.round(g * 127) : 0;
            var bi = b ? Math.round(b * 127) : 0;
            var track_msb = Math.floor(index / 128);
            var track_lsb = index % 128;
            
            var msg = [0xF0, 0x7D, 0x02, track_msb, track_lsb, ri, gi, bi, 0xF7];
            midiOutput.sendMidi(activeDevice, msg);
        };"""

js_content = re.sub(old_color_block, new_color_block, js_content)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'w') as f:
    f.write(js_content)


# FIX cubase_adapter.py
with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    py_content = f.read()

# Replace the SysEx block
old_sysex_block = r"""        # Track Name via SysEx \(DAWDesk Custom 7D\)
        if msg\.type == 'sysex':
            return"""

new_sysex_block = """        # Track Name & Color via SysEx (DAWDesk Custom 7D)
        if msg.type == 'sysex':
            if len(msg.data) >= 3 and msg.data[0] == 0x7D:
                cmd = msg.data[1]
                track_index = (msg.data[2] * 128) + msg.data[3]
                
                if cmd == 0x01: # String Name
                    name_bytes = msg.data[4:]
                    parsed_str = bytes(name_bytes).decode('ascii', errors='ignore')
                    if self._callback:
                        self._callback(0x03, track_index, parsed_str)
                
                elif cmd == 0x02: # Color
                    if len(msg.data) >= 7:
                        r = msg.data[4] / 127.0
                        g = msg.data[5] / 127.0
                        b = msg.data[6] / 127.0
                        if r == 0.0 and g == 0.0 and b == 0.0:
                            r, g, b = 0.55, 0.62, 0.68
                        if self._callback:
                            self._callback(0x04, track_index, (r, g, b))
            return"""
py_content = re.sub(old_sysex_block, new_sysex_block, py_content)


# Remove the CC 50-59 block entirely!
cc_block = r"""                if msg\.control == 50:   # Track Index MSB \(for Strings\)\n(?:.*?\n){1,30}                        self\._callback\(0x04, getattr\(self, \'_color_track\', 0\), \(r, g, b\)\)\n                    return"""

py_content = re.sub(cc_block, """                pass""", py_content, flags=re.MULTILINE|re.DOTALL)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(py_content)

