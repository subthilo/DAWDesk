# Konfiguration

Alle visuellen und funktionalen Parameter werden zentral in `dawdesk.kv` über Kivy-Klassenregeln konfiguriert. Die Python-Dateien definieren lediglich Fallback-Standardwerte.

## Wo wird was konfiguriert?

| Property | Definiert in | Gesetzt in | Beschreibung |
|----------|-------------|-----------|-------------|
| **Visuell (Fader)** | `fader.py` | `dawdesk.kv` `<DAWFader>:` | Knob-Form, Skala, Farben |
| **Visuell (Pan)** | `pan_knob.py` | `dawdesk.kv` `<DAWPanKnob>:` | Ring-Dicke, Öffnung, Drag |
| **Layout** | `channel_strip.py` | `dawdesk.kv` `<DAWChannelStrip>:` | Pan-Größe, Label-Höhe, Trennlinien |
| **Daten** | `channel_strip.py` | `main.py` (zur Laufzeit) | Werte, Pan, Meter, Spurname |

## DAWFader – Properties

Alle gesetzt in `<DAWFader>:` (dawdesk.kv, Zeilen 5–24):

| Property | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `knob_height` | Numeric | 38 | Höhe des Knobs in Pixel (Basis) |
| `knob_width_ratio` | Numeric | 0.7 | Breite des Knobs relativ zur Widget-Breite |
| `knob_corner_radius` | Numeric | 10 | Eckenradius des Knobs |
| `knob_x_offset` | Numeric | -10 | Horizontaler Versatz des Knobs |
| `knob_line_width` | Numeric | 4.0 | Linienstärke des C-förmigen Knobs |
| `track_width` | Numeric | 8 | Breite der Track-Rille |
| `meter_width` | Numeric | 6 | Breite des Meter-Balkens |
| `meter_x_offset` | Numeric | 0 | Horizontaler Versatz des Meters |
| `ticks_x_offset` | Numeric | 0 | Horizontaler Versatz der Tick-Markierungen |
| `labels_x_offset` | Numeric | -35 | Horizontaler Versatz der dB-Labels |
| `default_tick_width` | Numeric | 20 | Standardbreite der Tick-Striche |
| `tick_line_width` | Numeric | 1.5 | Linienstärke der Tick-Striche |
| `label_font_size` | Numeric | 22 | Schriftgröße der dB-Labels |
| `value_font_size` | Numeric | 20 | Schriftgröße der Wertanzeige im Knob |
| `value_display_x_offset` | Numeric | -25 | X-Versatz der Wertanzeige |
| `foil_padding` | Numeric | 6 | Padding der Folie hinter den Labels |
| `db_min` | Numeric | -60.0 | Unteres dB-Limit |
| `db_max` | Numeric | 6.0 | Oberes dB-Limit |
| `scale_exponent` | Numeric | 2.0 | Exponent der logarithmischen Kurve |

## DAWPanKnob – Properties

Alle gesetzt in `<DAWPanKnob>:` (dawdesk.kv, Zeilen 26–32):

| Property | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `ring_thickness` | Numeric | 2.0 | Stärke des Kreisrings |
| `opening_angle` | Numeric | 90.0 | Öffnungswinkel des Rings unten (in Grad) |
| `font_size` | Numeric | 14 | Schriftgröße der Center-Anzeige (Basis) |
| `dot_size_ratio` | Numeric | 1.0 | Punkt-Stärke relativ zur Ring-Dicke (1.0 = identisch) |
| `drag_sensitivity` | Numeric | 0.01 | Wertänderung pro Pixel Dragging |
| `drag_axis` | Option | `'vertical'` | Wischrichtung: `'vertical'` oder `'horizontal'` |

### Nicht in der KV-Datei (nur als Fallback in Python definiert):

| Property | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `value` | Numeric | 0.0 | Aktueller Pan-Wert (-1.0 bis 1.0) |
| `pan_min` | Numeric | -100.0 | Mappings-Limit für Links-Anschlag |
| `pan_max` | Numeric | 100.0 | Mappings-Limit für Rechts-Anschlag |
| `active_color` | Color | (0.0, 0.9, 0.9) | Farbe des aktiven Bogens (Cyan) |
| `inactive_color` | Color | (0.08, 0.12, 0.18) | Farbe des inaktiven Rings |
| `text_color` | Color | (0.85, 0.92, 0.95) | Farbe des Center-Texts |
| `text_opacity` | Numeric | 0.85 | Deckkraft des Texts |

## DAWChannelStrip – Properties

Gesetzt in `<DAWChannelStrip>:` (dawdesk.kv, Zeilen 34–47) und `main.py`:

### Layout-Properties (dawdesk.kv)

| Property | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `pan_knob_size` | Numeric | 135.0 | Basisgröße des Pan-Knopfes (px, vor Skalierung) |
| `label_height` | Numeric | 35.0 | Basishöhe des Namenlabels (px, vor Skalierung) |
| `divider_width_ratio` | Numeric | 0.6 | Breite der Trennstriche relativ zur Widget-Breite |
| `reference_height` | Numeric | 600.0 | Referenzhöhe für Skalierungsberechnung |
| `reference_width` | Numeric | 180.0 | Referenzbreite (Skalierung gedeckelt bei 1.0) |

### Daten-Properties (main.py)

| Property | Typ | Default | Beschreibung |
|----------|-----|---------|-------------|
| `track_name` | String | "Spur" | Angezeigter Spurname |
| `value` | Numeric | -60.0 | Fader-dB-Wert |
| `meter_value` | Numeric | -60.0 | Meter-Pegelwert (dB) |
| `pan` | Numeric | 0.0 | Pan-Position (-1.0 bis 1.0) |
| `pan_min` | Numeric | -100.0 | Anzeige-Skala Links-Limit |
| `pan_max` | Numeric | 100.0 | Anzeige-Skala Rechts-Limit |

## Beispiel: Einen Wert ändern

### In der KV-Datei (vor App-Start):
```yaml
<DAWPanKnob>:
    ring_thickness: 5.0        # Dickerer Ring
    drag_axis: 'horizontal'    # Links/Rechts wischen statt Hoch/Runter
```

### Zur Laufzeit aus Python:
```python
# Pan-Knob eines Kanalzugs anpassen
channel = mixer.children[0]
channel.ids.pan_knob.ring_thickness = 5.0
channel.ids.pan_knob.drag_axis = 'horizontal'

# Kanalzug-Layout ändern
channel.pan_knob_size = 100.0   # Kleinerer Pan-Knob + Trennlinie passt sich an
channel.divider_width_ratio = 0.8  # Breitere Trennstriche
```

Alle Änderungen lösen automatisch ein Neuzeichnen aus – kein manuelles Rendern nötig.
