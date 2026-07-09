# DAWDesk - High-Performance Controller für DAWs

DAWDesk ist ein Touchscreen-basierter virtueller Controller für Digital Audio Workstations (DAW), optimiert für den Betrieb auf einem **Raspberry Pi 4 / 5 mit offiziellem 7" Touch-Display**.

## Besonderheiten
- **High Performance:** Geschrieben in Python und Kivy. Das UI nutzt eine hochoptimierte Single-Widget Canvas-Architektur für Zero-Allocation Render-Loops und garantierte 60 FPS selbst bei 12 gleichzeitig dargestellten Kanälen.
- **Zero Latency Touch:** Tiefe Integration in die Linux MTDev/Input-Pipeline, um Latenzen bei Fader-Bewegungen vollständig zu eliminieren.
- **Raspberry Pi Optimiert:** Startet als systemd-Service direkt ohne X11/Wayland Desktop-Umgebung (EGLFS/DRM).

## Projektstruktur
* `main.py`: Einstiegspunkt der Anwendung. Setzt Zero-Latency Konfigurationen.
* `dawdesk.kv`: Minimale Layout-Konfiguration.
* `widgets/channel_strip.py`: Der gesamte Kanalzug (Pan, Fader, Pegel) als einzelnes High-Performance Widget.
* `scripts/`: Deployment- und Setup-Skripte für den Raspberry Pi.

## Installation & Deployment
Die Software wird lokal am Entwicklungsrechner bearbeitet und via SSH auf den Pi deployt.

Auf dem Mac (oder PC) ausführen:
```bash
python3 scripts/deploy.py <IP_DES_PI> <USER> <PASSWORT>
```
Das Skript kopiert den Code, installiert auf dem Pi alle System- und Python-Abhängigkeiten (Kivy 2.3.1), richtet ein Virtual Environment ein und erstellt einen Autostart-Service (`dawdesk.service`).

## Systemvoraussetzungen (Ziel-Hardware)
- Raspberry Pi (4 oder 5 empfohlen)
- Raspberry Pi OS (Bookworm oder neuer, 64-bit Lite Version empfohlen)
- Offizielles Raspberry Pi 7" Touch Display (oder kompatibles)
