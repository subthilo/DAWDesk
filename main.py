import os
import json
import time
import socket
import asyncio
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading
from kivy.config import Config
from kivy.lang import Builder

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
        self.channel_strips = []
        self._meter_buffer = {}  # {channel_id: float} – written by OSC thread, read by Clock
        # Flush meter buffer at 15fps (good balance between smooth display and CPU)
        Clock.schedule_interval(self._flush_meters, 1.0 / 15.0)

    def on_start(self):
        # Anfangsstatus direkt mit der ID setzen
        self.connection_status = f"◌ SEARCHING...  {self.controller_id}"

        # Dynamisches Hinzufügen von Kanalzügen beim Start
        layout = self.root.ids.mixer_layout
        for i in range(self.channels):
            channel_id = i + 1
            strip = DAWChannelStrip(
                channel_id=channel_id,
                track_name=f"Ch {channel_id}",
                value=-60.0,
                meter_value=-60.0,
                pan=0.0,
                pan_min=-100.0,
                pan_max=100.0
            )
            self.channel_strips.append(strip)
            layout.add_widget(strip)

    from kivy.clock import mainthread
    @mainthread
    def update_fader_from_osc(self, channel_id: int, value: float):
        if 1 <= channel_id <= len(self.channel_strips):
            strip = self.channel_strips[channel_id - 1]
            if strip.is_touched:
                return  # Prevent MIDI feedback jitter
            # Convert 0.0..1.0 back to dB (-60..+6)
            db_val = value * (strip.db_max - strip.db_min) + strip.db_min
            # Suppress near-identical updates (dedup)
            if abs(strip.value - db_val) < 0.05:
                return
            strip._ignore_osc_send = True
            strip.value = db_val
            strip._ignore_osc_send = False

    @mainthread
    def update_pan_from_osc(self, channel_id: int, value: float):
        if 1 <= channel_id <= len(self.channel_strips):
            strip = self.channel_strips[channel_id - 1]
            if strip.is_touched:
                return  # Prevent MIDI feedback jitter
                
            if value < -0.5:
                pan_val = -999.0
            else:
                # Convert 0.0..1.0 back to pan (-1.0..1.0)
                pan_val = (value * 2.0) - 1.0
                
            # Suppress near-identical updates (dedup)
            if abs(strip.pan - pan_val) < 0.01:
                return
            strip._ignore_osc_send = True
            strip.pan = pan_val
            strip._ignore_osc_send = False

    @mainthread
    def update_name_from_osc(self, channel_id: int, name: str):
        if 1 <= channel_id <= len(self.channel_strips):
            strip = self.channel_strips[channel_id - 1]
            strip.track_name = name or f"Ch {channel_id}"

    @mainthread
    def update_color_from_osc(self, channel_id: int, r: float, g: float, b: float):
        if 1 <= channel_id <= len(self.channel_strips):
            strip = self.channel_strips[channel_id - 1]
            strip.track_color = (r, g, b, 1.0)

    @mainthread
    def update_solo_from_osc(self, channel_id: int, value: float):
        if 1 <= channel_id <= len(self.channel_strips):
            strip = self.channel_strips[channel_id - 1]
            strip.is_solo = (value >= 0.5)

    @mainthread
    def update_mute_from_osc(self, channel_id: int, value: float):
        if 1 <= channel_id <= len(self.channel_strips):
            strip = self.channel_strips[channel_id - 1]
            strip.is_muted = (value >= 0.5)

    def update_meter_from_osc(self, channel_id: int, value: float):
        """Called from OSC thread – just buffer the value, no mainthread needed."""
        self._meter_buffer[channel_id] = value

    def _flush_meters(self, dt):
        """Called at 15fps by Clock. Applies all buffered meter values at once and decays others."""
        snapshot, self._meter_buffer = self._meter_buffer, {}
        for i, strip in enumerate(self.channel_strips):
            ch_id = i + 1
            if ch_id in snapshot:
                value = snapshot[ch_id]
                if value <= 0.001:
                    strip.meter_value = strip.db_min
                else:
                    strip.meter_value = strip.db_min + value * (strip.db_max - strip.db_min)
            else:
                # Decay meter if no new value was received (e.g., empty channel after nudging)
                if strip.meter_value > strip.db_min:
                    strip.meter_value -= 8.0  # Fast decay
                    if strip.meter_value < strip.db_min:
                        strip.meter_value = strip.db_min

    def set_bank_offset(self, offset: float):
        if hasattr(self, 'osc_client') and self.osc_client:
            try:
                self.osc_client.send_message(f"/broker/set_offset", int(offset))
            except Exception as e:
                print(f"Error sending set_offset: {e}")


