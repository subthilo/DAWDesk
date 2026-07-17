import mido
import sys
import time

port_name = None
for p in mido.get_input_names():
    if "DAWDesk" in p:
        port_name = p
        break

if not port_name:
    print("Port not found")
    sys.exit(1)

print(f"Listening on {port_name} for 3 seconds...")
inport = mido.open_input(port_name)

start = time.time()
count = 0
while time.time() - start < 3:
    msg = inport.poll()
    if msg:
        if msg.type == 'control_change' and msg.channel == 14:
            print(f"Received CH 15 CC {msg.control} Val {msg.value}")
            count += 1
            if count > 10:
                break
    time.sleep(0.01)
inport.close()
print(f"Received {count} messages on CH 15.")
