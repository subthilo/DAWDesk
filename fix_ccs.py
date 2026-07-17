with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'r') as f:
    content = f.read()

content = content.replace('.bindToControlChange(14, 126)', '.bindToControlChange(14, 62)')
content = content.replace('.bindToControlChange(14, 127)', '.bindToControlChange(14, 63)')
content = content.replace('.bindToControlChange(14, 124)', '.bindToControlChange(14, 60)')
content = content.replace('.bindToControlChange(14, 125)', '.bindToControlChange(14, 61)')

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/daw_scripts/cubase/DAWDesk_Cubase.js', 'w') as f:
    f.write(content)


with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    py_content = f.read()

py_content = py_content.replace('cc = 125 if direction > 0 else 124', 'cc = 61 if direction > 0 else 60')
py_content = py_content.replace('cc = 127 if direction > 0 else 126', 'cc = 63 if direction > 0 else 62')

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(py_content)
