with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

patch = """    def _incoming_midi_loop(self):
        with open("raw_midi.txt", "w") as dump_file:
            for msg in self.inport:
                dump_file.write(str(msg) + "\\n")
                dump_file.flush()
                self.parse_midi_message(msg)"""

content = content.replace("    def _incoming_midi_loop(self):\n        for msg in self.inport:\n            self.parse_midi_message(msg)", patch)

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
    f.write(content)
