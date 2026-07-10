import os
import json
import time
import socket
import asyncio
from pythonosc.udp_client import SimpleUDPClient
from kivy.config import Config

# -------------------------------------------------------------------------
# GERÄTEKONFIGURATION laden (vom Deployment-Skript erstellt)
# Enthält: rotation, controller_id
# -------------------------------------------------------------------------
_config_path = os.path.join(os.path.dirname(__file__), 'device_config.json')
_device_config = {}
if os.path.exists(_config_path):
    try:
        with open(_config_path, 'r') as _f:
            _device_config = json.load(_f)
            if 'rotation' in _device_config:
                Config.set('graphics', 'rotation', _device_config['rotation'])
    except Exception as e:
        print(f"Warning: Could not read device config: {e}")

# -------------------------------------------------------------------------
# KIVY-KONFIGURATION (muss VOR allen Kivy-Imports stehen)
# -------------------------------------------------------------------------
Config.set('graphics', 'multisamples', '0')

# RASPBERRY PI ZERO-LATENCY TOUCH HACK
Config.set('postproc', 'retain_time', '0')
Config.set('postproc', 'retain_distance', '0')
Config.set('postproc', 'jitter_distance', '0')
Config.set('postproc', 'jitter_ignore', '1')

# FPS-Monitor aktiv lassen
Config.set('modules', 'monitor', '')

import kivy
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.properties import StringProperty
from widgets.channel_strip import DAWChannelStrip

kivy.require('2.0.0')

# -------------------------------------------------------------------------
# DISCOVERY KONFIGURATION
# -------------------------------------------------------------------------
DISCOVERY_PORT    = 5006   # Broker lauscht hier auf Broadcasts
CONTROLLER_PORT   = 9001   # Controller lauscht hier auf WELCOME vom Broker
BROKER_OSC_PORT   = 8000   # OSC-Port des Brokers
HELLO_INTERVAL    = 5.0    # Sekunden zwischen HELLO-Broadcasts
ONLINE_TIMEOUT    = 15.0   # Sekunden ohne WELCOME → Status zurück auf SEARCHING


# -------------------------------------------------------------------------
# DISCOVERY CLIENT (asyncio DatagramProtocol, läuft neben Kivy)
# -------------------------------------------------------------------------
class _DiscoveryClientProtocol(asyncio.DatagramProtocol):
    """Empfängt DAWDESK_WELCOME Nachrichten vom Broker."""

    def __init__(self, on_welcome):
        self._on_welcome = on_welcome
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            msg = data.decode('utf-8').strip()
        except UnicodeDecodeError:
            return
        if msg.startswith('DAWDESK_WELCOME'):
            self._on_welcome(addr[0])

    def error_received(self, exc):
        print(f"[Discovery] Socket error: {exc}")


async def run_discovery_client(app):
    """
    Sendet alle HELLO_INTERVAL Sekunden einen UDP-Broadcast ins LAN.
    Empfängt WELCOME-Antworten vom Broker und aktualisiert app.connection_status.
    Läuft als asyncio-Task parallel zur Kivy-Main-Loop.
    """
    loop = asyncio.get_running_loop()
    controller_id = app.controller_id
    last_welcome_time = 0.0

    def on_welcome(broker_ip: str):
        nonlocal last_welcome_time
        last_welcome_time = time.monotonic()
        _update_status(app, f"● CONNECTED  {controller_id}")
        # OSC-Client anlegen / aktualisieren (Thread-sicher via mainthread decorator)
        _set_osc_client(app, broker_ip)

    # UDP-Socket für Senden (Broadcast) und Empfangen (WELCOME)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', CONTROLLER_PORT))

    transport, _ = await loop.create_datagram_endpoint(
        lambda: _DiscoveryClientProtocol(on_welcome),
        sock=sock
    )

    hello_msg = f"DAWDESK_HELLO {controller_id} {CONTROLLER_PORT} {app.channels}".encode('utf-8')

    try:
        while True:
            # Broadcast senden
            try:
                transport.sendto(hello_msg, ('255.255.255.255', DISCOVERY_PORT))
            except Exception as e:
                print(f"[Discovery] Broadcast error: {e}")

            # Status prüfen: Wenn kein WELCOME seit ONLINE_TIMEOUT → SEARCHING
            if time.monotonic() - last_welcome_time > ONLINE_TIMEOUT:
                _update_status(app, f"◌ SEARCHING...  {controller_id}")

            await asyncio.sleep(HELLO_INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()


@mainthread
def _update_status(app, status: str):
    """Setzt connection_status im Kivy-Main-Thread (Thread-sicher)."""
    app.connection_status = status


@mainthread
def _set_osc_client(app, broker_ip: str):
    """Erstellt/aktualisiert den OSC-Client im Kivy-Main-Thread."""
    if getattr(app, 'osc_client', None) is None or app._broker_ip != broker_ip:
        app._broker_ip = broker_ip
        app.osc_client = SimpleUDPClient(broker_ip, BROKER_OSC_PORT)
        print(f"[OSC] Client verbunden mit {broker_ip}:{BROKER_OSC_PORT}")


# -------------------------------------------------------------------------
# KIVY APP
# -------------------------------------------------------------------------
class DAWDeskApp(App):
    connection_status = StringProperty("◌ SEARCHING...")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Controller-ID aus device_config.json, Fallback: Hostname
        self.controller_id = _device_config.get(
            'controller_id',
            socket.gethostname()
        )
        self.channels = _device_config.get('channels', 12)
        self.osc_client = None   # Wird gesetzt sobald Broker-IP bekannt
        self._broker_ip = None

    def on_start(self):
        # Anfangsstatus direkt mit der ID setzen
        self.connection_status = f"◌ SEARCHING...  {self.controller_id}"

        # Dynamisches Hinzufügen von Kanalzügen beim Start
        mixer = self.root.ids.mixer_layout
        for i in range(1, self.channels + 1):
            channel = DAWChannelStrip(
                channel_id=i,
                track_name=f"Ch {i}",
                value=-60.0,
                meter_value=-60.0,
                pan=0.0,
                pan_min=-100.0,
                pan_max=100.0
            )
            mixer.add_widget(channel)


# -------------------------------------------------------------------------
# EINSTIEGSPUNKT: asyncio + Kivy gemeinsam starten
# -------------------------------------------------------------------------
async def _async_main():
    app = DAWDeskApp()
    
    # Discovery als Background-Task starten
    discovery_task = asyncio.create_task(run_discovery_client(app))
    
    # Warten, bis die Kivy-App beendet wird (z.B. durch SIGTERM)
    await app.async_run('asyncio')
    
    # Endlosschleife des Discovery-Clients abbrechen, damit der Prozess sauber beenden kann
    discovery_task.cancel()
    try:
        await discovery_task
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    asyncio.run(_async_main())
