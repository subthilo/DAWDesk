import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'r') as f:
    content = f.read()

# We want to replace everything from `def set_pan(self, track_index: int, pan: float):` to the end of the file.
match = re.search(r'    def set_pan\(self, track_index: int, pan: float\):', content)
if match:
    new_tail = """    def set_pan(self, track_index: int, pan: float):
        if not self.outport: return
        if not (0 <= track_index < 400): return
        
        # Echo suppression
        key = (track_index, 0x02)
        self._last_sent[key] = pan
        self._last_sent_time[key] = time.monotonic()
        
        val_7 = int(max(0.0, min(1.0, pan)) * 127)
        channel = track_index // 56
        cc = 64 + (track_index % 56)
        
        self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=val_7))

    def set_solo(self, track_index: int, value: float):
        if not self.outport: return
        if not (0 <= track_index < 400): return
        vel = 127 if value >= 0.5 else 0
        channel = track_index // 120
        note = track_index % 120
        self.outport.send(mido.Message('note_on', channel=channel, note=note, velocity=vel))

    def set_mute(self, track_index: int, value: float):
        if not self.outport: return
        if not (0 <= track_index < 400): return
        vel = 127 if value >= 0.5 else 0
        channel = 4 + (track_index // 120)
        note = track_index % 120
        self.outport.send(mido.Message('note_on', channel=channel, note=note, velocity=vel))

    def send_nudge(self, direction: int):
        if not self.outport: return
        cc = 127 if direction > 0 else 126
        try:
            self.outport.send(mido.Message('control_change', channel=14, control=cc, value=127))
            self.outport.send(mido.Message('control_change', channel=14, control=cc, value=0))
        except Exception as e:
            pass

    def set_transport(self, cmd_id: int, value: float):
        if not self.outport: return
        note = -1
        if cmd_id == 0: note = 104
        elif cmd_id == 1: note = 106
        elif cmd_id == 2: note = 107
        if note >= 0:
            vel = 127 if value > 0.5 else 0
            self.outport.send(mido.Message('note_on', channel=14, note=note, velocity=vel))

    def defeat_all_solos(self):
        if not self.outport: return
        for i in range(400):
            channel = i // 120
            note = i % 120
            self.outport.send(mido.Message('note_on', channel=channel, note=note, velocity=0))

    def defeat_all_mutes(self):
        if not self.outport: return
        for i in range(400):
            channel = 4 + (i // 120)
            note = i % 120
            self.outport.send(mido.Message('note_on', channel=channel, note=note, velocity=0))
"""
    content = content[:match.start()] + new_tail

    with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/cubase_adapter.py', 'w') as f:
        f.write(content)
