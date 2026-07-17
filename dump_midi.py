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

print(f"Listening on {port_name} for 10 seconds. NUDGE NOW!")
inport = mido.open_input(port_name)

start = time.time()
count = 0
with open("midi_dump.txt", "w") as f:
    while time.time() - start < 10:
        msg = inport.poll()
        if msg:
            f.write(str(msg) + "\n")
            count += 1
        time.sleep(0.01)
inport.close()
print(f"Dumped {count} messages to midi_dump.txt")
