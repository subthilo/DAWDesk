import math
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ColorProperty, ListProperty
from kivy.graphics import Color, Line, Rectangle
from kivy.core.text import Label as CoreLabel


class DAWFader(Widget):
    """DAW-Fader Widget – nur Grafik und Zustand.
    Steuerlogik (MIDI, OSC, Automation) kommt von außen.
    Alle visuellen Parameter sind als Kivy-Properties konfigurierbar.
    Das Widget passt sein Aussehen bei Skalierung intelligent an:
    - Vertikal (Höhe) skaliert alles fließend, um Überlappungen zu verhindern.
    - Horizontal (Breite) bleibt das Aussehen konstant (zentriert) und wächst nicht mit,
      schrumpft aber bei Unterschreitung der Referenzbreite, um Überlappungen zu vermeiden.
    """

    value = NumericProperty(-60.0)        # Fader-Position in dB
    meter_value = NumericProperty(-60.0)  # Meter-Pegel in dB (separat)

    # Farben (RGB)
    background_color = ColorProperty((0.12, 0.18, 0.25))
    track_color = ColorProperty((0.08, 0.12, 0.18))
    meter_color = ColorProperty((0.0, 0.9, 0.9))
    meter_background_color = ColorProperty(None, allownone=True)
    knob_color = ColorProperty((0.55, 0.62, 0.68))
    tick_color = ColorProperty((0.6, 0.65, 0.7))
    label_color = ColorProperty((0.75, 0.80, 0.85))
    value_display_color = ColorProperty((0.85, 0.92, 0.95))

    # Opazitäten (0.0 bis 1.0)
    background_opacity = NumericProperty(1.0)
    track_opacity = NumericProperty(1.0)
    meter_opacity = NumericProperty(1.0)
    meter_background_opacity = NumericProperty(None, allownone=True)
    knob_opacity = NumericProperty(1.0)
    tick_opacity = NumericProperty(0.7)
    label_opacity = NumericProperty(0.8)
    value_display_opacity = NumericProperty(1.0)
    foil_opacity = NumericProperty(0.65)

    # Dimensionen (Referenzwerte bei einer Breite von 180px und Höhe von 600px)
    knob_height = NumericProperty(50)
    knob_margin = NumericProperty(4)
    knob_width_ratio = NumericProperty(0.7)
    knob_corner_radius = NumericProperty(10)
    knob_x_offset = NumericProperty(-10)
    knob_line_width = NumericProperty(8)
    track_width = NumericProperty(8)
    meter_width = NumericProperty(6)
    meter_x_offset = NumericProperty(0)
    ticks_x_offset = NumericProperty(0)
    labels_x_offset = NumericProperty(-35)
    default_tick_width = NumericProperty(20)
    tick_line_width = NumericProperty(1.5)
    label_font_size = NumericProperty(18)
    value_font_size = NumericProperty(25)
    value_display_x_offset = NumericProperty(-25)
    foil_padding = NumericProperty(6)

    # dB-Bereich
    db_min = NumericProperty(-60.0)
    db_max = NumericProperty(6.0)
    scale_exponent = NumericProperty(2.0)

    # Skalierungsreferenzen
    reference_width = NumericProperty(180.0)
    reference_height = NumericProperty(600.0)

    # Ticks: Liste von (dB-Wert, Beschriftung, Tick-Breite oder None, Linienstärke oder None)
    ticks = ListProperty([
        (+6,  '+6',  None),
        ( 0,   '0',  None, 3.0),   # 0 dB ist etwas dicker gezeichnet
        (-6,  '-6',  None),
        (-12, '-12', None),
        (-18, '-18', None),
        (-24, '-24', None),
        (-30, '-30', None),
        (-40, '-40', None),
        (-50, '-50', None),
        (-60, '-\u221e',  None),
    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Alle Eigenschaften binden, damit jede Änderung einen Redraw auslöst
        props_to_bind = [
            'pos', 'size', 'value', 'meter_value',
            'background_color', 'track_color', 'meter_color', 'meter_background_color',
            'knob_color', 'tick_color', 'label_color', 'value_display_color',
            'background_opacity', 'track_opacity', 'meter_opacity', 'meter_background_opacity',
            'knob_opacity', 'tick_opacity', 'label_opacity', 'value_display_opacity', 'foil_opacity',
            'knob_height', 'knob_margin', 'knob_width_ratio', 'knob_corner_radius', 'knob_x_offset',
            'knob_line_width', 'track_width', 'meter_width', 'meter_x_offset', 'ticks_x_offset',
            'labels_x_offset', 'default_tick_width', 'tick_line_width', 'label_font_size',
            'value_font_size', 'value_display_x_offset', 'foil_padding',
            'db_min', 'db_max', 'scale_exponent', 'ticks', 'reference_width', 'reference_height'
        ]
        for prop in props_to_bind:
            self.bind(**{prop: self._redraw})

    def get_scales(self):
        """Berechnet die Skalierungsfaktoren für Höhe und Breite.
        - sh: Skaliert die Höhe (fließend nach oben/unten)
        - sw: Skaliert die Breite. Ist nach oben bei 1.0 gedeckelt, damit Elemente
              bei breiteren Widgets nicht wachsen (Hintergrund dehnt sich nur),
              schrumpft aber unter 1.0, wenn das Widget schmaler als 180px wird,
              um Überlappungen zu verhindern.
        """
        sh = self.height / self.reference_height if self.reference_height > 0 else 1.0
        sw = self.width / self.reference_width if self.reference_width > 0 else 1.0
        sw = min(1.0, sw)
        return sh, sw

    def get_color(self, name):
        """Kombiniert den RGB-Farbwert mit der zugehörigen Opazität aus den Properties."""
        color = getattr(self, name)
        if color is None:
            if name == 'meter_background_color':
                color = self.background_color
            else:
                color = (1.0, 1.0, 1.0)

        opacity_name = name.replace('_color', '_opacity')
        opacity = getattr(self, opacity_name)
        if opacity is None:
            if opacity_name == 'meter_background_opacity':
                opacity = self.background_opacity
            else:
                opacity = 1.0
        return (color[0], color[1], color[2], opacity)

    # ------------------------------------------------------------------
    # Mapping-Helfer
    # ------------------------------------------------------------------

    def db_to_y(self, db):
        """dB-Wert → Y-Pixel-Position (logarithmische Kurve)."""
        sh, _ = self.get_scales()
        db = max(self.db_min, min(self.db_max, db))
        ratio = (db - self.db_min) / (self.db_max - self.db_min)
        curved = ratio ** self.scale_exponent
        pad = (self.knob_height / 2 + self.knob_line_width / 2 + self.knob_margin) * sh
        return (self.y + pad) + curved * (self.height - 2 * pad)

    def y_to_db(self, y):
        """Y-Pixel-Position → dB-Wert (inverse logarithmische Kurve)."""
        sh, _ = self.get_scales()
        pad = (self.knob_height / 2 + self.knob_line_width / 2 + self.knob_margin) * sh
        usable = self.height - 2 * pad
        if usable <= 0:
            return self.db_min
        curved = (y - self.y - pad) / usable
        curved = max(0.0, min(1.0, curved))
        ratio = curved ** (1.0 / self.scale_exponent) if self.scale_exponent != 0 else curved
        return self.db_min + ratio * (self.db_max - self.db_min)

    # ------------------------------------------------------------------
    # Zeichnen
    # ------------------------------------------------------------------

    def _redraw(self, *args):
        self.canvas.clear()
        sh, sw = self.get_scales()
        cx = self.x + self.width / 2.0
        mx = cx + self.meter_x_offset * sw

        with self.canvas:
            # 1) Hintergrund
            Color(*self.get_color('background_color'))
            Rectangle(pos=self.pos, size=self.size)

            # 2) Track (vertikale Rille)
            Color(*self.get_color('track_color'))
            tw = self.track_width * sw
            Rectangle(pos=(mx - tw / 2, self.y), size=(tw, self.height))

            # 3) Meter-Hintergrund (der Kanal, in dem die Pegelanzeige verläuft - über die gesamte Höhe)
            bg_w = max(self.track_width * sw, self.meter_width * sw)
            Color(*self.get_color('meter_background_color'))
            Rectangle(pos=(mx - bg_w / 2, self.y),
                      size=(bg_w, self.height))

            # 3.5) Meter (Cyan-Balken von unten bis meter_value)
            m_bot = self.db_to_y(self.db_min)
            m_top = self.db_to_y(self.meter_value)
            if m_top > m_bot:
                Color(*self.get_color('meter_color'))
                mw = self.meter_width * sw
                Rectangle(pos=(mx - mw / 2, m_bot),
                          size=(mw, m_top - m_bot))

            # 4) Knob (unter der Folie gezeichnet)
            self._draw_knob(mx, sh, sw)

            # 5) Die durchsichtige Folie (symmetrisch um die Labels gezeichnet, gleiche Farbe wie Hintergrund)
            max_label_w = 0
            scaled_label_font_size = max(1, int(self.label_font_size * min(sh, sw)))
            for item in self.ticks:
                label_text = item[1]
                cl = CoreLabel(text=label_text, font_size=scaled_label_font_size)
                cl.refresh()
                max_label_w = max(max_label_w, cl.texture.size[0])

            foil_cx = mx + self.labels_x_offset * sw
            pad = self.foil_padding * sw
            fw = max_label_w + 2 * pad
            fx = foil_cx - fw / 2

            bg_col = self.get_color('background_color')
            Color(bg_col[0], bg_col[1], bg_col[2], self.foil_opacity)
            Rectangle(pos=(fx, self.y), size=(fw, self.height))

            # 6) Ticks + Labels (auf der Folie)
            self._draw_ticks(mx, sh, sw)

            # 7) Wertanzeige (dB rechts neben dem Knob)
            self._draw_value_display(mx, sh, sw)

    def _draw_ticks(self, mx, sh, sw):
        """Zeichnet alle Tick-Markierungen und dB-Labels relativ zum Meter."""
        scaled_label_font_size = max(1, int(self.label_font_size * min(sh, sw)))
        for item in self.ticks:
            db_val = item[0]
            label_text = item[1]
            tick_w = item[2] if len(item) > 2 else None
            tick_lw = item[3] if len(item) > 3 else None

            tick_y = self.db_to_y(db_val)
            tw_act = (tick_w * sw) if tick_w is not None else (self.default_tick_width * sw)
            tlw_act = (tick_lw * min(sh, sw)) if tick_lw is not None else (self.tick_line_width * min(sh, sw))

            # Tick-Linie
            Color(*self.get_color('tick_color'))
            t_center = mx + self.ticks_x_offset * sw
            t_start = t_center - tw_act / 2
            t_end = t_center + tw_act / 2
            Line(points=[t_start, tick_y, t_end, tick_y],
                 width=tlw_act)

            # Label
            cl = CoreLabel(text=label_text,
                           font_size=scaled_label_font_size,
                           color=(1, 1, 1, 1))
            cl.refresh()
            tex = cl.texture
            lx = mx + self.labels_x_offset * sw - tex.size[0] / 2
            ly = tick_y - tex.size[1] / 2
            Color(*self.get_color('label_color'))
            Rectangle(texture=tex, pos=(lx, ly), size=tex.size)

    def _draw_knob(self, mx, sh, sw):
        """Zeichnet den Fader-Knob als C-Form (rechts offen) – ein Linienzug."""
        kh = self.knob_height * sh
        kw = (self.reference_width * self.knob_width_ratio) * sw
        ky = self.db_to_y(self.value) - kh / 2
        kx = mx - kw / 2 + self.knob_x_offset * sw
        r = min(self.knob_corner_radius * min(sh, sw), kh / 2)
        lw = self.knob_line_width * min(sh, sw)
        num_seg = 16

        points = [kx + kw, ky + kh]

        # Viertelkreis oben-links
        for i in range(num_seg + 1):
            angle = math.radians(90 + i * 90.0 / num_seg)
            points.append((kx + r) + r * math.cos(angle))
            points.append((ky + kh - r) + r * math.sin(angle))

        # Viertelkreis unten-links
        for i in range(num_seg + 1):
            angle = math.radians(180 + i * 90.0 / num_seg)
            points.append((kx + r) + r * math.cos(angle))
            points.append((ky + r) + r * math.sin(angle))

        points.extend([kx + kw, ky])

        Color(*self.get_color('knob_color'))
        Line(points=points, width=lw)

    def _draw_value_display(self, mx, sh, sw):
        """Zeichnet den aktuellen dB-Wert in der C-Öffnung."""
        kw = (self.reference_width * self.knob_width_ratio) * sw
        knob_right = mx - kw / 2 + self.knob_x_offset * sw + kw

        val_text = "-\u221e" if self.value <= self.db_min else f"{self.value:.1f}"
        scaled_value_font_size = max(1, int(self.value_font_size * min(sh, sw)))
        vl = CoreLabel(text=val_text,
                       font_size=scaled_value_font_size,
                       color=(1, 1, 1, 1),
                       bold=True)
        vl.refresh()
        vt = vl.texture
        vx = knob_right - vt.size[0] - self.value_display_x_offset * sw
        vy = self.db_to_y(self.value) - vt.size[1] / 2
        Color(*self.get_color('value_display_color'))
        Rectangle(texture=vt, pos=(vx, vy), size=vt.size)

    # ------------------------------------------------------------------
    # Touch-Handling
    # ------------------------------------------------------------------

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            start_knob_y = self.db_to_y(self.value)
            touch.ud['knob_offset_y'] = touch.y - start_knob_y
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            target_knob_y = touch.y - touch.ud.get('knob_offset_y', 0)
            self.value = self.y_to_db(target_knob_y)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)
