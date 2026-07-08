# Architektur

## Projektstruktur

```
DAWDesk/
├── main.py                    # App-Einstiegspunkt, Demo-Kanäle
├── dawdesk.kv                 # Zentrale Styling- & Layout-Konfiguration
├── requirements.txt           # Python-Abhängigkeiten
├── docs/                      # Dokumentation
│   ├── README.md
│   ├── architecture.md
│   ├── widgets.md
│   ├── configuration.md
│   └── design-decisions.md
└── widgets/                   # Wiederverwendbare UI-Komponenten
    ├── __init__.py            # Paket mit __all__-Exporten
    ├── fader.py               # DAWFader – Lautstärkeregler
    ├── pan_knob.py            # DAWPanKnob – Pan-Regler (Kreisring)
    └── channel_strip.py       # DAWChannelStrip – Verbund-Widget (Kanalzug)
```

## Modul-Verantwortlichkeiten

### `main.py`
- Einziger Ort für `kivy.require('2.0.0')`.
- Definiert `DAWDeskApp` und erstellt in `on_start()` dynamisch Kanalzüge.
- Demonstriert verschiedene Pan-Skalen (L100/R100, L50/R50, L64/R64).

### `dawdesk.kv`
- **Zentrale Konfigurationsdatei** für alle visuellen Parameter.
- Enthält Klassenregeln (`<DAWFader>:`, `<DAWPanKnob>:`, `<DAWChannelStrip>:`) mit Styling-Werten.
- Definiert das Root-Layout (BoxLayout → mixer_layout).
- Zeichnet Trennstriche (canvas.after) auf dem Kanalzug.

### `widgets/fader.py`
- Eigenständiges Widget für den Lautstärkeregler.
- Enthält die gesamte Zeichen- und Touch-Logik.
- Konvertiert dB-Werte in Y-Positionen (logarithmische Kurve).

### `widgets/pan_knob.py`
- Eigenständiges Widget für den Pan-Regler.
- Zeichnet einen nach unten offenen Kreisring mit aktiver Füllung.
- Unterstützt vertikales und horizontales Dragging.

### `widgets/channel_strip.py`
- Container-Widget, das Pan-Knob, Fader und Label vertikal anordnet.
- Berechnet den reaktiven `scale`-Faktor für proportionale Skalierung.
- Definiert Layout-Properties (`pan_knob_size`, `label_height`), die auch von den Trennlinien genutzt werden.

## Datenfluss

```
main.py
  └── DAWChannelStrip(track_name="Kick", value=0.0, pan=0.0, ...)
        ├── DAWPanKnob   ← pan-Wert bidirektional gebunden
        ├── DAWFader     ← value/meter_value bidirektional gebunden
        └── Label        ← track_name gebunden
```

Alle Properties sind über Kivy-Bindings verknüpft: Ändert sich `DAWChannelStrip.pan`, aktualisiert sich `DAWPanKnob.value` automatisch und umgekehrt. Dasselbe gilt für den Fader-Wert.

## Skalierungskonzept

Das System nutzt einen **kombinierten Skalierungsfaktor** (`scale`), der auf dem `DAWChannelStrip` berechnet wird:

```python
scale_x = min(1.0, width / reference_width)   # Gedeckelt bei 1.0 (wächst nicht)
scale_y = height / reference_height            # Fließend
scale = min(scale_x, scale_y)                 # Kleinster Faktor gewinnt
```

**Kernprinzip**: Bei Verbreiterung des Kanals dehnt sich nur der Hintergrund – Knöpfe und Beschriftungen bleiben konstant. Bei Verschmälerung schrumpfen sie proportional mit, um Überlappungen zu vermeiden.

Dieses `scale`-Property wird von der KV-Datei für alle dynamischen Größen genutzt:
- Pan-Knob-Größe: `root.pan_knob_size * root.scale`
- Label-Höhe: `root.label_height * root.scale`
- Schriftgrößen: `max(14, int(22 * root.scale))`
- Trennlinien-Positionen
