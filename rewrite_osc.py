import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/osc_server.py', 'r') as f:
    content = f.read()

match = re.search(r'    def handle_nudge\(address: str, \*args\):', content)
end_match = re.search(r'    def handle_ping\(address: str, \*args\):', content)

if match and end_match:
    new_func = """    def handle_nudge(address: str, *args):
        parts = address.strip('/').split('/')
        if len(parts) == 3:
            controller_id = parts[1]
            try:
                steps = int(args[0]) if args else None
                if steps is not None and steps != 0:
                    _log(f"  ↓ [{controller_id}] nudge  {steps}")
                    
                    all_controllers = state.registry.get_all()
                    displayable_channels = sum(c.channels for c in all_controllers.values())
                    if displayable_channels == 0:
                        displayable_channels = 12 # Fallback
                        
                    max_offset = max(0, 400 - displayable_channels)
                    new_offset = state.bank_offset + steps
                    
                    state.bank_offset = max(0, min(max_offset, new_offset))
                    
                    _log(f"  → Routing offset is now {state.bank_offset} (In-Memory)")
                    
                    if hasattr(state, 'on_routing_changed') and state.on_routing_changed:
                        state.on_routing_changed()
            except Exception as e:
                _log(f"  [ERROR] Nudge processing failed: {e}")

"""
    content = content[:match.start()] + new_func + content[end_match.start():]
    
    with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/osc_server.py', 'w') as f:
        f.write(content)
