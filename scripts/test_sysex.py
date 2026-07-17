import mido
import time
import platform
import os
import sys

PORT_NAME = "DAWDesk"

print("--- DAWDesk SysEx Test ---")
print("HINWEIS: Bitte stelle sicher, dass der normale Broker GESTOPPT ist,")
print("bevor du dieses Skript ausführst, da sonst die Ports belegt sind!\n")

try:
    if platform.system() == "Darwin" or platform.system() == "Linux":
        outport = mido.open_output(PORT_NAME, virtual=True)
        inport = mido.open_input(PORT_NAME, virtual=True)
    else:
        available_ports = mido.get_output_names()
        target_port = next((p for p in available_ports if PORT_NAME in p), None)
        outport = mido.open_output(target_port)
        inport = mido.open_input(target_port)
except Exception as e:
    print(f"❌ Fehler beim Öffnen des MIDI Ports: {e}")
    sys.exit(1)

received = []

def callback(msg):
    if msg.type == 'sysex':
        print(f"✅ ERFOLG! Echo von Cubase empfangen: {msg.hex()}")
        received.append(msg)

inport.callback = callback

# Wir senden eine harmlose Test-SysEx-Nachricht
sysex_msg = mido.Message('sysex', data=[0x7D, 0x11, 0x22, 0x33])
print(f"Sende Test-SysEx an Cubase: {sysex_msg.hex()}")
print("Warte 2 Sekunden auf Echo...\n")
outport.send(sysex_msg)

time.sleep(2)

if not received:
    print("❌ FEHLGESCHLAGEN: Kein Echo erhalten.")
    print("Mögliche Gründe:")
    print("1. Cubase hat das Skript noch nicht neu geladen.")
    print("2. Cubase Remote API blockiert SysEx in dieser Konfiguration.")
    print("3. Cubase ist nicht mit dem Port verbunden.")
else:
    print("\n🎉 Test erfolgreich abgeschlossen! SysEx funktioniert einwandfrei.")

outport.close()
inport.close()
