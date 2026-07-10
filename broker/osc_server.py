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

OSC_PORT = 8000


def _handle_volume(address: str, *args):
    """Empfängt /ui/{controller_id}/fader/{ch}/volume Float"""
    # Format: ui / {controller_id} / fader / {channel_id} / volume
    parts = address.strip('/').split('/')
    if len(parts) == 5:
        controller_id = parts[1]
        channel_id    = parts[3]
        value = args[0] if args else None
        _log(f"  ↓ [{controller_id}] ch{channel_id}/volume  {value:.3f}")


def _handle_pan(address: str, *args):
    """Empfängt /ui/{controller_id}/fader/{ch}/pan Float"""
    parts = address.strip('/').split('/')
    if len(parts) == 5:
        controller_id = parts[1]
        channel_id    = parts[3]
        value = args[0] if args else None
        _log(f"  ↓ [{controller_id}] ch{channel_id}/pan      {value:.3f}")


def _handle_fallback(address: str, *args):
    _log(f"  ↓ [unbekannt] {address}  {args}")


async def start_osc_server():
    """Startet den asyncio OSC-UDP-Server auf port OSC_PORT."""
    dispatcher = Dispatcher()
    dispatcher.map('/ui/*/fader/*/volume', _handle_volume)
    dispatcher.map('/ui/*/fader/*/pan',    _handle_pan)
    dispatcher.set_default_handler(_handle_fallback)

    server = AsyncIOOSCUDPServer(
        ('0.0.0.0', OSC_PORT),
        dispatcher,
        asyncio.get_running_loop()
    )
    transport, protocol = await server.create_serve_endpoint()
    _log(f"OSC server listening on UDP port {OSC_PORT}")
    return transport, protocol
