with open("broker/cubase_adapter.py", "r") as f:
    text = f.read()

import re
header = text.split("def _on_midi_in(self, msg):")[0]

new_code = """    def _on_midi_in(self, msg):
        self.parse_midi_message(msg)

    def parse_midi_message(self, msg: mido.Message):
        if _MIDI_DEBUG:
            _log(f"[Cubase -> Broker] {msg}")

        # Transport Feedback (Channel 15, CC 104-105 for Play/Stop, Note 106-107 for Rec/Cycle)
        if msg.channel == 14:
            if msg.type == "control_change":
                float_val = msg.value / 127.0
                if msg.control == 104:
                    self._fire_callback(0x08, 0, float_val)
                elif msg.control == 105:
                    if float_val >= 0.5:
                        self._fire_callback(0x08, 0, 0.0)
                return
            elif msg.type in ("note_on", "note_off"):
                float_val = 1.0 if (msg.type == "note_on" and msg.velocity > 0) else 0.0
                if msg.note == 106:
                    self._fire_callback(0x08, 1, float_val)
                elif msg.note == 107:
                    self._fire_callback(0x08, 2, float_val)
                return

        # HACK: Transport Locator (PitchBend on Channel 15)
        if msg.type == "pitchwheel" and msg.channel == 14:
            # We don't care about the value, just the timing
            self._fire_callback(0x09, 0, 1.0)
            return

        # Solo (Note On) - Ch 0, 1
        if msg.type in ("note_on", "note_off") and msg.channel in (0, 1):
            track_index = (msg.channel * 120) + msg.note
            float_val = 1.0 if (msg.type == "note_on" and msg.velocity > 0) else 0.0
            self._fire_callback(0x05, track_index, float_val)
            return

        # Mute (Note On) - Ch 2, 3
        if msg.type in ("note_on", "note_off") and msg.channel in (2, 3):
            track_index = ((msg.channel - 2) * 120) + msg.note
            float_val = 1.0 if (msg.type == "note_on" and msg.velocity > 0) else 0.0
            self._fire_callback(0x06, track_index, float_val)
            return

        if msg.type == "control_change":
            if msg.channel == 14:
                if msg.control == 115:
                    self._str_type = 0
                    self._str_track = msg.value
                    self._str_buf = []
                    return
                elif msg.control == 114:
                    self._str_type = 0
                    self._str_track = msg.value + 120
                    self._str_buf = []
                    return
                elif msg.control == 116:
                    self._str_type = 1
                    self._str_track = msg.value
                    self._str_buf = []
                    return
                elif msg.control == 119:
                    self._str_type = 2
                    self._str_track = 0
                    self._str_buf = []
                    return
                elif msg.control == 117:
                    self._str_buf.append(msg.value)
                    return
                elif msg.control == 118:
                    parsed_str = bytes(self._str_buf).decode("ascii", errors="ignore")
                    if self._str_type == 0:
                        _log(f"  [Cubase] Track {self._str_track} Name: {parsed_str}")
                        if self._callback:
                            self._callback(0x03, self._str_track, parsed_str)
                    elif self._str_type == 1:
                        pass
                    elif self._str_type == 2:
                        _log(f"  [Cubase] DEBUG BUTTON PRESSED! Content: {parsed_str}")
                    self._str_buf = []
                    return
                elif msg.control == 120:
                    self._color_track = msg.value
                    self._color_rgb = [0, 0, 0]
                    return
                elif msg.control == 113:
                    self._color_track = msg.value + 120
                    self._color_rgb = [0, 0, 0]
                    return
                elif msg.control == 121:
                    self._color_rgb[0] = msg.value
                    return
                elif msg.control == 122:
                    self._color_rgb[1] = msg.value
                    return
                elif msg.control == 123:
                    self._color_rgb[2] = msg.value
                    r = self._color_rgb[0] / 127.0
                    g = self._color_rgb[1] / 127.0
                    b = self._color_rgb[2] / 127.0
                    if self._callback:
                        self._callback(0x04, self._color_track, (r, g, b))
                    return

            # Pan (7-bit) - Ch 8, 9
            if msg.channel in (8, 9) and 1 <= msg.control <= 120:
                track_index = ((msg.channel - 8) * 120) + (msg.control - 1)
                float_val = msg.value / 127.0
                self._fire_callback(0x02, track_index, float_val)
                return
            
            # VU Meter (7-bit) - Ch 10, 11
            if msg.channel in (10, 11) and 1 <= msg.control <= 120:
                track_index = ((msg.channel - 10) * 120) + (msg.control - 1)
                float_val = msg.value / 127.0
                self._fire_callback(0x07, track_index, float_val)
                return
            
            # Volume MSB - Ch 0..7
            if 0 <= msg.channel <= 7 and ((1 <= msg.control <= 5) or (7 <= msg.control <= 31)):
                track_offset = _msb_cc_to_track(msg.control)
                track_index = (msg.channel * 30) + track_offset
                self._msb_cache[track_index] = msg.value
                return
            
            # Volume LSB - Ch 0..7
            if 0 <= msg.channel <= 7 and ((33 <= msg.control <= 37) or (39 <= msg.control <= 63)):
                msb_cc = msg.control - 32
                track_offset = _msb_cc_to_track(msb_cc)
                track_index = (msg.channel * 30) + track_offset
                msb = self._msb_cache.get(track_index, 0)
                val_14 = (msb << 7) | msg.value
                float_val = val_14 / 16383.0
                self._fire_callback(0x01, track_index, float_val)
                return

    def set_volume(self, track_index: int, volume: float):
        if not self.outport: return
        key = (track_index, 0x01)
        self._last_sent[key] = volume
        self._last_sent_time[key] = time.monotonic()
        val_14 = int(max(0.0, min(1.0, volume)) * 16383)
        msb = (val_14 >> 7) & 0x7F
        lsb = val_14 & 0x7F
        channel = track_index // 30
        cc_msb = _track_to_msb_cc(track_index % 30)
        cc_lsb = cc_msb + 32
        self.outport.send(mido.Message("control_change", channel=channel, control=cc_msb, value=msb))
        self.outport.send(mido.Message("control_change", channel=channel, control=cc_lsb, value=lsb))

    def set_pan(self, track_index: int, pan: float):
        if not self.outport: return
        key = (track_index, 0x02)
        self._last_sent[key] = pan
        self._last_sent_time[key] = time.monotonic()
        val_7 = int(max(0.0, min(1.0, pan)) * 127)
        channel = 8 + (track_index // 120)
        cc = 1 + (track_index % 120)
        self.outport.send(mido.Message("control_change", channel=channel, control=cc, value=val_7))

    def set_solo(self, track_index: int, value: float):
        if not self.outport: return
        vel = 127 if value >= 0.5 else 0
        channel = 0 + (track_index // 120)
        note = track_index % 120
        self.outport.send(mido.Message("note_on", channel=channel, note=note, velocity=vel))

    def set_mute(self, track_index: int, value: float):
        if not self.outport: return
        vel = 127 if value >= 0.5 else 0
        channel = 2 + (track_index // 120)
        note = track_index % 120
        self.outport.send(mido.Message("note_on", channel=channel, note=note, velocity=vel))
        
    def set_transport(self, cmd_idx: int, value: float):
        if not self.outport: return
        # cmd_idx: 0=Play, 1=Rec, 2=Loop
        # We send a quick CC 127 / CC 0 to simulate button press
        import asyncio
        async def send_click(ch, cc):
            self.outport.send(mido.Message("control_change", channel=ch, control=cc, value=127))
            await asyncio.sleep(0.05)
            self.outport.send(mido.Message("control_change", channel=ch, control=cc, value=0))

        if cmd_idx == 0:
            if value >= 0.5:
                asyncio.create_task(send_click(14, 104))
            else:
                asyncio.create_task(send_click(14, 105))
        elif cmd_idx == 1:
            vel = 127 if value >= 0.5 else 0
            self.outport.send(mido.Message("note_on", channel=14, note=106, velocity=vel))
        elif cmd_idx == 2:
            vel = 127 if value >= 0.5 else 0
            self.outport.send(mido.Message("note_on", channel=14, note=107, velocity=vel))

    def defeat_all_solos(self):
        if not self.outport: return
        for i in range(240):
            channel = 0 + (i // 120)
            note = i % 120
            self.outport.send(mido.Message("note_on", channel=channel, note=note, velocity=0))
        for i in range(239, -1, -1):
            channel = 0 + (i // 120)
            note = i % 120
            self.outport.send(mido.Message("note_on", channel=channel, note=note, velocity=0))

    def defeat_all_mutes(self):
        if not self.outport: return
        for i in range(240):
            channel = 2 + (i // 120)
            note = i % 120
            self.outport.send(mido.Message("note_on", channel=channel, note=note, velocity=0))
        for i in range(239, -1, -1):
            channel = 2 + (i // 120)
            note = i % 120
            self.outport.send(mido.Message("note_on", channel=channel, note=note, velocity=0))

    def send_nudge(self, direction: int):
        if not self.outport:
            return
        cc = 126 if direction == -1 else 127
        msg_down = mido.Message('control_change', channel=14, control=cc, value=127)
        msg_up = mido.Message('control_change', channel=14, control=cc, value=0)
        try:
            self.outport.send(msg_down)
            self.outport.send(msg_up)
        except Exception:
            pass
"""

with open("broker/cubase_adapter.py", "w") as f:
    f.write(header + new_code)
