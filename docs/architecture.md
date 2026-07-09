# Architektur

## Projektstruktur

```
DAWDesk/
├── main.py                    # App-Einstiegspunkt, Initialisierung und FPS-Monitor
├── dawdesk.kv                 # Root-Layout Konfiguration
├── requirements.txt           # Python-Abhängigkeiten
├── scripts/                   # Automatisierungs- und Deployment-Skripte
│   ├── deploy.py              # Skript zum Pushen des Codes auf den Raspberry Pi
│   └── setup_rpi.py           # Skript zur Systemkonfiguration auf dem Pi
├── docs/                      # Dokumentation
│   ├── README.md
│   ├── architecture.md
│   ├── widgets.md
│   ├── configuration.md
│   ├── ProjectSpecifications.md
│   └── design-decisions.md
└── widgets/                   # Wiederverwendbare UI-Komponenten
    ├── __init__.py
    └── channel_strip.py       # DAWChannelStrip – High-Performance Single-Widget Kanalzug
```

## Modul-Verantwortlichkeiten

### `main.py`
- Einziger Ort für `kivy.require('2.0.0')`.
- Setzt Kivy-Konfigurationen (`postproc` für Zero-Latency Touch, `monitor` für FPS).
- Definiert `DAWDeskApp` und erstellt in `on_start()` dynamisch 12 `DAWChannelStrip`-Instanzen.
- Bietet den Einstiegspunkt für den Start der Anwendung.

### `dawdesk.kv`
- Sehr minimale Kivy-Language-Datei.
- Definiert das `DAWDeskRoot`-Layout (Toolbar oben, `MixerLayout` unten).
- Enthält keine Logik für den Kanalzug selbst, da dieser komplett in Python gezeichnet wird.

### `widgets/channel_strip.py`
- **Kernkomponente**: Das `DAWChannelStrip` Widget.
- Setzt die **Single-Widget Architecture** um: Es werden *keine* Sub-Widgets (wie Labels oder Layouts) verwendet.
- Alle UI-Elemente (Hintergrund, Pan-Ring, Fader-Linien, Pegelanzeigen, Texte) werden direkt über Kivy Canvas-Instruktionen (`Rectangle`, `Line`, `SmoothLine`, `Ellipse`) gezeichnet.
- Text wird mittels `kivy.core.text.Label` gepuffert und als Textur auf den Canvas gelegt (Caching-System).
- Behandelt sämtliche Touch-Events (`on_touch_down`, `on_touch_move`) intern und berechnet, ob das Pan- oder Fader-Control berührt wurde.

## Datenfluss
Da wir keine separaten Sub-Widgets mehr nutzen, existiert kein klassisches Kivy-Property-Binding mehr zwischen Eltern- und Kind-Komponenten innerhalb eines Kanalzugs. 
- Wenn `value` (Fader), `meter_value` oder `pan` geändert werden, feuert ein Kivy-Binding die interne Methode `_update_dynamic()`.
- Diese Methode modifiziert lediglich die existierenden Canvas-Instruktionen (z.B. `Line.points`, `Rectangle.pos`, `Rectangle.size`), anstatt neue zu generieren.
- Dies führt zu einem **Zero-Allocation Render Loop**, was den Garbage Collector entlastet und 60 FPS auf dem Raspberry Pi ermöglicht.

## Skalierungskonzept
- Das Widget berechnet seine internen Geometrien (Positionen, Höhen von Pan und Fader) in `_get_geometry()` dynamisch anhand der Widget-Breite und -Höhe.
- Texte und Elemente sind fix definiert, positionieren sich aber relativ zur Mitte (`center_x`) und passen sich in der Höhe prozentual an.
