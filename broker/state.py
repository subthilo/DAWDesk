from .config import BrokerConfig
from .registry import ControllerRegistry

class BrokerState:
    def __init__(self, broker_config: BrokerConfig, registry: ControllerRegistry):
        self.broker_config = broker_config
        self.registry = registry
        self.bank_offset = 0  # Our "Nudge" offset within the current Cubase bank
        self.cubase_bank_index = 0 # How many 60-track banks Cubase is currently shifted
        self.track_values = {} # {track_index: {cmd: float_val}}
        self.transport_state = {0: 0.0, 1: 0.0, 2: 0.0} # {cmd_idx: float_val}
        self.on_routing_changed = None # Callback when offset changes
        self.cubase_bank_index = 0
        self.bank_cache = {} # {bank_index: {track_index: {cmd: val}}}

    def update_track_value(self, track: int, cmd: int, val: float):
        if track not in self.track_values:
            self.track_values[track] = {}
        self.track_values[track][cmd] = val

    def get_track_value(self, track: int, cmd: int) -> float:
        default_val = 0.5 if cmd == 0x02 else 0.0
        return self.track_values.get(track, {}).get(cmd, default_val)

    def update_transport_state(self, cmd_idx: int, val: float):
        self.transport_state[cmd_idx] = val
        
    def get_transport_state(self, cmd_idx: int) -> float:
        return self.transport_state.get(cmd_idx, 0.0)

    def update_track_name(self, track: int, name: str):
        if track not in self.track_values:
            self.track_values[track] = {}
        self.track_values[track][0x03] = name

    def get_track_name(self, track: int) -> str:
        return self.track_values.get(track, {}).get(0x03, "")

    def update_track_color(self, track: int, color: tuple):
        if track not in self.track_values:
            self.track_values[track] = {}
        self.track_values[track][0x04] = color

    def get_track_color(self, track: int) -> tuple:
        return self.track_values.get(track, {}).get(0x04, (0.55, 0.62, 0.68))

    def get_daw_track_index(self, controller_id: str, local_channel: int) -> int:
        """
        Maps a specific controller's local channel (1-indexed) to a continuous DAW track index (0-indexed).
        Returns -1 if the controller is not registered or not in the layout.
        """
        order = self.broker_config.get_order()
        if controller_id not in order:
            return -1
        
        all_controllers = self.registry.get_all()
        if controller_id not in all_controllers:
            return -1

        absolute_index = 0
        
        for cid in order:
            if cid == controller_id:
                # We found the controller, add its local offset
                # local_channel is 1-indexed (1, 2, 3...)
                # absolute_index is 0-indexed (0, 1, 2...)
                bank_base = self.cubase_bank_index * 60
                return absolute_index + (local_channel - 1) + self.bank_offset + bank_base
            
            # Add the number of channels of the previous controller
            if cid in all_controllers:
                absolute_index += all_controllers[cid].channels
        
        return -1

    def get_controller_and_local_channel(self, daw_track_index: int) -> tuple[str, int]:
        """
        Maps an absolute DAW track index (0-indexed) back to a controller ID and local channel (1-indexed).
        Returns (None, -1) if the index is out of bounds.
        """
        if daw_track_index < 0:
            return None, -1
            
        bank_base = self.cubase_bank_index * 60
        target_index = daw_track_index - self.bank_offset - bank_base
        if target_index < 0:
            return None, -1
            
        order = self.broker_config.get_order()
        all_controllers = self.registry.get_all()
        
        absolute_index = 0
        for cid in order:
            if cid in all_controllers:
                channels = all_controllers[cid].channels
                if absolute_index <= target_index < absolute_index + channels:
                    # Found the controller
                    local_channel = target_index - absolute_index + 1
                    return cid, local_channel
                absolute_index += channels
                
        return None, -1
