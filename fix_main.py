import re

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'r') as f:
    content = f.read()

# Replace set_callback and inject on_routing_changed
match1 = re.search(r'    cubase_adapter\.set_callback\(on_cubase_event\)', content)
if match1:
    replacement1 = """    _push_task = None
    def on_routing_changed():
        nonlocal _push_task
        if _push_task and not _push_task.done():
            _push_task.cancel()
        async def _push():
            try:
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
    cubase_adapter.set_callback(on_cubase_event)"""
    content = content[:match1.start()] + replacement1 + content[match1.end():]

# Replace request_cubase_state
match2 = re.search(r'    async def request_cubase_state\(\):\n(?:.*?\n){1,15}            _sync_in_progress = False', content, re.MULTILINE | re.DOTALL)
if match2:
    replacement2 = """    async def request_cubase_state():
        nonlocal _sync_in_progress
        if _sync_in_progress: return
        _sync_in_progress = True
        try:
            _log("Requesting full state sync from Cubase (400 tracks)...")
            cubase_adapter.send_nudge(-1) # Force to bank 0
            await asyncio.sleep(0.1)
            cubase_adapter.send_nudge(1)
            await asyncio.sleep(0.4)
            cubase_adapter.send_nudge(-1)
            await asyncio.sleep(0.4)
            if hasattr(state, 'on_routing_changed') and state.on_routing_changed:
                state.on_routing_changed()
        except asyncio.CancelledError:
            pass
        finally:
            _sync_in_progress = False"""
    content = content[:match2.start()] + replacement2 + content[match2.end():]

with open('/Users/thilo/Library/CloudStorage/SynologyDrive-DatenSync/Repos/DAWDesk/broker/main.py', 'w') as f:
    f.write(content)
