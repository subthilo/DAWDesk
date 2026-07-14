import mido
import platform
import os
import time
import asyncio
from .logger import _log

# Set DAWDESK_MIDI_DEBUG=1 to log every MIDI message
_MIDI_DEBUG = False


def _track_to_msb_cc(track_within_channel: int) -> int:
    """Convert track offset (0-29) to MSB CC number, skipping CC 6 (Data Entry)."""
    cc = 1 + track_within_channel
    if cc >= 6:
        cc += 1
    return cc


def _msb_cc_to_track(cc: int) -> int:
    """Convert MSB CC number back to track offset, undoing CC 6 skip."""
    if cc > 6:
        cc -= 1
    return cc - 1

class CubaseAdapter:
    def __init__(self, port_name="DAWDesk"):
        self.port_name = port_name
        self.outport = None
        self.inport = None
        self._callback = None
        # 14-bit reconstruction cache (MSB per track, keyed by track_index)
        self._msb_cache = {}
        # Dedup cache: stores last forwarded float per (track, cmd) to suppress echoes
        self._last_sent = {}
        # Time-based echo suppression: timestamp of last set_volume/set_pan per (track, cmd)
        self._last_sent_time = {}
        # CC-ASCII stream state (Channel 15 protocol)
        self._str_type = 0     # 0=title, 1=value, 2=debug
        self._str_track = 0
        self._str_buf = []
        # Color stream state
        self._color_track = 0
        self._color_rgb = [0, 0, 0]
        self._init_midi()

    def _init_midi(self):
        try:
            # On macOS/Linux, rtmidi supports creating virtual ports
            if platform.system() == "Darwin" or platform.system() == "Linux":
                self.outport = mido.open_output(self.port_name, virtual=True)
                self.inport = mido.open_input(self.port_name, virtual=True)
                _log(f"[Cubase] Opened virtual MIDI ports (In/Out): {self.port_name}")
            else:
                # On Windows, loopMIDI is required to create virtual ports.
                available_ports = mido.get_output_names()
                target_port = next((p for p in available_ports if self.port_name in p), None)
                if target_port:
                    self.outport = mido.open_output(target_port)
                    self.inport = mido.open_input(target_port)
                    _log(f"[Cubase] Connected to MIDI port: {target_port}")
                else:
                    _log(f"[Cubase] ERROR: Port '{self.port_name}' not found. Please create it using loopMIDI.")
        except Exception as e:
            _log(f"[Cubase] Failed to initialize MIDI: {e}")

        if self.inport:
            self.inport.callback = self._on_midi_in

    def set_callback(self, callback):
        """Register a callback: func(command, track_index, float_val)"""
        self._callback = callback

    def _fire_callback(self, cmd, track_index, value):
        """Fire callback only if value actually changed (dedup + time-based echo suppression)."""
        key = (track_index, cmd)
        if cmd in (0x01, 0x02):
            # Time-based: suppress ALL echoes for 150ms after we sent to Cubase.
            # This prevents stale echoes (from earlier sends) from leaking through.
            sent_time = self._last_sent_time.get(key, 0)
            if time.monotonic() - sent_time < 0.15:
                return  # echo within suppression window
            
            # Value-based: suppress near-identical values (steady-state dedup)
            old = self._last_sent.get(key)
            if old is not None and abs(old - value) < 0.005:
                return
            self._last_sent[key] = value
        if self._callback:
            self._callback(cmd, track_index, value)

    def _on_midi_in(self, msg):
        self.parse_midi_message(msg)

    def parse_midi_message(self, msg: mido.Message):
        if _MIDI_DEBUG:
            _log(f"[Cubase -> Broker] {msg}")

        # Transport Feedback (Channel 15, Notes 104-107)
        if msg.type in ('note_on', 'note_off') and msg.channel == 14 and 104 <= msg.note <= 107:
            float_val = 1.0 if (msg.type == 'note_on' and msg.velocity > 0) else 0.0
            if msg.note == 104:
                self._fire_callback(0x08, 0, float_val)  # play
            elif msg.note == 105:
                if float_val == 1.0: # stopped
                    self._fire_callback(0x08, 0, 0.0) # set play to false
            elif msg.note == 106:
                self._fire_callback(0x08, 1, float_val)  # rec
            elif msg.note == 107:
                self._fire_callback(0x08, 2, float_val)  # loop
            return

        # Track Name via SysEx (DAWDesk Custom 7D)
        if msg.type == 'sysex':
            return
            
        if msg.type == 'control_change':
            # Handle DAWDesk CC-ASCII Stream (Channel 15 -> msg.channel == 14)
            if msg.channel == 14:
                if msg.control == 115:   # Start Title
                    self._str_type = 0
                    self._str_track = msg.value
                    self._str_buf = []
                    return
                elif msg.control == 116: # Start Value
                    self._str_type = 1
                    self._str_track = msg.value
                    self._str_buf = []
                    return
                elif msg.control == 119: # Start Debug
                    self._str_type = 2
                    self._str_track = 0
                    self._str_buf = []
                    return
                elif msg.control == 117: # Char Payload
                    self._str_buf.append(msg.value)
                    return
                elif msg.control == 118: # End String
                    parsed_str = bytes(self._str_buf).decode('ascii', errors='ignore')
                    if self._str_type == 0:
                        _log(f"  [Cubase] Track {self._str_track} Name: {parsed_str}")
                        if self._callback:
                            self._callback(0x03, self._str_track, parsed_str)
                    elif self._str_type == 1:
                        _log(f"  [Cubase] Track {self._str_track} Display Value: {parsed_str}")
                    elif self._str_type == 2:
                        _log(f"  [Cubase] DEBUG BUTTON PRESSED! Content: {parsed_str}")
                    self._str_buf = []
                    return
                # COLOR STREAM (CC 120-123)
                elif msg.control == 120: # Color Sync Start
                    self._color_track = msg.value
                    self._color_rgb = [0, 0, 0]
                    return
                elif msg.control == 121: # Red
                    self._color_rgb[0] = msg.value
                    return
                elif msg.control == 122: # Green
                    self._color_rgb[1] = msg.value
                    return
                elif msg.control == 123: # Blue
                    self._color_rgb[2] = msg.value
                    r = self._color_rgb[0] / 127.0
                    g = self._color_rgb[1] / 127.0
                    b = self._color_rgb[2] / 127.0
                    if self._callback:
                        self._callback(0x04, self._color_track, (r, g, b))
                    return
            # We need to reconstruct 14-bit values for faders
            # MSB: CC 1-5, 7-31 (skip CC 6, Data Entry). LSB = MSB + 32.
            # Pan: CC 64-93
            
            # Transport Feedback (Channel 15, Notes 104-107)
            if msg.type in ('note_on', 'note_off') and msg.channel == 14 and 104 <= msg.note <= 107:
                float_val = 1.0 if (msg.type == 'note_on' and msg.velocity > 0) else 0.0
                if msg.note == 104:
                    self._fire_callback(0x08, 0, float_val)  # play
                elif msg.note == 105:
                    if float_val == 1.0: # stopped
                        self._fire_callback(0x08, 0, 0.0) # set play to false
                elif msg.note == 106:
                    self._fire_callback(0x08, 1, float_val)  # rec
                elif msg.note == 107:
                    self._fire_callback(0x08, 2, float_val)  # loop
                return
            
            # Pan (7-bit) – CC 1-60 on Channel 4-5
            if msg.channel in (4, 5) and 1 <= msg.control <= 60:
                track_index = ((msg.channel - 4) * 60) + (msg.control - 1)
                float_val = msg.value / 127.0
                self._fire_callback(0x02, track_index, float_val)
                return
            
            # Solo (7-bit) – CC 1-60 on Channel 6-7
            if msg.channel in (6, 7) and 1 <= msg.control <= 60:
                track_index = ((msg.channel - 6) * 60) + (msg.control - 1)
                float_val = 1.0 if msg.value >= 64 else 0.0
                self._fire_callback(0x05, track_index, float_val)
                return
            
            # Mute (7-bit) – CC 1-60 on Channel 8-9
            if msg.channel in (8, 9) and 1 <= msg.control <= 60:
                track_index = ((msg.channel - 8) * 60) + (msg.control - 1)
                float_val = 1.0 if msg.value >= 64 else 0.0
                self._fire_callback(0x06, track_index, float_val)
                return
            
            # Arm (7-bit) - CC 1-60 on Channel 12-13
            if msg.channel in (12, 13) and 1 <= msg.control <= 60:
                track_index = ((msg.channel - 12) * 60) + (msg.control - 1)
                float_val = 1.0 if msg.value >= 64 else 0.0
                self._fire_callback(0x09, track_index, float_val)
                return
            
            # VU Meter (7-bit) – CC 1-60 on Channel 10-11
            if msg.channel in (10, 11) and 1 <= msg.control <= 60:
                track_index = ((msg.channel - 10) * 60) + (msg.control - 1)
                float_val = msg.value / 127.0
                self._fire_callback(0x07, track_index, float_val)
                return
            
            # Volume MSB – CC 1-5, 7-31 on Channel 0-1 (skip CC 6)
            if msg.channel in (0, 1) and ((1 <= msg.control <= 5) or (7 <= msg.control <= 31)):
                track_offset = _msb_cc_to_track(msg.control)
                track_index = (msg.channel * 30) + track_offset
                self._msb_cache[track_index] = msg.value
                return
            
            # Volume LSB – CC 33-37, 39-63 on Channel 0-1 (skip CC 38)
            if msg.channel in (0, 1) and ((33 <= msg.control <= 37) or (39 <= msg.control <= 63)):
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
        if not (0 <= track_index < 120): return
        
        # Echo suppression: record what we sent and when
        key = (track_index, 0x01)
        self._last_sent[key] = volume
        self._last_sent_time[key] = time.monotonic()
        
        val_14 = int(max(0.0, min(1.0, volume)) * 16383)
        msb = (val_14 >> 7) & 0x7F
        lsb = val_14 & 0x7F
        
        channel = track_index // 30
        cc_msb = _track_to_msb_cc(track_index % 30)
        cc_lsb = cc_msb + 32
        
        self.outport.send(mido.Message('control_change', channel=channel, control=cc_msb, value=msb))
        self.outport.send(mido.Message('control_change', channel=channel, control=cc_lsb, value=lsb))

    def set_pan(self, track_index: int, pan: float):
        if not self.outport: return
        if not (0 <= track_index < 120): return
        
        # Echo suppression: record what we sent and when
        key = (track_index, 0x02)
        self._last_sent[key] = pan
        self._last_sent_time[key] = time.monotonic()
        
        val_7 = int(max(0.0, min(1.0, pan)) * 127)
        channel = 4 + (track_index // 60)
        cc = 1 + (track_index % 60)
        
        self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=val_7))

    def set_solo(self, track_index: int, value: float):
        """Set solo for a track. value >= 0.5 = on, < 0.5 = off."""
        if not self.outport: return
        if not (0 <= track_index < 120): return
        val_7 = 127 if value >= 0.5 else 0
        channel = 6 + (track_index // 60)
        cc = 1 + (track_index % 60)
        self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=val_7))

    def set_mute(self, track_index: int, value: float):
        """Set mute for a track. value >= 0.5 = on, < 0.5 = off."""
        if not self.outport: return
        if not (0 <= track_index < 120): return
        val_7 = 127 if value >= 0.5 else 0
        channel = 8 + (track_index // 60)
        cc = 1 + (track_index % 60)
        self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=val_7))
        
    def set_arm(self, track_index: int, value: float):
        """Set arm for a track. value >= 0.5 = on, < 0.5 = off."""
        if not self.outport: return
        if not (0 <= track_index < 120): return
        val_7 = 127 if value >= 0.5 else 0
        channel = 12 + (track_index // 60)
        cc = 1 + (track_index % 60)
        self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=val_7))
        
    def set_transport(self, cmd_idx: int, value: float):
        """Send transport command. cmd_idx: 0=Play, 1=Rec, 2=Loop"""
        if not self.outport: return
        async def send_click(ch, note):
            self.outport.send(mido.Message('note_on', channel=ch, note=note, velocity=127))
            await asyncio.sleep(0.05)
            self.outport.send(mido.Message('note_off', channel=ch, note=note, velocity=0))

        if cmd_idx == 0:  # Play/Pause
            if value >= 0.5:
                # Play (Note 104)
                asyncio.create_task(send_click(14, 104))
            else:
                # Stop (Note 105)
                asyncio.create_task(send_click(14, 105))
        elif cmd_idx == 1:  # Record
            note = 106
            asyncio.create_task(send_click(14, note))
        elif cmd_idx == 2:  # Loop
            note = 107
            asyncio.create_task(send_click(14, note))

    def defeat_all_solos(self):
        """Send Solo=OFF for all 120 tracks forwards and backwards (to bypass VCA locks)."""
        if not self.outport: return
        for i in range(120):
            channel = 6 + (i // 60)
            cc = 1 + (i % 60)
            self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=0))
        for i in range(119, -1, -1):
            channel = 6 + (i // 60)
            cc = 1 + (i % 60)
            self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=0))

    def defeat_all_mutes(self):
        """Send Mute=OFF for all 120 tracks forwards and backwards (to bypass VCA locks)."""
        if not self.outport: return
        for i in range(120):
            channel = 8 + (i // 60)
            cc = 1 + (i % 60)
            self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=0))
        for i in range(119, -1, -1):
            channel = 8 + (i // 60)
            cc = 1 + (i % 60)
            self.outport.send(mido.Message('control_change', channel=channel, control=cc, value=0))

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
