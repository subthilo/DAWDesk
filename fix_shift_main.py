with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

content = content.replace('cubase_adapter.send_nudge(-1)', 'cubase_adapter.send_shift(-1)')
content = content.replace('cubase_adapter.send_nudge(1)', 'cubase_adapter.send_shift(1)')

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
