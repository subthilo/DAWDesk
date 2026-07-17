import mido
import time

port_name = "DAWDesk"

print(f"Available ports: {mido.get_output_names()}")

try:
    outport = mido.open_output(port_name, virtual=False)
    inport = mido.open_input(port_name, virtual=False)
    print(f"Connected to existing {port_name} port.")
except Exception as e:
    print(f"Failed to connect to existing port: {e}. Are you sure the broker is running?")
    exit(1)

received_msgs = 0

def on_msg(msg):
    global received_msgs
    received_msgs += 1
    # print(msg)

inport.callback = on_msg

print("Waiting 1 second...")
time.sleep(1.0)

print("Sending Nudge Right (CC 127)...")
outport.send(mido.Message('control_change', channel=14, control=127, value=127))
outport.send(mido.Message('control_change', channel=14, control=127, value=0))

time.sleep(2.0)
print(f"Received {received_msgs} messages after Nudge Right.")
received_msgs = 0

print("Sending Nudge Left (CC 126)...")
outport.send(mido.Message('control_change', channel=14, control=126, value=127))
outport.send(mido.Message('control_change', channel=14, control=126, value=0))

time.sleep(2.0)
print(f"Received {received_msgs} messages after Nudge Left.")

