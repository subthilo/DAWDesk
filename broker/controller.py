"""
Datenmodell für eine einzelne Controller-Verbindung.
"""
import time
from dataclasses import dataclass, field


@dataclass
class ControllerConnection:
    """Repräsentiert einen verbundenen DAWDesk-Controller (Raspberry Pi)."""
    controller_id: str
    ip: str
    osc_port: int
    channels: int = 12
    last_seen: float = field(default_factory=time.monotonic)
    status: str = 'online'  # 'online' | 'offline'


    def update_seen(self):
        """Aktualisiert den Heartbeat-Timestamp und setzt Status auf 'online'."""
        self.last_seen = time.monotonic()
        self.status = 'online'

    def __repr__(self):
        return f"<Controller '{self.controller_id}' @ {self.ip}:{self.osc_port} [{self.status}]>"
