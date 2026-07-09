# DAWDesk Widgets

Im Rahmen der Optimierung für den Raspberry Pi mit Kivy 2.3.1 wurde das klassische Kivy-Widget-Modell (viele kleine Widgets in Layouts) komplett verworfen.

## Das Single-Widget Konzept
Es gibt für einen Kanalzug nur noch **ein einziges** Kivy-Widget: den `DAWChannelStrip`.

### Warum?
Jedes Kivy-Widget (z.B. ein Label, ein Layout, ein Knopf) fügt Overhead beim Layouting und Event-Dispatching hinzu. Bei 12 Kanälen mit jeweils einem Pan-Knob, einem Fader, Pegelanzeigen und diversen Text-Labels summierte sich dies so stark auf, dass die FPS auf dem Raspberry Pi beim Wischen spürbar einbrachen.

### Die Lösung (`channel_strip.py`)
Der `DAWChannelStrip` erbt direkt von `Widget` und zeichnet ALLE visuellen Elemente (Pan-Ring, Fader, Pegel, Linien, Text) direkt auf seinen eigenen Canvas.

**Elemente auf dem Canvas:**
1. **Spurname**: Ein gecachter Kivy CoreText-Label, der als Textur gezeichnet wird.
2. **Pan Hintergrund**: Inaktive Ringe (`SmoothLine`), die statisch im `canvas.before` gezeichnet werden.
3. **Fader Hintergrund**: Die Ticks und Pegel-Hintergründe (Linien und Rechtecke).
4. **Pan Aktiv**: Der farbige Bogen, der den aktuellen Pan-Wert darstellt (im `canvas`). Wird in `_update_dynamic` durch Anpassen der `ellipse`-Property modifiziert.
5. **Fader Pegel & Kappe**: Der Pegel (`meter_value`) als Rechteck, sowie die Faderkappe. Die Kappe ist eine C-förmige Linie ohne Cap (`cap='none'`), umrahmt von zwei expliziten Kreisen (`Ellipse`) an den offenen Enden, um ein perfektes Rendering auf OpenGL-ES Hardware zu garantieren.
6. **Fader Ticks & Zahlen**: Ein halbtransparenter Streifen und die dB-Zahlen werden im `canvas.after` über die Faderkappe gezeichnet, sodass der Fader "unter" den Zahlen durchgleitet.

### Interaktivität (Touch)
Da es keine Sub-Widgets gibt, muss der `DAWChannelStrip` selbst berechnen, was berührt wurde:
- In `on_touch_down` wird geprüft, ob die Y-Koordinate im oberen Bereich (Pan) oder unteren Bereich (Fader) liegt.
- Das Touch-Event speichert den aktiven Bereich (z.B. `touch.ud['active_control'] = 'fader'`).
- In `on_touch_move` wird basierend auf dem `active_control` der jeweilige Wert (`pan` oder `value`) neu berechnet.

### Zero-Allocation
In `_update_dynamic` (aufgerufen bei Wertänderungen) werden *keine* neuen Canvas-Objekte erstellt. Es werden lediglich Eigenschaften wie `size`, `pos` oder `points` bestehender Objekte aktualisiert. Dies verhindert Garbage-Collection-Ruckler komplett.
