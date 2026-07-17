import asyncio
from broker.state import BrokerState
from broker.config import BrokerConfig
from broker.registry import ControllerRegistry
from broker.cubase_adapter import CubaseAdapter
import broker.osc_server as osc_server

class MockCubaseAdapter:
    def __init__(self):
        self.nudge_commands_sent = []
    def send_nudge(self, steps):
        self.nudge_commands_sent.append(steps)
        print(f"    [MockCubaseAdapter] Sent native Nudge({steps}) to Cubase!")

async def test():
    print("\n--- STARTING VIRTUAL TEST ---")
    registry = ControllerRegistry()
    broker_config = BrokerConfig()
    registry.register("rpi-studio-1", "127.0.0.1", 8000, 12)
    broker_config.set_order(["rpi-studio-1"])
    
    state = BrokerState(broker_config, registry)
    osc_server.state = state

    adapter = MockCubaseAdapter()
    osc_server.daw_adapter = adapter
    
    print("\n1. Kivy Pi sends a single Nudge Right (user tapped '1 >')")
    print("  -> OSC receives: /ui/rpi-studio-1/nudge 1")
    osc_server.handle_nudge("/ui/rpi-studio-1/nudge", 1)
    
    print("\n2. Kivy Pi sends a Nudge Left (user tapped '< 1')")
    print("  -> OSC receives: /ui/rpi-studio-1/nudge -1")
    osc_server.handle_nudge("/ui/rpi-studio-1/nudge", -1)

    print("\n3. Kivy Pi sends an 8x Nudge Right (user tapped '8 >')")
    print("  -> OSC receives: /ui/rpi-studio-1/nudge 8")
    osc_server.handle_nudge("/ui/rpi-studio-1/nudge", 8)
    
    print("\n--- TEST COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    asyncio.run(test())
