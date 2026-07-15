"""
DAWDesk Broker — Einstiegspunkt (GUI Version).
Läuft auf dem Host-Computer (Mac/Linux).

Starten:
    python -m broker
"""
import os
import asyncio
from datetime import datetime

import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock, mainthread
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout

kivy.require('2.0.0')

try:
    from broker.registry import ControllerRegistry
    from broker.discovery import start_discovery_server
    from broker.osc_server import start_osc_server
    from broker.config import BrokerConfig
    from broker.logger import _log, logger
    from broker.state import BrokerState
    from broker.cubase_adapter import CubaseAdapter
except ImportError:
    from registry import ControllerRegistry
    from discovery import start_discovery_server
    from osc_server import start_osc_server
    from config import BrokerConfig
    from logger import _log, logger
    from state import BrokerState
    from cubase_adapter import CubaseAdapter

WATCHDOG_INTERVAL = 5.0  # Sekunden zwischen Timeout-Checks


class BrokerApp(App):
    log_text = kivy.properties.StringProperty("")

    def __init__(self, registry: ControllerRegistry, **kwargs):
        super().__init__(**kwargs)
        self.registry = registry
        self.broker_config = BrokerConfig()
        
        # Register logger callback
        logger.callbacks.append(self.append_log)
        
    def build(self):
        self.title = "DAWDesk Broker"
        kv_path = os.path.join(os.path.dirname(__file__), 'broker_ui.kv')
        Builder.load_file(kv_path)
        
        self.root = Factory.BrokerRoot()
        
        # Start UI update loop
        Clock.schedule_interval(self.update_ui, 1.0)
        return self.root

    @mainthread
    def append_log(self, line: str):
        self.log_text += line + "\n"
        if len(self.log_text) > 5000:
            self.log_text = self.log_text[-5000:]

    @mainthread
    def update_ui(self, dt):
        """Updates the controller list in the GUI."""
        # 1. Update order based on registry discovery
        current_order = self.broker_config.get_order()
        all_controllers = self.registry.get_all()
        
        changed = False
        for cid in all_controllers.keys():
            if cid not in current_order:
                current_order.append(cid)
                changed = True
        
        if changed:
            self.broker_config.set_order(current_order)
            
        # 2. Rebuild list
        controller_list = self.root.ids.controller_list
        controller_list.clear_widgets()
        
        for cid in current_order:
            if cid in all_controllers:
                ctrl = all_controllers[cid]
                row = Factory.ControllerRow()
                row.controller_id = ctrl.controller_id
                row.ip = ctrl.ip
                row.osc_port = ctrl.osc_port
                row.channels = ctrl.channels
                row.status = ctrl.status
                controller_list.add_widget(row)

    def move_controller_up(self, controller_id: str):
        order = self.broker_config.get_order()
        try:
            idx = order.index(controller_id)
            if idx > 0:
                order[idx], order[idx-1] = order[idx-1], order[idx]
                self.broker_config.set_order(order)
                self.update_ui(0)
                if hasattr(self, 'state') and self.state.on_routing_changed:
                    self.state.on_routing_changed()
        except ValueError:
            pass

    def move_controller_down(self, controller_id: str):
        order = self.broker_config.get_order()
        try:
            idx = order.index(controller_id)
            if idx < len(order) - 1:
                order[idx], order[idx+1] = order[idx+1], order[idx]
                self.broker_config.set_order(order)
                self.update_ui(0)
                if hasattr(self, 'state') and self.state.on_routing_changed:
                    self.state.on_routing_changed()
        except ValueError:
            pass


async def registry_watchdog(registry: ControllerRegistry):
    """Prüft alle WATCHDOG_INTERVAL Sekunden auf timed-out Controller."""
    while True:
        await asyncio.sleep(WATCHDOG_INTERVAL)
        newly_offline = registry.check_timeouts()
        for controller_id in newly_offline:
            _log(f"✕ Controller '{controller_id}' OFFLINE (timeout)")


