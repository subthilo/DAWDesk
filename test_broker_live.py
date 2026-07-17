import asyncio
import time
from broker.state import BrokerState
from broker.config import BrokerConfig
from broker.registry import ControllerRegistry
from broker.cubase_adapter import CubaseAdapter
import broker.osc_server as osc_server

async def test():
    print("Initializing test...")
    registry = ControllerRegistry()
    broker_config = BrokerConfig()
    registry.register("rpi-studio-1", "127.0.0.1", 8000, 12)
    broker_config.set_order(["rpi-studio-1"])
    
    state = BrokerState(broker_config, registry)
    osc_server.state = state

    adapter = CubaseAdapter(port_name="DAWDeskTest")
    osc_server.daw_adapter = adapter
    
    print("Simulating Cubase sending initial bank (24 channels)...")
    for i in range(24):
        state.update_track_value(i, 0x01, 0.5) 
        state.update_track_value(i, 0x02, 0.5) 
        state.update_track_color(i, (0.5, 0.5, 0.5))
        state.update_track_name(i, f"Track {i+1}")
        
    print("Current Kivy layout (Pi 1: 1-12):")
    for i in range(12):
        cid, ch = state.get_controller_and_local_channel(i)
        print(f"Hardware Track {i} maps to {cid} Channel {ch}")
        
    print("\nSimulating Kivy sending 'Nudge 1'...")
    osc_server.handle_nudge("/ui/rpi-studio-1/nudge", 1)
    
    print("Test completed successfully.")

if __name__ == "__main__":
    asyncio.run(test())
