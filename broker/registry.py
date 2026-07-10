"""
Registry: Verwaltet alle bekannten Controller-Verbindungen.
"""
import time
from .controller import ControllerConnection

# Sekunden ohne HELLO bevor ein Controller als offline gilt
OFFLINE_TIMEOUT = 15.0


class ControllerRegistry:
    """Thread-sichere Verwaltung aller DAWDesk-Controller."""

    def __init__(self):
        self._controllers: dict[str, ControllerConnection] = {}

    def register(self, controller_id: str, ip: str, osc_port: int) -> tuple[bool, bool]:
        """
        Registriert oder aktualisiert einen Controller.
        Returns: (is_new: bool, came_back_online: bool)
        """
        if controller_id in self._controllers:
            ctrl = self._controllers[controller_id]
            was_offline = ctrl.status == 'offline'
            ctrl.update_seen()
            ctrl.ip = ip
            ctrl.osc_port = osc_port
            return False, was_offline
        else:
            self._controllers[controller_id] = ControllerConnection(
                controller_id=controller_id,
                ip=ip,
                osc_port=osc_port
            )
            return True, False

    def get_online(self) -> list[ControllerConnection]:
        """Gibt alle aktuell verbundenen Controller zurück."""
        return [c for c in self._controllers.values() if c.status == 'online']

    def get_all(self) -> dict[str, ControllerConnection]:
        return dict(self._controllers)

    def check_timeouts(self) -> list[str]:
        """
        Prüft auf Timeouts. Gibt Liste der IDs zurück, die gerade offline gegangen sind.
        """
        now = time.monotonic()
        newly_offline = []
        for ctrl in self._controllers.values():
            if ctrl.status == 'online' and (now - ctrl.last_seen) > OFFLINE_TIMEOUT:
                ctrl.status = 'offline'
                newly_offline.append(ctrl.controller_id)
        return newly_offline
