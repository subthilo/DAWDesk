import os
import json
from typing import List

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'broker_config.json')

class BrokerConfig:
    """Verwaltet persistente Broker-Einstellungen, z.B. die Reihenfolge der Controller."""
    
    def __init__(self):
        self.controller_order: List[str] = []
        self._load()

    def _load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.controller_order = data.get('controller_order', [])
            except Exception as e:
                print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'controller_order': self.controller_order}, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get_order(self) -> List[str]:
        return self.controller_order

    def set_order(self, order: List[str]):
        self.controller_order = order
        self.save()
