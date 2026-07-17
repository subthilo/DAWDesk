import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'r') as f:
    content = f.read()

# Replace String handling
match_str = re.search(r'        // Track Name \(cached.*?midiOutput\.sendMidi\(activeDevice, \[0xBE, 118, 0\]\);.*?};', content, re.MULTILINE | re.DOTALL)
if match_str:
    replacement_str = """        // Track Name (cached)
        channelBankItem.mValue.mVolume.mOnTitleChange = function(activeDevice, activeMapping, objectTitle) {
            var str = objectTitle ? objectTitle.toString() : "";
            if (str === lastTitle[index]) return; // No change → skip
            lastTitle[index] = str;
            var maxLen = Math.min(str.length, 20);
            var track_msb = Math.floor(index / 128);
            var track_lsb = index % 128;
            midiOutput.sendMidi(activeDevice, [0xBE, 114, track_msb]);
            midiOutput.sendMidi(activeDevice, [0xBE, 115, track_lsb]);
            for (var j = 0; j < maxLen; j++) {
                midiOutput.sendMidi(activeDevice, [0xBE, 117, str.charCodeAt(j) & 0x7F]);
            }
            midiOutput.sendMidi(activeDevice, [0xBE, 118, 0]); 
        };"""
    content = content[:match_str.start()] + replacement_str + content[match_str.end():]

# Replace Color handling
match_col = re.search(r'        // Send Track Color.*?midiOutput\.sendMidi\(activeDevice, \[0xBE, 123, bi\]\);.*?};', content, re.MULTILINE | re.DOTALL)
if match_col:
    replacement_col = """        // Send Track Color
        faderElements[index].mSurfaceValue.mOnColorChange = function(activeDevice, r, g, b, a, isActive) {
            var ri = r ? Math.round(r * 127) : 0;
            var gi = g ? Math.round(g * 127) : 0;
            var bi = b ? Math.round(b * 127) : 0;
            var track_msb = Math.floor(index / 128);
            var track_lsb = index % 128;
            midiOutput.sendMidi(activeDevice, [0xBE, 119, track_msb]);
            midiOutput.sendMidi(activeDevice, [0xBE, 120, track_lsb]);
            midiOutput.sendMidi(activeDevice, [0xBE, 121, ri]);
            midiOutput.sendMidi(activeDevice, [0xBE, 122, gi]);
            midiOutput.sendMidi(activeDevice, [0xBE, 123, bi]);
        };"""
    content = content[:match_col.start()] + replacement_col + content[match_col.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'w') as f:
    f.write(content)
