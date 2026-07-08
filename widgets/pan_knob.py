import math
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ColorProperty, OptionProperty
from kivy.graphics import Color, Line, Rectangle
from kivy.core.text import Label as CoreLabel


class DAWPanKnob(Widget):
    """Dynamisches Pan-Regler Widget.
    Stellt einen nach unten unterbrochenen Kreisring dar.
    Die Füllung zeigt den aktuellen Panning-Wert (-1.0 bis 1.0) reaktiv an.
    In der Mitte befindet sich ein mitskalierendes Label für den kalibrierten Wert.
    """

    value = NumericProperty(0.0)           # -1.0 (Links) bis 1.0 (Rechts)
    ring_thickness = NumericProperty(3.0)  # Ringstärke (standardmäßig dünner)
    opening_angle = NumericProperty(90.0)  # Öffnungswinkel unten in Grad

    # Skalierungseinstellungen für den Center-Text
    pan_min = NumericProperty(-100.0)      # Mappings-Limit für maximalen Links-Anschlag
    pan_max = NumericProperty(100.0)       # Mappings-Limit für maximalen Rechts-Anschlag
    font_size = NumericProperty(14)        # Basis-Schriftgröße der Center-Anzeige
    dot_size_ratio = NumericProperty(1.0)  # Verhältnis der Punktstärke zur Ringstärke (1.0 = exakt gleich dick)
    drag_sensitivity = NumericProperty(0.01)  # Drag-Empfindlichkeit (Wertänderung pro Pixel Bewegung)
    drag_axis = OptionProperty('vertical', options=['vertical', 'horizontal'])  # Wischrichtung

    # Farben (RGB)
    active_color = ColorProperty((0.0, 0.9, 0.9))         # Cyan (passend zum Meter)
    inactive_color = ColorProperty((0.08, 0.12, 0.18))    # Dunkles Anthrazit (passend zum Track)
    text_color = ColorProperty((0.85, 0.92, 0.95))        # Textfarbe der Center-Anzeige
    text_opacity = NumericProperty(0.85)                  # Text-Deckkraft

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Reagiert auf alle Property-Änderungen und zeichnet sich neu
        bind_props = [
            'pos', 'size', 'value', 'ring_thickness', 'opening_angle', 
            'active_color', 'inactive_color', 'pan_min', 'pan_max', 
            'font_size', 'text_color', 'text_opacity', 'dot_size_ratio'
        ]
        for prop in bind_props:
            self.bind(**{prop: self._redraw})

    def _redraw(self, *args):
        self.canvas.clear()
        
        # Proportionale Linienstärke basierend auf der aktuellen Widget-Breite (Referenz: 60px)
        scale = self.width / 60.0 if self.width > 0 else 1.0
        lw = self.ring_thickness * scale
        
        # Mittelpunkt des Reglers
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        
        # Durchmesser und Radius unter Berücksichtigung der Strichstärke
        d = min(self.width, self.height) - lw
        r = d / 2.0
        
        # Position für das Kivy-Ellipse-Rechteck
        rx = cx - r
        ry = cy - r
        
        with self.canvas:
            # 1. Inaktiver Hintergrundring (nach unten geöffnet)
            # In Kivy: 0° ist oben (12 Uhr), positive Winkel verlaufen im Uhrzeigersinn.
            # Unterer Mittelpunkt ist bei 180° (6 Uhr).
            # Der offene Bereich unten liegt symmetrisch um 180°: von (180 - opening_angle/2) bis (180 + opening_angle/2).
            # Der gezeichnete Ring startet bei (180 + opening_angle/2) und verläuft im Uhrzeigersinn bis (180 - opening_angle/2 + 360).
            Color(*self.inactive_color)
            angle_start = 180.0 + self.opening_angle / 2.0
            angle_end = angle_start + (360.0 - self.opening_angle)
            Line(ellipse=(rx, ry, d, d, angle_start, angle_end), width=lw)
            
            # 2. Text-Anzeige in der Mitte (C, Lxx, Rxx basierend auf der DAW-Skala)
            val_text = "C"
            rounded_val = 0
            
            if self.value < 0:
                mapped_val = abs(self.value) * abs(self.pan_min)
                rounded_val = int(round(mapped_val))
                if rounded_val > 0:
                    val_text = f"L{rounded_val}"
            elif self.value > 0:
                mapped_val = self.value * self.pan_max
                rounded_val = int(round(mapped_val))
                if rounded_val > 0:
                    val_text = f"R{rounded_val}"

            # 3. Aktiver Bogen (Cyan) oder Center-Punkt (Dot)
            if rounded_val > 0:
                # Aktiver Bogen (Cyan, füllt sich ausgehend von der Mitte nach links/rechts)
                Color(*self.active_color)
                total_active_range = 360.0 - self.opening_angle
                target_angle = self.value * (total_active_range / 2.0)
                
                if self.value < 0:
                    # Links-Bogen: von target_angle (negativ, z.B. -45°) bis 0.0
                    Line(ellipse=(rx, ry, d, d, 360.0 + target_angle, 360.0), width=lw)
                else:
                    # Rechts-Bogen: von 0.0 bis target_angle (positiv, z.B. +45°)
                    Line(ellipse=(rx, ry, d, d, 0.0, target_angle), width=lw)
            else:
                # Center-Dot: Ein gefüllter Punkt genau oben auf 12 Uhr (0°).
                # Um exakt dieselbe Linienstärke und dasselbe Rendering-Verhalten wie für die 
                # L/R-Bögen zu garantieren, zeichnen wir den Punkt als sehr kurzes Segment des Hauptbogens mittels Line.
                Color(*self.active_color)
                if d > 0:
                    delta = (self.dot_size_ratio * lw / (math.pi * d)) * 180.0
                else:
                    delta = 2.0
                Line(ellipse=(rx, ry, d, d, 360.0 - delta, 360.0 + delta), width=lw)

            # 4. Text zeichnen
            scaled_font_size = max(1, int(self.font_size * scale))
            cl = CoreLabel(text=val_text,
                           font_size=scaled_font_size,
                           color=(1, 1, 1, 1),
                           bold=True)
            cl.refresh()
            tex = cl.texture
            tx = cx - tex.size[0] / 2.0
            ty = cy - tex.size[1] / 2.0
            
            # Textfarbe und Opazität anwenden
            tc = self.text_color
            Color(tc[0], tc[1], tc[2], self.text_opacity)
            Rectangle(texture=tex, pos=(tx, ty), size=tex.size)

    # ------------------------------------------------------------------
    # Touch-Steuerung (Dragging ändert den Wert)
    # ------------------------------------------------------------------

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            touch.ud['start_value'] = self.value
            touch.ud['start_x'] = touch.x
            touch.ud['start_y'] = touch.y
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if self.drag_axis == 'vertical':
                delta = touch.y - touch.ud['start_y']
            else:
                delta = touch.x - touch.ud['start_x']
            val = touch.ud['start_value'] + delta * self.drag_sensitivity
            self.value = max(-1.0, min(1.0, val))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)
