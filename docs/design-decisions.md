# Design Decisions

Dieses Dokument protokolliert wesentliche technische Entscheidungen während der Entwicklung von DAWDesk.

## 1. Single-Widget Architektur (Canvas Drawing)
**Problem:** Die Performance auf dem Raspberry Pi (Kivy 2.3.1) war unzureichend, wenn 12 Kanäle mit Sub-Widgets (Layouts, Fader-Klassen, Pan-Klassen, Labels) genutzt wurden.
**Entscheidung:** Verzicht auf Kivy's Standard-Layout-System zugunsten eines einzelnen Widgets pro Kanal (`DAWChannelStrip`), das alles auf seinen Canvas zeichnet.
**Resultat:** Deutlich höhere und stabile Framerate (60 FPS), da der Overhead für Event-Dispatching und Layout-Berechnungen von hunderten auf exakt 12 Widgets reduziert wurde. Zero-Allocation Render Loop verhindert GC-Spikes.

## 2. Text-Rendering
**Problem:** `Label`-Widgets erzeugen extrem viel Overhead.
**Entscheidung:** Texte werden mittels `kivy.core.text.Label` gerendert und die resultierende Textur in einem Dictionary gecacht (z.B. "Ch 1", "-6.0"). Beim Zeichnen wird lediglich ein `Rectangle` mit dieser Textur auf den Canvas gelegt.
**Resultat:** Keine Frame-Drops bei sich ändernden Texten.

## 3. Fader Kappe Rendering auf Pi
**Problem:** `cap='round'` bei Kivy's `Line` funktionierte auf der OpenGL-ES Implementierung des Raspberry Pi nicht zuverlässig. Die Enden waren abgeschnitten (Square-Caps).
**Entscheidung:** Der C-förmige Fader wird mit `cap='none'` gezeichnet. Die runden Enden der Linien werden durch manuelle `Ellipse`-Objekte mit dem Radius der Linienbreite exakt an den Endkoordinaten gezeichnet.
**Resultat:** Perfekte Pillen- bzw. Rundform auch auf dem Pi.

## 4. Overlay der Fader-Ticks
**Problem:** Die Faderkappe sollte die Tick-Striche und Zahlen nicht verdecken, sondern sanft unter ihnen "hindurchgleiten".
**Entscheidung:** Nutzung von Kivy's `canvas.after`. Ein halbtransparenter Streifen (Folie) und die Texte/Striche werden im `canvas.after` gezeichnet.
**Resultat:** Die Fader-Kappe (im regulären `canvas`) liegt visuell unter den Ticks, bleibt aber gut sichtbar.

## 5. Input Configuration (Zero Latency)
**Problem:** Kivy verzögerte standardmäßig Touch-Events, um zu erkennen, ob der User swiped oder tappt (Jitter-Distance, Retain-Time).
**Entscheidung:** In `main.py` wurden alle Post-Processing Filter (wie `retain_time`, `jitter_distance`) auf 0 gesetzt.
**Resultat:** Sofortiges, direktes Feedback beim Berühren der Fader auf dem Pi.
