# Konfiguration

Die Software ist primär für den Raspberry Pi konzipiert und liest Konfigurationen sowohl aus Kivy's Config-System als auch aus hardcodierten Konstanten.

## `main.py` Konfigurationen
Hier werden fundamentale Konstanten gesetzt, die das Verhalten der gesamten App steuern:

- `NUM_CHANNELS = 12`: Legt fest, wie viele Kanalzüge beim Start in das `MixerLayout` geladen werden. Die Breite der Kanäle skaliert automatisch anhand der Fenstergröße.
- **FPS Monitor**: `Config.set('modules', 'monitor', '')` ist standardmäßig aktiv, um auf dem Pi die Performance überwachen zu können.

## Kivy Touch-Optimierung
Damit die Fader ohne spürbare Verzögerung reagieren, werden in der `main.py` (VOR dem Import von Kivy-Modulen) interne Filter deaktiviert:
```python
Config.set('postproc', 'retain_time', '0')
Config.set('postproc', 'retain_distance', '0')
Config.set('postproc', 'jitter_distance', '0')
Config.set('postproc', 'jitter_ignore', '1')
```
Dies führt im EGLFS-Modus auf dem Raspberry Pi zu echtem "Zero-Latency" Touch.

## Geräte-spezifische Konfiguration (`device_config.json`)
Da das Kivy-Display auf dem Raspberry Pi (insbesondere im Direct-DRM Modus) manchmal gedreht ist, kann eine `device_config.json` neben der `main.py` abgelegt werden.

Beispiel für eine 180-Grad Drehung (wird vom Deployment-Skript automatisch verwaltet):
```json
{
  "rotation": 180
}
```
Die `main.py` liest diese Datei und setzt `Config.set('graphics', 'rotation', ...)` entsprechend.

## Farben & Styling
Alle Farben sind in `widgets/channel_strip.py` als Kivy `ColorProperty` direkt in der Klasse definiert. Sie können dort global angepasst werden:
- `c_bg`: Widget Hintergrund
- `c_track`: Fader-Schlitz
- `c_fader`: Fader-Kappe
- `c_meter`: Pegelanzeige (Cyan)
- `c_text`: Textfarbe
- `c_tick`: Farbe der kleinen Striche
