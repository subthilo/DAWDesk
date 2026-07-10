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

from .registry import ControllerRegistry
from .discovery import start_discovery_server
from .osc_server import start_osc_server
from .config import BrokerConfig
from .logger import _log, logger

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
    """Hauptkoroutine: startet alle Broker-Tasks und die Kivy GUI."""
    registry = ControllerRegistry()

    _log("=" * 50)
    _log("  DAWDesk Broker  v1 (GUI)")
    _log("=" * 50)

    transport_disc, _ = await start_discovery_server(registry)
    transport_osc, _  = await start_osc_server()

    app = BrokerApp(registry)

    try:
        await asyncio.gather(
            app.async_run('asyncio'),
            registry_watchdog(registry)
        )
    except asyncio.CancelledError:
        pass
    finally:
        transport_disc.close()
        transport_osc.close()
        _log("Broker shut down.")


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nBroker stopped by user.")


if __name__ == '__main__':
    main()
