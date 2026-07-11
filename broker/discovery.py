"""
Discovery-Server: Lauscht auf UDP-Broadcasts von Controllern.

Protokoll (Controller -> Broker, Broadcast alle 5 Sek.):
  DAWDESK_HELLO <controller_id> <osc_port>

Antwort (Broker -> Controller, Unicast):
  DAWDESK_WELCOME <broker_osc_port>
"""
import asyncio
import socket
from datetime import datetime

from .registry import ControllerRegistry
from .logger import _log

DISCOVERY_PORT = 5006   # UDP-Port auf dem der Broker lauscht
BROKER_OSC_PORT = 8000  # OSC-Port des Brokers (für spätere Nutzung)

class DiscoveryProtocol(asyncio.DatagramProtocol):
    """asyncio UDP-Protokoll-Handler für eingehende HELLO-Broadcasts."""

    def __init__(self, registry: ControllerRegistry, on_connect_callback=None):
        self.registry = registry
        self.on_connect_callback = on_connect_callback
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        sock = transport.get_extra_info('socket')
        _log(f"Discovery server listening on UDP port {DISCOVERY_PORT}")

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            message = data.decode('utf-8').strip()
        except UnicodeDecodeError:
            return

        if not message.startswith('DAWDESK_HELLO'):
            return

        parts = message.split()
        if len(parts) < 3:
            return

        controller_id = parts[1]
        osc_port_str = parts[2]
        
        # Falls ältere Controller senden, Fallback auf 12
        channels_str = parts[3] if len(parts) >= 4 else "12"
        
        ip = addr[0]

        try:
            osc_port = int(osc_port_str)
            channels = int(channels_str)
        except ValueError:
            _log(f"  Malformed HELLO from {ip}: invalid port or channel count")
            return

        is_new, came_back = self.registry.register(controller_id, ip, osc_port, channels)

        if is_new:
            _log(f"● Controller '{controller_id}' ({ip}:{osc_port}) ONLINE  [new]")
        elif came_back:
            _log(f"● Controller '{controller_id}' ({ip}:{osc_port}) ONLINE  [reconnected]")
            
        # Robustness: Always trigger sync on HELLO. If the controller just booted, 
        # its UI might not have been ready for the first packet. 
        # Sending state every 5s is a great self-healing mechanism.
        if self.on_connect_callback:
            self.on_connect_callback(controller_id)

        # WELCOME-Antwort direkt an den Controller-IP senden (Unicast)
        welcome_msg = f"DAWDESK_WELCOME {BROKER_OSC_PORT}".encode('utf-8')
        self.transport.sendto(welcome_msg, (ip, osc_port))

    def error_received(self, exc):
        _log(f"  Discovery socket error: {exc}")

    def connection_lost(self, exc):
        _log("  Discovery server stopped.")


async def start_discovery_server(registry: ControllerRegistry, on_connect_callback=None):
    """Startet den asynchronen UDP-Discovery-Server."""
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', DISCOVERY_PORT))

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DiscoveryProtocol(registry, on_connect_callback),
        sock=sock
    )
    return transport, protocol
