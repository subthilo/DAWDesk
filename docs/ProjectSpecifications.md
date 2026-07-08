Architektur-Spezifikation: Custom Multi-DAW Controller (Cubase & Ableton Live)

1. Systemübersicht & Design-Philosophie

Dieses Projekt implementiert einen hochauflösenden, modularen DAW-Hardware-Controller (Touchscreen) mit Fokus auf Mischen, EQ, Routing und 60-fps-Metering.
Das Kernkonzept basiert auf dem Adapter-Muster (Decoupling) und strenger Modularität. Die grafische Oberfläche (GUI) und die DAWs kommunizieren niemals direkt miteinander.

Das System besteht aus drei isolierten Layern:

Layer 1: Frontend (Kivy): Dumme, performante Touch-GUI. Spricht ausschließlich ein standardisiertes, internes OSC-Protokoll.

Layer 2: Backend (Python-Broker): Die zentrale Intelligenz (State Management, dynamisches Banking). Nutzt das Strategy-Pattern, um Daten für die jeweilige Ziel-DAW zu übersetzen.

Layer 3: DAW-Endpoints: Dumme Dolmetscher in der jeweiligen Audiosoftware (JavaScript für Cubase, Max for Live für Ableton).

2. Detaillierte Modul-Spezifikationen

2.1 Frontend (Kivy)

Technologie: Python 3 / Kivy (Framework für NUI).

Architektur-Regel: Das UI kennt keine DAW-Spezifika (kein MIDI, kein "Cubase", kein "Ableton"). Es sendet und empfängt nur normierte Floats und Strings.

Implementierungs-Details:

Networking: Asynchroner UDP/OSC-Server und -Client (via python-osc). Darf die Kivy-Main-Loop (60 Hz) nicht blockieren (Nutzung von asyncio in Kombination mit Kivys async-Support).

Metering (Performance-Kritisch): Für VU-Meter dürfen keine Standard-Kivy-Widgets (wie ProgressBar) verwendet werden. Pegel MÜSSEN direkt über Kivy Canvas-Instruktionen (Rectangle, Color) gezeichnet werden. Updates erfolgen per OSC-Callback, der lediglich size und pos auf der GPU aktualisiert.

Lange Texte: Kanalnamen werden via Auto-Scaling (Schriftgröße) oder Animation (Marquee-Laufschrift) dargestellt, falls sie die Fader-Breite überschreiten.

2.2 Backend (Python-Broker)

Technologie: Python (Headless), mido / rtmidi (für SysEx), python-osc (für Netzwerk).

Rolle: Zentrale Vermittlungsstelle, Filter, Status-Halter (State Machine).

Implementierungs-Details (Das Schiebefenster / Sliding Window):

Der Broker empfängt von der aktiven DAW stets einen gigantischen Datenblock (z. B. 64 oder 128 Kanäle).

Er hält einen internen Status current_bank_offset (z. B. 0 für GUI-Kanäle 1-8).

Dynamisches Banking: Wechselt der User die Bank in Kivy, ändert der Broker nur den current_bank_offset und leitet ab sofort die Tracks 9-16 an Kivy weiter. An die DAW wird kein Bank-Befehl gesendet, bis das Fenster der 64 Tracks überschritten wird.

Design-Pattern (Strategy):

Der Broker implementiert eine Basisklasse DAWAdapter.

Davon erben CubaseAdapter und AbletonAdapter.

Je nach Nutzer-Auswahl instanziiert der Broker die passende Klasse.

2.3 DAW-Integration A: Cubase 12+ (MIDI Remote API)

Technologie: JavaScript (ES6, Cubase MIDI Remote API), Virtueller MIDI-Port (loopMIDI/IAC).

Protokoll: SysEx (System Exclusive) für 14-Bit-Auflösung ohne Kanal-Limits. Kein Standard-CC, kein Pitchbend, kein Mackie Control.

Implementierungs-Details:

Initialisierung: Erzeugt eine oversized MixerBankZone (64 Kanäle hardcodiert).

Feedback (DAW -> Broker): Abonniert mOnTitleChange, mOnColorChange, mOnProcessValueChange (Pegel).

Farb-Konvertierung: Cubase liefert Floats (0.0 - 1.0). JS skaliert auf 7-Bit (0-127) für den SysEx-Transport. Der Broker rechnet dies für Kivy wieder auf Floats oder Hex-Strings um.

Werte-Parsing (Broker -> DAW): Das JS-Skript liest SysEx, extrahiert MSB/LSB und berechnet den DAW-Float: (MSB << 7) + LSB / 16383.

2.4 DAW-Integration B: Ableton Live 11+ (Max for Live)

