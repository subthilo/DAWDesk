"""
OSC-Server: Empfängt Fader-, Pan-, Solo-, Mute- und Nudge-Werte von Controllern.

Interne OSC-Pfade:
  /ui/{controller}/fader/{ch}/volume       Float 0.0 – 1.0
  /ui/{controller}/fader/{ch}/pan          Float 0.0 – 1.0  (0.5 = Mitte)
  /ui/{controller}/fader/{ch}/solo         Float (trigger toggle)
  /ui/{controller}/fader/{ch}/mute         Float (trigger toggle)
  /ui/{controller}/global/solo_defeat      Float (alle Solos aus)
  /ui/{controller}/global/mute_defeat      Float (alle Mutes aus)
  /ui/{controller}/nudge                   Int -1 oder 1
"""
import asyncio

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import AsyncIOOSCUDPServer
from .logger import _log
from .state import BrokerState
from .cubase_adapter import CubaseAdapter

OSC_PORT = 8000


def _handle_fallback(address: str, *args):
    _log(f"  ↓ [unbekannt] {address}  {args}")

def create_dispatcher(state: BrokerState, daw_adapter: CubaseAdapter) -> Dispatcher:
    dispatcher = Dispatcher()

    def handle_volume(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) == 5:
            controller_id = parts[1]
            try:
                channel_id = int(parts[3])
                value = args[0] if args else None
                if value is not None:
                    _log(f"  ↓ [{controller_id}] ch{channel_id}/volume  {value:.3f}")
                    daw_index = state.get_daw_track_index(controller_id, channel_id)
                    if daw_index >= 0:
                        state.update_track_value(daw_index, 0x01, value)
                        daw_adapter.set_volume(daw_index, value)
            except ValueError:
                pass

    def handle_pan(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) == 5:
            controller_id = parts[1]
            try:
                channel_id = int(parts[3])
                value = args[0] if args else None
                if value is not None:
                    _log(f"  ↓ [{controller_id}] ch{channel_id}/pan      {value:.3f}")
                    daw_index = state.get_daw_track_index(controller_id, channel_id)
                    if daw_index >= 0:
                        state.update_track_value(daw_index, 0x02, value)
                        daw_adapter.set_pan(daw_index, value)
            except ValueError:
                pass

    def handle_nudge(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) == 3:
            controller_id = parts[1]
            try:
                steps = int(args[0]) if args else None
                if steps is not None and steps != 0:
                    _log(f"  ↓ [{controller_id}] nudge  {steps}")
                    
                    if not hasattr(state, 'cubase_bank_index'):
                        state.cubase_bank_index = 0
                        
                    all_controllers = state.registry.get_all()
                    displayable_channels = sum(c.channels for c in all_controllers.values())
                    if displayable_channels == 0:
                        displayable_channels = 12 # Fallback

                    # Filter real_tracks to only include those in the current 60-track bank
                    current_bank_start = state.cubase_bank_index * 60
                    current_bank_end = current_bank_start + 60
                    
                    real_tracks = [
                        t_idx for t_idx in state.track_values.keys() 
                        if current_bank_start <= t_idx < current_bank_end 
                        and state.get_track_name(t_idx).strip() != ''
                    ]
                    
                    if not real_tracks:
                        # Broker just restarted or bank just shifted and Cubase hasn't sent track names yet.
                        # Assume a full bank so nudging is not completely locked.
                        current_bank_real_tracks = 60
                    else:
                        # Convert absolute max index back to a relative count (1 to 60)
                        current_bank_real_tracks = max(real_tracks) - current_bank_start + 1

                    max_offset = max(0, current_bank_real_tracks - displayable_channels)
                    new_offset = state.bank_offset + steps

                    if new_offset < 0:
                        if state.cubase_bank_index > 0:
                            daw_adapter.send_nudge(-1)
                            state.cubase_bank_index -= 1
                            state.bank_offset = 60 - displayable_channels
                            if state.bank_offset < 0: state.bank_offset = 0
                        else:
                            state.bank_offset = 0 # Hard clamp at the absolute start
                    elif new_offset > max_offset:
                        # If the bank is completely full, we assume there might be more tracks in the next Cubase bank
                        if current_bank_real_tracks >= 60:
                            daw_adapter.send_nudge(1)
                            state.cubase_bank_index += 1
                            state.bank_offset = 0
                        else:
                            state.bank_offset = max_offset # Hard clamp at the absolute end
                    else:
                        state.bank_offset = new_offset
                        
                    _log(f"  → Routing offset is now {state.bank_offset} (Bank: {state.cubase_bank_index})")
                    if hasattr(state, 'on_routing_changed') and state.on_routing_changed:
                        state.on_routing_changed()
            except Exception as e:
                _log(f"  [ERROR] Nudge processing failed: {e}")
                pass

    def handle_solo(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) == 5:
            controller_id = parts[1]
            try:
                channel_id = int(parts[3])
                value = args[0] if args else None
                if value is not None:
                    daw_index = state.get_daw_track_index(controller_id, channel_id)
                    if daw_index >= 0:
                        # Toggle: check current state and send opposite
                        current = state.get_track_value(daw_index, 0x05)
                        new_val = 0.0 if current >= 0.5 else 1.0
                        _log(f"  ↓ [{controller_id}] ch{channel_id}/solo     {int(current)}→{int(new_val)}")
                        daw_adapter.set_solo(daw_index, new_val)
            except ValueError:
                pass

    def handle_mute(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) == 5:
            controller_id = parts[1]
            try:
                channel_id = int(parts[3])
                value = args[0] if args else None
                if value is not None:
                    daw_index = state.get_daw_track_index(controller_id, channel_id)
                    if daw_index >= 0:
                        # Toggle: check current state and send opposite
                        current = state.get_track_value(daw_index, 0x06)
                        new_val = 0.0 if current >= 0.5 else 1.0
                        _log(f"  ↓ [{controller_id}] ch{channel_id}/mute     {int(current)}→{int(new_val)}")
                        daw_adapter.set_mute(daw_index, new_val)
            except ValueError:
                pass

    def handle_solo_defeat(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) >= 3:
            controller_id = parts[1]
            _log(f"  ↓ [{controller_id}] global/solo_defeat")
            daw_adapter.defeat_all_solos()

    def handle_mute_defeat(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) >= 3:
            controller_id = parts[1]
            _log(f"  ↓ [{controller_id}] global/mute_defeat")
            daw_adapter.defeat_all_mutes()

    def handle_transport(address: str, *args):
        parts = address.strip('/').split('/')
        # /ui/{controller}/transport/{cmd}
        if len(parts) == 4 and parts[2] == 'transport':
            controller_id = parts[1]
            cmd = parts[3]
            value = args[0] if args else None
            if value is not None:
                _log(f"  ↓ [{controller_id}] transport/{cmd}  {value:.3f}")
                cmd_idx = 0 if cmd == 'play' else 1 if cmd == 'rec' else 2
                daw_adapter.set_transport(cmd_idx, value)

    dispatcher.map('/ui/*/fader/*/volume', handle_volume)
    dispatcher.map('/ui/*/fader/*/pan',    handle_pan)
    dispatcher.map('/ui/*/fader/*/solo',   handle_solo)
    dispatcher.map('/ui/*/fader/*/mute',   handle_mute)
    dispatcher.map('/ui/*/global/solo_defeat', handle_solo_defeat)
    dispatcher.map('/ui/*/global/mute_defeat', handle_mute_defeat)
    dispatcher.map("/ui/*/nudge", handle_nudge)
    dispatcher.map("/ui/*/transport/*", handle_transport)
    dispatcher.set_default_handler(_handle_fallback)
    
    return dispatcher

async def start_osc_server(state: BrokerState, daw_adapter: CubaseAdapter):
    """Startet den asyncio OSC-UDP-Server auf port OSC_PORT."""
    dispatcher = create_dispatcher(state, daw_adapter)

    server = AsyncIOOSCUDPServer(
        ('0.0.0.0', OSC_PORT),
        dispatcher,
        asyncio.get_running_loop()
    )
    transport, protocol = await server.create_serve_endpoint()
    _log(f"OSC server listening on UDP port {OSC_PORT}")
    return transport, protocol
