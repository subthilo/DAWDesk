with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

patch = """    def parse_midi_message(self, msg: mido.Message):
        if hasattr(msg, 'channel') and msg.channel == 15:
            _log(f"[Cubase -> Broker] RAW CH16: {msg}")"""

content = content.replace("    def parse_midi_message(self, msg: mido.Message):\n        if _MIDI_DEBUG:\n            _log(f\"[Cubase -> Broker] {msg}\")", patch)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(content)
