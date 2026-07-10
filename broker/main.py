"""
DAWDesk Broker — Einstiegspunkt.
Läuft auf dem Host-Computer (Mac/Linux).

Starten:
    python -m broker

Aufgaben in v1:
  - Discovery-Server: findet Controller im LAN via UDP-Broadcast
  - Registry-Watchdog: markiert inaktive Controller als offline
  - stdout-Logging: Verbindungsstatus und (später) Datenverkehr
"""
import asyncio
from datetime import datetime

from .registry import ControllerRegistry
from .discovery import start_discovery_server
from .osc_server import start_osc_server

WATCHDOG_INTERVAL = 5.0  # Sekunden zwischen Timeout-Checks


def _log(msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)


async def registry_watchdog(registry: ControllerRegistry):
    """
    Läuft als Background-Task.
    Prüft alle WATCHDOG_INTERVAL Sekunden auf timed-out Controller.
    """
    while True:
        await asyncio.sleep(WATCHDOG_INTERVAL)

        # Controller die gerade offline gegangen sind
        newly_offline = registry.check_timeouts()
        for controller_id in newly_offline:
            _log(f"✕ Controller '{controller_id}' OFFLINE (timeout)")

        # Status-Übersicht (nur wenn Controller bekannt sind)
        online = registry.get_online()
        all_ctrl = registry.get_all()
        if all_ctrl:
            online_ids  = [c.controller_id for c in online]
            offline_ids = [cid for cid, c in all_ctrl.items() if c.status == 'offline']
            parts = []
            if online_ids:
                parts.append(f"Online: {online_ids}")
            if offline_ids:
                parts.append(f"Offline: {offline_ids}")
            _log("  " + " | ".join(parts))


async def run():
    """Hauptkoroutine: startet alle Broker-Tasks."""
    registry = ControllerRegistry()

    _log("=" * 50)
    _log("  DAWDesk Broker  v1")
    _log("=" * 50)

    transport_disc, _ = await start_discovery_server(registry)
    transport_osc, _  = await start_osc_server()

    try:
        await registry_watchdog(registry)
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