async def run():
    # 1. Initialize core components
    registry = ControllerRegistry()
    broker_config = BrokerConfig()
    
    # 2. Initialize State and DAW Adapter
    state = BrokerState(broker_config, registry)
    cubase_adapter = CubaseAdapter(port_name="DAWDesk")
    
    # Cache for UDP clients to avoid instantiating sockets continuously
    udp_clients = {}

    def send_to_rpi(controller_id: str, channel_id: int, cmd: int, float_val: float):
        ctrl = registry.get_all().get(controller_id)
        if not ctrl: return
        from pythonosc.udp_client import SimpleUDPClient
        target_port = 8001
        
        # Use cached client if available
        if controller_id not in udp_clients or udp_clients[controller_id]._address != (ctrl.ip, target_port):
            udp_clients[controller_id] = SimpleUDPClient(ctrl.ip, target_port)
            
        client = udp_clients[controller_id]
        
        if cmd == 0x01:
            client.send_message(f"/ui/fader/{channel_id}/volume", float_val)
        elif cmd == 0x02:
            client.send_message(f"/ui/fader/{channel_id}/pan", float_val)
        elif cmd == 0x05:
            client.send_message(f"/ui/fader/{channel_id}/solo", float_val)
        elif cmd == 0x06:
            client.send_message(f"/ui/fader/{channel_id}/mute", float_val)
        elif cmd == 0x07:
            client.send_message(f"/ui/fader/{channel_id}/meter", float_val)

    def send_to_rpi_string(controller_id: str, channel_id: int, cmd: int, str_val: str):
        ctrl = registry.get_all().get(controller_id)
        if not ctrl: return
        from pythonosc.udp_client import SimpleUDPClient
        target_port = 8001
        
        if controller_id not in udp_clients or udp_clients[controller_id]._address != (ctrl.ip, target_port):
            udp_clients[controller_id] = SimpleUDPClient(ctrl.ip, target_port)
            
        client = udp_clients[controller_id]
        if cmd == 0x03:
            client.send_message(f"/ui/fader/{channel_id}/name", str_val)

    def send_to_rpi_color(controller_id: str, channel_id: int, cmd: int, color_val: tuple):
        ctrl = registry.get_all().get(controller_id)
        if not ctrl: return
        from pythonosc.udp_client import SimpleUDPClient
        target_port = 8001
        
        if controller_id not in udp_clients or udp_clients[controller_id]._address != (ctrl.ip, target_port):
            udp_clients[controller_id] = SimpleUDPClient(ctrl.ip, target_port)
            
        client = udp_clients[controller_id]
        if cmd == 0x04:
            client.send_message(f"/ui/fader/{channel_id}/color", color_val)

    def send_to_rpi_transport(controller_id: str, local_ch: int, cmd: int, float_val: float):
        ctrl = registry.get_all().get(controller_id)
        if not ctrl: return
        from pythonosc.udp_client import SimpleUDPClient
        target_port = 8001
        
        if controller_id not in udp_clients or udp_clients[controller_id]._address != (ctrl.ip, target_port):
            udp_clients[controller_id] = SimpleUDPClient(ctrl.ip, target_port)
            
        client = udp_clients[controller_id]
        t_names = ['play', 'rec', 'loop']
        if cmd == 0x08 and 0 <= local_ch < 3:
            client.send_message(f"/ui/{controller_id}/transport/{t_names[local_ch]}", float_val)

    # Meter buffer: {daw_track_index: float} – written by MIDI thread, flushed by Clock
    _meter_buffer = {}

    def _flush_meter_buffer(dt):
        """Flush buffered meter values to connected RPis at 15fps."""
        nonlocal _meter_buffer
        if not _meter_buffer:
            return
        # Atomic swap: take ownership of current buffer, replace with empty one
        snapshot, _meter_buffer = _meter_buffer, {}
        for track_index, val in snapshot.items():
            controller_id, channel_id = state.get_controller_and_local_channel(track_index)
            if controller_id:
                send_to_rpi(controller_id, channel_id, 0x07, val)

    Clock.schedule_interval(_flush_meter_buffer, 1.0 / 15.0)

    # --- DELTA CACHE & OSC QUEUE FOR THROTTLING ---
    _sent_state_cache = {}  # { (cid, local_ch, cmd): value }
    _osc_queue = []
    
    def _flush_osc_queue(dt):
        """Flushes the OSC queue progressively to avoid UDP flood drops over Wi-Fi."""
        nonlocal _osc_queue
        if not _osc_queue:
            return
        # Send up to 20 messages per frame (~1200 msg/sec at 60fps)
        batch = _osc_queue[:20]
        _osc_queue = _osc_queue[20:]
        for send_func, cid, local_ch, cmd, val in batch:
            send_func(cid, local_ch, cmd, val)
            
    Clock.schedule_interval(_flush_osc_queue, 1.0 / 60.0)
    
    def _send_if_changed(cid, local_ch, cmd, val, send_func):
        key = (cid, local_ch, cmd)
        if _sent_state_cache.get(key) != val:
            _sent_state_cache[key] = val
            _osc_queue.append((send_func, cid, local_ch, cmd, val))

    _received_cubase_events = False

    def on_cubase_event(cmd: int, track: int, val):
        nonlocal _received_cubase_events
        _received_cubase_events = True
        
        if cmd == 0x08:
            state.transport_state[track] = float(val)
            for cid in state.registry.get_all().keys():
                _send_if_changed(cid, track, cmd, float(val), send_to_rpi_transport)
            return

        # 1. Cache the value (skip meter – ephemeral, high-frequency)
        if cmd == 0x03:
            state.update_track_name(track, val)
        elif cmd == 0x04:
            state.update_track_color(track, val)
        elif cmd == 0x07:
            # Buffer meter – will be flushed at 15fps
            _meter_buffer[track] = float(val)
            return
        else:
            state.update_track_value(track, cmd, float(val))
        
        # 2. Forward to RPi if it's currently mapped (immediate for non-meter)
        controller_id, channel_id = state.get_controller_and_local_channel(track)
        if not controller_id:
            return
            
        if cmd == 0x03:
            _send_if_changed(controller_id, channel_id, cmd, val, send_to_rpi_string)
        elif cmd == 0x04:
            _send_if_changed(controller_id, channel_id, cmd, val, send_to_rpi_color)
        else:
            _send_if_changed(controller_id, channel_id, cmd, float(val), send_to_rpi)
        
    _push_task = None
    
    def on_routing_changed():
        """Called when the broker's bank offset changes (nudging). Pushes cached values to RPis."""
        nonlocal _push_task
        if _push_task and not _push_task.done():
            _push_task.cancel()
            
        async def _push():
            try:
                # Push global transport state
                for cmd_idx, val in state.transport_state.items():
                    for cid in state.registry.get_all().keys():
                        _send_if_changed(cid, cmd_idx, 0x08, val, send_to_rpi_transport)

                order = broker_config.get_order()
                all_controllers = registry.get_all()
                for cid in order:
                    if cid in all_controllers:
                        channels = all_controllers[cid].channels
                        for local_ch in range(1, channels + 1):
                            daw_index = state.get_daw_track_index(cid, local_ch)
                            if daw_index >= 0:
                                vol = state.get_track_value(daw_index, 0x01)
                                pan = state.get_track_value(daw_index, 0x02)
                                solo = state.get_track_value(daw_index, 0x05)
                                mute = state.get_track_value(daw_index, 0x06)
                                name = state.get_track_name(daw_index)
                                color = state.get_track_color(daw_index)
                                
                                _send_if_changed(cid, local_ch, 0x01, vol, send_to_rpi)
                                _send_if_changed(cid, local_ch, 0x02, pan, send_to_rpi)
                                _send_if_changed(cid, local_ch, 0x05, solo, send_to_rpi)
                                _send_if_changed(cid, local_ch, 0x06, mute, send_to_rpi)
                                _send_if_changed(cid, local_ch, 0x03, name, send_to_rpi_string)
                                _send_if_changed(cid, local_ch, 0x04, color, send_to_rpi_color)
            except asyncio.CancelledError:
                pass
                
        _push_task = asyncio.create_task(_push())

    state.on_routing_changed = on_routing_changed
    cubase_adapter.set_callback(on_cubase_event)

    # 3. Kivy App
    app = BrokerApp(registry)
    app.state = state

    # 4. Background tasks
    watchdog_task = asyncio.create_task(registry_watchdog(registry))
    
    _sync_in_progress = False

    async def request_cubase_state():
        """Force Cubase to dump its state by shifting banks back and forth."""
        nonlocal _sync_in_progress
        if _sync_in_progress: return
        _sync_in_progress = True
        try:
            _log("Requesting full state sync from Cubase...")
            # 1. Force bank to the far left (0-59) just in case
            for _ in range(2):
                cubase_adapter.send_nudge(-1)
                await asyncio.sleep(0.1)
            
            # 2. Nudge right (60-119). Cubase will dump state for 60-119.
            cubase_adapter.send_nudge(1)
            await asyncio.sleep(0.8)  # Wait for Cubase to process and send
            
            # 3. Nudge left (0-59). Cubase will dump state for 0-59.
            cubase_adapter.send_nudge(-1)
            await asyncio.sleep(0.8)
            _log("Cubase state sync complete.")
            
            # 4. Push newly cached state to all connected tablets
            on_routing_changed()
        finally:
            _sync_in_progress = False

    def on_controller_connected(controller_id: str):
        """Sends full cached state to a (re)connected controller. Also called on every HELLO for self-healing."""
        ctrl = registry.get_all().get(controller_id)
        if not ctrl: return
        channels = ctrl.channels
        for local_ch in range(1, channels + 1):
            daw_index = state.get_daw_track_index(controller_id, local_ch)
            if daw_index >= 0:
                vol = state.get_track_value(daw_index, 0x01)
                pan = state.get_track_value(daw_index, 0x02)
                solo = state.get_track_value(daw_index, 0x05)
                mute = state.get_track_value(daw_index, 0x06)
                name = state.get_track_name(daw_index)
                color = state.get_track_color(daw_index)
                send_to_rpi(controller_id, local_ch, 0x01, vol)
                send_to_rpi(controller_id, local_ch, 0x02, pan)
                send_to_rpi(controller_id, local_ch, 0x05, solo)
                send_to_rpi(controller_id, local_ch, 0x06, mute)
                send_to_rpi_string(controller_id, local_ch, 0x03, name)
                send_to_rpi_color(controller_id, local_ch, 0x04, color)
                
        # Push global transport state
        for cmd_idx, val in state.transport_state.items():
            send_to_rpi_transport(controller_id, cmd_idx, 0x08, val)
                
        # If cache is completely empty, it means Cubase hasn't sent us anything yet.
        # Force a sync so the tablet gets the actual Cubase state instead of zeros.
        if not _received_cubase_events:
            asyncio.create_task(request_cubase_state())
        
    discovery_transport, discovery_protocol = await start_discovery_server(registry, on_connect_callback=on_controller_connected)
    osc_transport, osc_protocol = await start_osc_server(state, cubase_adapter)
    
    # 5. Request Cubase state after MIDI port is ready.
    # We delay this to give Cubase time to detect the virtual MIDI port.
    async def initial_request():
        await asyncio.sleep(5.0)
        if not _received_cubase_events:
            await request_cubase_state()
    
    asyncio.create_task(initial_request())

    try:
        await asyncio.gather(
            app.async_run('asyncio'),
            watchdog_task
        )
    except asyncio.CancelledError:
        pass
    finally:
        discovery_transport.close()
        osc_transport.close()
        _log("Broker shut down.")


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nBroker stopped by user.")


if __name__ == '__main__':
    main()
