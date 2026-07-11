"""
OSC-Server: Empfängt Fader- und Pan-Werte von Controllern.

Interne OSC-Pfade (Spec §3.1):
  /ui/fader/{channel_id}/volume   Float 0.0 – 1.0
  /ui/fader/{channel_id}/pan      Float 0.0 – 1.0  (0.5 = Mitte)
"""
import asyncio
from datetime import datetime

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
                direction = int(args[0]) if args else None
                if direction is not None:
                    _log(f"  ↓ [{controller_id}] nudge  {direction}")
                    state.bank_offset += direction
                    if state.bank_offset < 0:
                        state.bank_offset = 0
                    
                    _log(f"  → Routing offset is now {state.bank_offset}")
                    if hasattr(state, 'on_routing_changed') and state.on_routing_changed:
                        state.on_routing_changed()
            except ValueError:
                pass

    dispatcher.map('/ui/*/fader/*/volume', handle_volume)
    dispatcher.map('/ui/*/fader/*/pan',    handle_pan)
    dispatcher.map("/ui/*/nudge", handle_nudge)
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