# -------------------------------------------------------------------------
# EINSTIEGSPUNKT: asyncio + Kivy gemeinsam starten
# -------------------------------------------------------------------------
async def run_app():
    app = DAWDeskApp()
    
    # Start Discovery Loop (Background)
    discovery_task = asyncio.create_task(run_discovery_client(app))
    
    # Start OSC Server to receive feedback from Broker
    def handle_volume(address, *args):
        try:
            ch = int(address.split('/')[3])
            val = float(args[0])
            app.update_fader_from_osc(ch, val)
        except Exception:
            pass

    def handle_pan(address, *args):
        try:
            ch = int(address.split('/')[3])
            val = float(args[0])
            app.update_pan_from_osc(ch, val)
        except Exception:
            pass

    def handle_name(address, *args):
        try:
            ch = int(address.split('/')[3])
            name = str(args[0])
            app.update_name_from_osc(ch, name)
        except Exception:
            pass

    def handle_color(address, *args):
        try:
            ch = int(address.split('/')[3])
            r, g, b = float(args[0]), float(args[1]), float(args[2])
            app.update_color_from_osc(ch, r, g, b)
        except Exception:
            pass

    def handle_solo(address, *args):
        try:
            ch = int(address.split('/')[3])
            val = float(args[0])
            app.update_solo_from_osc(ch, val)
        except Exception:
            pass

    def handle_mute(address, *args):
        try:
            ch = int(address.split('/')[3])
            val = float(args[0])
            app.update_mute_from_osc(ch, val)
        except Exception:
            pass

    def handle_meter(address, *args):
        try:
            ch = int(address.split('/')[3])
            val = float(args[0])
            app.update_meter_from_osc(ch, val)
        except Exception:
            pass

    def handle_transport(address, *args):
        try:
            parts = address.split('/')
            if len(parts) >= 5:
                cmd = parts[4]
                val = float(args[0])
                app.update_transport_from_osc(cmd, val)
        except Exception as e:
            print(f"Error handling transport OSC: {e}")

    @mainthread
    def update_transport_from_osc(self, cmd: str, val: float):
        action_row = self.root.ids.get('action_row')
        if action_row:
            action_row.update_transport_state(cmd, val)

    dispatcher = Dispatcher()
    dispatcher.map('/ui/fader/*/volume', handle_volume)
    dispatcher.map('/ui/fader/*/pan', handle_pan)
    dispatcher.map('/ui/fader/*/name', handle_name)
    dispatcher.map('/ui/fader/*/color', handle_color)
    dispatcher.map('/ui/fader/*/solo', handle_solo)
    dispatcher.map('/ui/fader/*/mute', handle_mute)
    dispatcher.map('/ui/fader/*/meter', handle_meter)
    dispatcher.map('/ui/*/transport/*', handle_transport)
    
    # Run OSC Server in a dedicated background thread to bypass Kivy's touch event loop blocks
    server = ThreadingOSCUDPServer(('0.0.0.0', 8001), dispatcher)
    osc_thread = threading.Thread(target=server.serve_forever, daemon=True)
    osc_thread.start()

    try:
        await app.async_run('asyncio')
    except asyncio.CancelledError:
        pass
    finally:
        discovery_task.cancel()
        server.shutdown()
        print("Application closed.")


if __name__ == '__main__':
    asyncio.run(run_app())
