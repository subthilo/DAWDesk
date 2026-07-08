# Widgets

## DAWFader

**Datei**: `widgets/fader.py` (ca. 325 Zeilen)

Ein vollständig parametrisierbarer DAW-Lautstärkeregler mit logarithmischer dB-Skala, Meter-Pegelanzeige und interaktivem Knob.

### Visuelle Bestandteile

1. **Hintergrund** – Einfarbiges Rechteck über die gesamte Widget-Fläche
2. **Track** – Vertikale Rille in der Mitte (Schiene für den Knob)
3. **Meter-Hintergrund** – Kanal für die Pegelanzeige
4. **Meter (Cyan)** – Pegelbalken von unten bis `meter_value`
5. **Knob** – C-förmiger Griff (rechts offen), als Linienzug mit abgerundeten Ecken
6. **Folie** – Halbtransparente Überlagerung hinter den Labels
7. **Tick-Markierungen + dB-Labels** – Konfigurierbare Skala (z.B. +6, 0, -6, -12, …, -∞)
8. **Wertanzeige** – Aktueller dB-Wert innerhalb der C-Öffnung des Knobs

### dB-Mapping

Der Fader nutzt eine **potenz-basierte Kurve** zur Abbildung von dB auf Pixelpositionen:

```
ratio = (db - db_min) / (db_max - db_min)
curved = ratio ^ scale_exponent
y = pad + curved * usable_height
```

Mit `scale_exponent: 2.0` verteilt sich der untere dB-Bereich (z.B. -60 bis -30) auf weniger Pixel, während der obere Bereich (-6 bis +6) mehr Platz bekommt – wie bei einer echten DAW.

### Touch-Handling

- **Knob-Offset**: Beim Klicken wird der Y-Abstand zwischen Finger und Knob-Mitte gespeichert (`knob_offset_y`), damit der Knob nicht springt.
- **Dragging**: Vertikales Ziehen konvertiert die Y-Position in einen dB-Wert über `y_to_db()`.

---

## DAWPanKnob

**Datei**: `widgets/pan_knob.py` (ca. 158 Zeilen)

Ein interaktiver Pan-Regler, dargestellt als nach unten offener Kreisring mit aktiver Füllung und zentrierter Textanzeige.

### Visuelle Bestandteile

1. **Inaktiver Ring** – Dunkler Kreisbogen, unten offen (Öffnungswinkel konfigurierbar)
2. **Aktiver Bogen (Cyan)** – Füllt sich ausgehend von 12 Uhr (oben/Center) nach links oder rechts
3. **Center-Dot** – In Center-Stellung wird statt eines Bogens ein Punkt gezeichnet (als kurzes `Line`-Segment für identische Stärke)
4. **Center-Text** – Zeigt `C` (Center), `Lxx` (Links) oder `Rxx` (Rechts) basierend auf der DAW-Skala

### Pan-Skala & Kalibrierung

Der interne Wert (`value`) geht immer von `-1.0` (voll links) bis `1.0` (voll rechts). Die Anzeige wird über `pan_min` und `pan_max` auf die jeweilige DAW-Skala gemappt:

| DAW-Typ | `pan_min` | `pan_max` | Anzeige |
|---------|-----------|-----------|---------|
| Standard | -100 | 100 | L100 … C … R100 |
| Kompakt | -50 | 50 | L50 … C … R50 |
| MIDI | -64 | 64 | L64 … C … R64 |

### Center-Erkennung

Werte nahe 0 werden intelligent erkannt: Wenn `round(abs(value) * pan_max) == 0`, springt die Anzeige auf `C` und der Center-Dot wird gezeichnet. Dadurch werden `L0` oder `R0` Anzeigen vermieden.

### Touch-Handling

- **Drag-Achse**: Konfigurierbar über `drag_axis` – `'vertical'` (Standard: hoch = rechts) oder `'horizontal'` (rechts = rechts).
- **Sensitivity**: Über `drag_sensitivity` (Standard: `0.01`, d.h. 100px Drag = voller Wertebereich).

### Kivy-Koordinatensystem für Ellipsen

Bei `Line(ellipse=(...))` gilt:
- `0°` ist oben (12 Uhr)
- Positive Winkel verlaufen im Uhrzeigersinn
- `180°` ist unten (6 Uhr)

Die Öffnung des Rings liegt symmetrisch um 180°:
- Start: `180 + opening_angle / 2`
- Ende: Start + `360 - opening_angle`

---

## DAWChannelStrip

**Datei**: `widgets/channel_strip.py` (ca. 44 Zeilen)

Ein vertikales Container-Widget, das einen kompletten Mixer-Kanalzug darstellt. Es vereint Pan-Knob, Fader und Spurbezeichnung und verwaltet die reaktive Skalierung.

### Aufbau (von oben nach unten)

```
┌─────────────────────┐
│    DAWPanKnob       │  ← Kreisförmiger Pan-Regler
├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤  ← Horizontaler Trennstrich (zentriert, parametrisierbar)
│                     │
│    DAWFader          │  ← Lautstärkeregler (füllt den verbleibenden Platz)
│                     │
├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤  ← Horizontaler Trennstrich (zentriert, parametrisierbar)
│    Spurenname        │  ← Label mit mitskalierender Schrift
└─────────────────────┘
│                     │  ← Vertikale Trennstriche links und rechts
```

### Trennlinien

Die Trennlinien werden im `canvas.after`-Block der KV-Datei gezeichnet:

- **Vertikale Linien**: Links und rechts am Kanalrand (durchgehend)
- **Horizontale Linien**: Zwischen den Sektionen (zentriert, Breite über `divider_width_ratio` steuerbar)
- **Positionsberechnung**: Rein mathematisch über `self.padding`, `root.pan_knob_size * root.scale` und `self.spacing` – keine harten Pixelwerte

### Reaktive Skalierung

Der `scale`-Faktor wird bei jeder Größenänderung (`width`/`height`) neu berechnet und als Kivy-Property veröffentlicht. Alle gebundenen Elemente in der KV-Datei aktualisieren sich automatisch.
