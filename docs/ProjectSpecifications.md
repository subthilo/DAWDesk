# DAWDesk - Project Specifications

## 1. Übersicht
**Projekt:** DAWDesk
**Zielplattform:** Raspberry Pi 4/5 mit offiziellem 7" Touch-Display (800x480).
**Technologie:** Python 3, Kivy 2.3.1 (EGLFS/DRM Modus).

## 2. Visuelles Konzept & Design
*   **Farbschema:** Dark Mode. Tiefe Blau/Grau-Töne (`#050812` bis `#141824`). Akzente in hellem Cyan (`#00E5E5`).
*   **UI-Paradigma:** Skeuomorphistisch angehaucht, aber modern und flach. Keine 3D-Schatten, stattdessen klare Linien und Transparenzen.
*   **Kanäle:** Bis zu 12 Kanäle gleichzeitig sichtbar (skaliert automatisch, wenn `NUM_CHANNELS` in `main.py` angepasst wird).

## 3. Kanalzug (Channel Strip)
Ein Kanalzug besteht visuell aus folgenden Elementen, wird technisch aber als ein einzelnes Kivy-Widget (`DAWChannelStrip`) gerendert.

### 3.1 Spurbezeichnung
*   Text-Label zentriert im oberen Drittel.
*   Farbe: Weiß/Hellblau.

### 3.2 Pan-Regler (Panorama)
*   Form: Ein nach unten offener Kreisring (60 Grad Öffnung unten).
*   Darstellung: Ein grauer Hintergrund-Ring, auf dem ein Cyan-farbener "Füll"-Bogen den aktuellen Wert anzeigt.
*   Wertebereich: L100 (links) bis R100 (rechts). Mitte ist "C".
*   Bedienung: Touch und vertikaler oder horizontaler Swipe zur Wertänderung.

### 3.3 Fader (Lautstärke)
*   **Skala:** -60 dB (unten) bis +6 dB (oben).
*   **Kurve:** Logarithmische Darstellung (quadratische Funktion für die Y-Position), um im fein steuerbaren Bereich (um 0 dB) mehr Pixelauflösung zu haben.
*   **Hintergrund:** Ein dunkler Schlitz (`c_track`).
*   **Pegelanzeige:** Ein Cyan-Balken, der innerhalb des Schlitzes von unten nach oben wächst.
*   **Fader-Kappe:** C-förmig (links geschlossen, rechts offen). Gezeichnet mit Kivy `Line` (`cap='none'`) und expliziten `Ellipse`-Abschlüssen für sauberes Rendering.
*   **Ticks:** Horizontale Striche. Ein halbtransparenter Streifen läuft unter den Ticks, aber *über* der Faderkappe, sodass diese elegant hindurchgleitet.
*   **Zahlen:** Dezibel-Werte auf dem transparenten Streifen links neben den Ticks.

## 4. Performance-Vorgaben
*   **Ziel:** Stabile 60 FPS bei Multitouch auf 12 Kanälen gleichzeitig.
*   **Strategie:** Vermeidung von Objektallokationen (Garbage Collection) während Touch-Events. Text-Caching in Texturen. Direct-Canvas-Drawing (Single-Widget).

## 5. Deployment
*   Das Projekt muss ohne Desktop-Umgebung (X11/Wayland) direkt in den Framebuffer booten können (`systemd` Service).
*   Automatisierter Deployment-Prozess via Python-Skript von einem Entwicklungsrechner.