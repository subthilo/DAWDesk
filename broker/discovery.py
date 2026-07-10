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

DISCOVERY_PORT = 5006   # UDP-Port auf dem der Broker lauscht
BROKER_OSC_PORT = 8000  # OSC-Port des Brokers (für spätere Nutzung)


def _log(msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)


class DiscoveryProtocol(asyncio.DatagramProtocol):
    """asyncio UDP-Protokoll-Handler für eingehende HELLO-Broadcasts."""

    def __init__(self, registry: ControllerRegistry):
        self.registry = registry
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
        if len(parts) != 3:
            return

        _, controller_id, osc_port_str = parts
        ip = addr[0]

        try:
            osc_port = int(osc_port_str)
        except ValueError:
            _log(f"  Malformed HELLO from {ip}: invalid port '{osc_port_str}'")
            return

        is_new, came_back = self.registry.register(controller_id, ip, osc_port)

        if is_new:
            _log(f"● Controller '{controller_id}' ({ip}:{osc_port}) ONLINE  [new]")
        elif came_back:
            _log(f"● Controller '{controller_id}' ({ip}:{osc_port}) ONLINE  [reconnected]")

        # WELCOME-Antwort direkt an den Controller-IP senden (Unicast)
        welcome_msg = f"DAWDESK_WELCOME {BROKER_OSC_PORT}".encode('utf-8')
        self.transport.sendto(welcome_msg, (ip, osc_port))

    def error_received(self, exc):
        _log(f"  Discovery socket error: {exc}")

    def connection_lost(self, exc):
        _log("  Discovery server stopped.")


async def start_discovery_server(registry: ControllerRegistry):
    """Startet den asynchronen UDP-Discovery-Server."""
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', DISCOVERY_PORT))

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DiscoveryProtocol(registry),
        sock=sock
    )
    return transport, protocol