Technologie: Max for Live (M4L), Live Object Model (LOM), OSC (UDP).

Protokoll: Direkte OSC-Netzwerk-Kommunikation. Kein MIDI-Routing nötig!

Implementierungs-Details:

Device-Setup: Ein unsichtbares M4L-Device liegt auf dem Master-Track. Es enthält udpreceive (Port X) und udpsend (Port Y).

Steuerung (Broker -> DAW): Das M4L-Device parst eingehende OSC-Strings (z. B. /live/track/5/volume 0.75) und wandelt sie in LOM-Befehle um (path live_set tracks 4, set value 0.75). Hinweis: LOM nutzt oft 0-basierte Indizes.

Feedback (DAW -> Broker): M4L nutzt live.observer, um Änderungen an Namen, Farben und Werten zu überwachen und als OSC an den Broker zu pushen.

Echtzeit-Metering (60 fps): Abletons API-Metering ist zu langsam. M4L nutzt stattdessen plugout~ oder direkt das meter~ Audio-Objekt, getaktet mit einem metro Objekt (z. B. alle 16ms) für direkte, hochauflösende Peak-Werte via UDP an den Broker.

3. Protokoll-Spezifikationen & Datenstrukturen

3.1 Interne OSC-Pfade (Kivy <-> Broker)

Dies ist die einheitliche Sprache des Systems. Beide DAWs werden vom Broker auf dieses Format genormt.

/ui/fader/{id}/volume (Float 0.0 - 1.0)

/ui/fader/{id}/pan (Float 0.0 - 1.0)

/ui/display/{id}/name (String, unbegrenzte Länge)

/ui/display/{id}/color (String "#RRGGBB" oder 3 Floats)

/ui/meter/{id}/level (Float 0.0 - 1.0)

/ui/bank/next bzw. /ui/bank/prev (Trigger)

3.2 Broker <-> Cubase (SysEx-Struktur)

Da MIDI-Bytes maximal 0x7F (127) fassen können, nutzen wir folgendes proprietäres 7-Byte Format für Werteänderungen:

F0 (SysEx Start)

7D (Dummy Manufacturer ID für Non-Commercial Education/DIY)

[Command ID] (z. B. 01 = Volume, 02 = Pan, 03 = Color, 04 = Name-Char)

[Track Index] (0x00 bis 0x3F für Kanal 1-64)

[MSB] (Most Significant Byte des 14-Bit Werts)

[LSB] (Least Significant Byte des 14-Bit Werts)

F7 (SysEx End)

Hinweis zu Namen in Cubase: Strings müssen in der Cubase API in ASCII-Byte-Arrays zerlegt, auf mehrere SysEx-Pakete verteilt und im Broker wieder zu Strings zusammengesetzt werden (Chunking).

3.3 Broker <-> Ableton (OSC-Struktur)

Direkte Übersetzung, da Ableton/M4L native Strings und Floats versteht.

Broker sendet: /live/track/index/volume [Float]

Ableton sendet: /live/track/index/name [String]

Ableton sendet: /live/track/index/meter [Float]

4. Absolute Regeln für KI-gestützte Code-Generierung

Wenn Code generiert wird (in Cursor, Windsurf, Antigravity etc.), MÜSSEN folgende Regeln befolgt werden, da das System sonst kollabiert:

Strikte Isolierung (Single Responsibility): Ein generiertes Modul für Kivy darf niemals mido oder Ableton-Pfade enthalten. Der Broker ist der einzige Ort, der Protokolle übersetzt.

Kein Blocking (Async-First): Im Broker MUSS asyncio verwendet werden (z.B. asyncio.DatagramProtocol für OSC). In der Kivy-GUI MÜSSEN alle Updates im Kivy-Main-Thread via @mainthread Dekorator oder Clock.schedule_once erfolgen, da asynchrone Netzwerk-Threads sonst UI-Abstürze provozieren.

Cubase API Version: Generiere für Cubase ausschließlich Code, der mit der midiremote JS-API ab Cubase 12 kompatibel ist. Nutze niemals XML, Mackie Control oder HUI-Emulation.

Bit-Operationen & Float-Math: Generierter Python-Code für 14-Bit muss exakt validiert werden:

Float zu MSB/LSB: val_14 = int(float_val * 16383); msb = (val_14 >> 7) & 0x7F; lsb = val_14 & 0x7F

MSB/LSB zu Float: float_val = ((msb << 7) + lsb) / 16383.0

Stateful Broker: Der Broker darf UI-Eingaben nicht blind durchreichen. Er muss das eingehende UI-Fader-OSC mit dem current_bank_offset addieren, um den echten DAW-Track-Index zu berechnen.