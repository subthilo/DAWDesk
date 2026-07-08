# Designentscheidungen

Dieses Dokument beschreibt die wichtigsten technischen Entscheidungen, die während der Entwicklung getroffen wurden, sowie Kivy-spezifische Erkenntnisse.

## 1. Modularisierung: Warum drei separate Widget-Klassen?

**Entscheidung**: Jedes visuelle Element (Fader, Pan-Knob) ist ein eigenständiges Widget mit eigener Zeichenlogik. Der Kanalzug (`DAWChannelStrip`) ist ein reiner Container.

**Begründung**:
- Jedes Widget kann unabhängig getestet und wiederverwendet werden.
- Die Zeichenlogik bleibt überschaubar (ein Widget = eine Verantwortung).
- Spätere Erweiterungen (z.B. Mute/Solo-Buttons) können als separate Widgets hinzugefügt werden, ohne bestehenden Code zu ändern.

## 2. Property-Architektur: Python-Defaults vs. KV-Klassenregeln

**Entscheidung**: Properties werden in Python mit sinnvollen Fallback-Defaults definiert (`NumericProperty(3.0)`), aber in der KV-Datei über Klassenregeln (`<DAWPanKnob>:`) konfiguriert.

**Begründung**:
- **Python-Defaults** stellen sicher, dass ein Widget auch ohne KV-Datei funktioniert.
- **KV-Klassenregeln** bieten eine zentrale, leicht auffindbare Stelle für alle Styling-Parameter.
- Wer das Design anpassen will, muss nur `dawdesk.kv` öffnen – nicht den Python-Code.

### Trennungsprinzip: Was gehört wohin?

| Eigenschaft gehört auf… | Wenn… |
|------------------------|------|
| Das Widget selbst (`<DAWPanKnob>:`) | Sie nur das Aussehen/Verhalten des Widgets beeinflusst |
| Den Container (`DAWChannelStrip`) | Sie das Layout anderer Widgets beeinflusst (z.B. Trennlinien-Positionen) |

**Beispiel**: `ring_thickness` gehört auf den `DAWPanKnob`, weil eine dickere Linie keine Auswirkung auf die Trennlinien hat. `pan_knob_size` hingegen gehört auf den `DAWChannelStrip`, weil die Größe die Position der Trennlinien bestimmt.

## 3. Skalierung: Gedeckeltes Scale-Modell

**Entscheidung**: Horizontale Skalierung ist bei `1.0` gedeckelt. Verbreiterung des Kanals dehnt nur den Hintergrund aus.

**Begründung**:
- Bei einem echten Mischpult werden die Knöpfe auch nicht größer, wenn man das Pult breiter baut.
- Verschmälerung skaliert proportional herunter, um Überlappungen zu vermeiden.
- Vertikale Skalierung ist nicht gedeckelt – ein höherer Kanalzug bekommt einen größeren Fader-Bereich.

## 4. Center-Dot: `Line(ellipse=...)` statt `Ellipse`

**Entscheidung**: Der Center-Punkt des Pan-Reglers wird als kurzes `Line(ellipse=...)`-Segment gezeichnet, nicht als `Ellipse`.

**Begründung**:
- `Line` und `Ellipse` nutzen in Kivy unterschiedliche Rendering-Pipelines.
- `Ellipse` wird als gefüllte Textur gerendert, `Line` nutzt Antialiasing und `width`-basiertes Rendering.
- Bei gleicher Pixel-Stärke sah `Ellipse` deutlich dicker/anders aus als die `Line`-basierten L/R-Bögen.
- Durch die Verwendung von `Line(ellipse=..., width=ring_thickness)` für den Dot ist die visuelle Konsistenz mit den Bögen garantiert.

### Mathematik des Center-Dots

Der Dot wird als ein `Line`-Segment mit einem `delta`-Winkel gezeichnet, der aus der `ring_thickness`, dem Widget-Radius und der `dot_size_ratio` berechnet wird:

```python
dot_effective = ring_thickness * dot_size_ratio
arc_r = (min(w, h) / 2) - ring_thickness
delta = math.degrees(dot_effective / arc_r) if arc_r > 0 else 1.0
```

## 5. Pan-Anzeige: Kalibrierbare Skala

**Entscheidung**: Der interne Wert (`-1.0` bis `1.0`) wird über `pan_min`/`pan_max` auf die jeweilige DAW-Skala gemappt.

**Begründung**:
- Verschiedene DAWs verwenden unterschiedliche Pan-Skalen (L100/R100, L50/R50, L64/R64 für MIDI).
- Die Skala muss pro Kanal konfigurierbar sein (z.B. könnte ein MIDI-Kanal L64/R64 nutzen, während ein Audio-Kanal L100/R100 verwendet).
- Die Center-Erkennung (`C` statt `L0`/`R0`) arbeitet mit dem gerundeten Displaywert, sodass Werte nahe 0 korrekt als Center angezeigt werden.

## 6. Trennlinien: Canvas.after mit Property-basierter Berechnung

**Entscheidung**: Trennlinien werden im `canvas.after`-Block des Kanalzugs gezeichnet, wobei alle Positionen mathematisch über Properties berechnet werden.

**Begründung**:
- `canvas.after` stellt sicher, dass die Linien über allen Kind-Widgets liegen.
- Kivy-IDs (`id: pan_knob`) sind im `canvas`-Block nicht zuverlässig verfügbar (können während der Initialisierung noch nicht gebunden sein).
- Stattdessen werden alle benötigten Werte aus `self.padding`, `root.pan_knob_size * root.scale`, `self.spacing` und `root.divider_width_ratio` berechnet.
- **Vorteil**: Ändert man `pan_knob_size`, passen sich die Trennlinien automatisch an.

## 7. Drag-Achse: Vertikales Panning

**Entscheidung**: Der Pan-Knob nutzt standardmäßig vertikales Dragging (hoch = rechts, runter = links) statt horizontales.

**Begründung**:
- Bei einem vertikalen Kanalzug ist vertikales Wischen ergonomischer, da der Finger bereits in der vertikalen Achse arbeitet.
- Der Finger verdeckt bei vertikalem Wischen weniger vom Kreisring-Widget.
- Horizontales Wischen steht als Alternative über `drag_axis: 'horizontal'` zur Verfügung.
- Die Achse ist als `OptionProperty` umschaltbar – auch zur Laufzeit.
