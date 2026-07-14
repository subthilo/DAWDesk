import time
import math
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty, ColorProperty, ListProperty, BooleanProperty
from kivy.graphics import Color, Rectangle, Line, SmoothLine, Ellipse
from kivy.core.text import Label as CoreLabel
from kivy.clock import Clock

class DAWChannelStrip(Widget):
    """
    High-Performance Single-Widget Channel Strip.
    Zeichnet Pan, Fader, Pegel und Text direkt auf seinen Canvas, um
    den Kivy-Widget-Overhead zu vermeiden. Bietet maximale FPS auf EGLFS.
    """
    track_name = StringProperty("Spur")
    channel_id = NumericProperty(0)   # Kanal-Index 1–12, wird von main.py gesetzt
    value = NumericProperty(-60.0)
    meter_value = NumericProperty(-60.0)
    pan = NumericProperty(0.0)  # -1.0 bis 1.0 (Pan-Bereich wie im alten Widget)
    
    pan_min = NumericProperty(-100.0)
    pan_max = NumericProperty(100.0)
    db_min = NumericProperty(-60.0)
    db_max = NumericProperty(6.0)

    # --- PAN PROPERTIES ---
    pan_ring_thickness = NumericProperty(4.0)
    pan_opening_angle = NumericProperty(60.0)
    c_pan_inactive = ColorProperty((0.3, 0.3, 0.3, 1))
    c_pan_active = ColorProperty((0.0, 0.9, 0.9, 1))
    pan_font_size = NumericProperty(20)

    # --- Interner State ---
    _ui_ready = BooleanProperty(False)
    _ignore_osc_send = BooleanProperty(False)
    is_touched = BooleanProperty(False)
    is_solo = BooleanProperty(False)
    is_muted = BooleanProperty(False)

    # --- FADER PROPERTIES ---
    c_bg = ColorProperty((0.08, 0.12, 0.18, 1))
    c_track = ColorProperty((0.04, 0.06, 0.10, 1))
    track_color = ColorProperty((0.55, 0.62, 0.68, 1)) # Default fader cap / track color
    c_meter = ColorProperty((0.0, 0.9, 0.9, 0.8))
    c_text = ColorProperty((0.85, 0.92, 0.95, 1))
    c_tick = ColorProperty((0.4, 0.4, 0.4, 1))
    
    fader_ticks = ListProperty([
        (6.0, "+6"), (0.0, "0"), (-5.0, "-5"), (-10.0, "-10"), 
        (-20.0, "-20"), (-30.0, "-30"), (-40.0, "-40"), (-60.0, "-\u221e")
    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._fader_rect = None
        self._meter_rect = None
        self._pan_line = None
        self._pan_value_rect = None
        self._fader_value_rect = None
        self._text_cache = {}
        
        self._name_rect = None
        self._color_fader = None
        self._mute_overlay = None
        self._mute_overlay_color = None
        
        # Gesture detection state (fader)
        self._last_tap_time = 0
        self._long_press_event = None
        self._touch_moved = False
        # Gesture detection state (label – global defeat)
        self._label_last_tap_time = 0
        self._label_long_press_event = None
        
        self.bind(pos=self._trigger_rebuild, size=self._trigger_rebuild)
        self.bind(track_name=self._update_dynamic, track_color=self._update_dynamic, value=self._update_dynamic, pan=self._update_dynamic)
        self.bind(is_solo=self._update_dynamic, is_muted=self._update_dynamic)
        self.bind(meter_value=self._update_meter)

    def _trigger_rebuild(self, *args):
        Clock.unschedule(self._rebuild_canvas)
        Clock.schedule_once(self._rebuild_canvas, 0)

    def _get_geometry(self):
        """Berechnet die internen Bereiche"""
        x, y = self.x, self.y
        w, h = self.width, self.height
        
        pad = min(10, w * 0.1)
        lbl_h = 40
        pan_h = w  # Pan-Bereich ist quadratisch oben
        fader_h = h - lbl_h - pan_h
        
        return {
            'pad': pad,
            'lbl_y': y, 'lbl_h': lbl_h,
            'pan_y': y + h - pan_h, 'pan_h': pan_h,
            'fader_y': y + lbl_h, 'fader_h': fader_h,
            'center_x': x + w / 2,
            'w': w, 'h': h, 'x': x, 'y': y
        }

    def _db_to_y(self, db, geo):
        db = max(self.db_min, min(self.db_max, db))
        ratio = (db - self.db_min) / (self.db_max - self.db_min)
        curved = ratio ** 2.0
        
        knob_h = 40
        usable_h = geo['fader_h'] - knob_h - 20
        return geo['fader_y'] + 10 + knob_h/2 + curved * usable_h

    def _y_to_db(self, py, geo):
        knob_h = 40
        usable_h = geo['fader_h'] - knob_h - 20
        if usable_h <= 0: return self.db_min
        
        curved = (py - geo['fader_y'] - 10 - knob_h/2) / usable_h
        curved = max(0.0, min(1.0, curved))
        ratio = curved ** 0.5
        return self.db_min + ratio * (self.db_max - self.db_min)
        
    def _get_cached_text(self, text, font_size, bold=False):
        cache_key = (text, int(font_size), bold)
        if cache_key not in self._text_cache:
            lbl = CoreLabel(text=text, font_size=int(font_size), color=(1, 1, 1, 1), bold=bold)
            lbl.refresh()
            self._text_cache[cache_key] = lbl.texture
        return self._text_cache[cache_key]
        
    def _get_kivy_arc_point(self, cx, cy, radius, angle_deg):
        # Kivy 0° is 12 o'clock, growing clockwise.
        # Math 0° is 3 o'clock, growing counter-clockwise.
        math_angle_rad = math.radians(90.0 - angle_deg)
        x = cx + radius * math.cos(math_angle_rad)
        y = cy + radius * math.sin(math_angle_rad)
        return x, y

    def _rebuild_canvas(self, dt):
        if self.width <= 0 or self.height <= 0:
            return
            
        geo = self._get_geometry()
        self.canvas.before.clear()
        self.canvas.clear()
        self.canvas.after.clear()
        
        with self.canvas.before:
            Color(*self.c_bg)
            Rectangle(pos=self.pos, size=self.size)
            
            # --- 0. SEPARATOREN ---
            Color(0.2, 0.2, 0.2, 1)  # Dezentes Grau für Trennlinien
            margin = 15  # Linien gehen nicht über die volle Breite
            # Linie zwischen Name (unten) und Fader
            Line(points=[geo['x'] + margin, geo['fader_y'], geo['x'] + geo['w'] - margin, geo['fader_y']], width=1.0)
            # Linie zwischen Fader und Pan (oben)
            Line(points=[geo['x'] + margin, geo['pan_y'], geo['x'] + geo['w'] - margin, geo['pan_y']], width=1.0)
            
            # --- 1. SPURNAME ---
            Color(*self.c_text)
            self._name_rect = Rectangle(pos=(0,0), size=(0,0))

            # --- 2. PAN HINTERGRUND ---
            if self.pan > -900:
                # Inaktiver Ring
                lw = self.pan_ring_thickness
                d = geo['pan_h'] * 0.8
                rx = geo['center_x'] - d / 2
                ry = geo['pan_y'] + (geo['pan_h'] - d) / 2
                
                Color(*self.c_pan_inactive)
                half_open = self.pan_opening_angle / 2.0
                a_start = 180.0 + half_open
                a_end = 540.0 - half_open
                SmoothLine(ellipse=(rx, ry, d, d, a_start, a_end, 128), width=lw, cap='none')
                
                # Manuelle runde Kappen für den inaktiven Ring
                cx_pan = geo['center_x']
                cy_pan = geo['pan_y'] + geo['pan_h']/2.0
                r_pan = d / 2.0
                
                x1, y1 = self._get_kivy_arc_point(cx_pan, cy_pan, r_pan, a_start)
                Ellipse(pos=(x1 - lw, y1 - lw), size=(lw*2, lw*2), segments=64)
                
                x2, y2 = self._get_kivy_arc_point(cx_pan, cy_pan, r_pan, a_end)
                Ellipse(pos=(x2 - lw, y2 - lw), size=(lw*2, lw*2), segments=64)
                
                # Center Dot
                dot_d = lw * 2.0
                SmoothLine(ellipse=(geo['center_x'] - dot_d/2, geo['pan_y'] + geo['pan_h']/2 - dot_d/2, dot_d, dot_d, 0, 360, 64), width=dot_d/2)


            # --- 3. FADER HINTERGRUND & TICKS ---
            track_w = 12
            meter_x = geo['center_x'] - track_w/2
            
            Color(*self.c_bg)
            Rectangle(pos=(meter_x, geo['fader_y'] + 10), size=(track_w, geo['fader_h'] - 20))
        with self.canvas:
            # --- 4. PAN AKTIV & TEXT ---
            Color(*self.c_pan_active)
            self._pan_line = SmoothLine(ellipse=(rx, ry, d, d, 0, 0, 128), width=lw, cap='none')
            self._pan_active_cap1 = Ellipse(pos=(0, 0), size=(0, 0), segments=64)
            self._pan_active_cap2 = Ellipse(pos=(0, 0), size=(0, 0), segments=64)
            
            Color(*self.c_text)
            self._pan_value_rect = Rectangle(pos=(0,0), size=(0,0))
            
            # --- 5. FADER METER ---
            Color(*self.c_meter)
            self._meter_rect = Rectangle(pos=(meter_x + 1, geo['fader_y'] + 10), size=(track_w - 2, 0))
            
            # --- 6. FADER KAPPE (C-Form / Eine Seite offen) & WERT ---
            self._color_fader = Color(*self.track_color)
            # Verwende eine Linie für die Kappe anstelle eines gefüllten Rechtecks
            self._fader_line = Line(points=[], width=2.0, cap='none', joint='round')
            self._fader_cap_top = Ellipse(pos=(0, 0), size=(4, 4), segments=64)
            self._fader_cap_bot = Ellipse(pos=(0, 0), size=(4, 4), segments=64)
            
            Color(*self.c_text)
            self._fader_value_rect = Rectangle(pos=(0, 0), size=(0, 0))

        with self.canvas.after:
            # Maximale Breite der Texte dynamisch berechnen, um den Streifen EXAKT anzupassen
            max_tex_w = 0
            for db_val, label_text in self.fader_ticks:
                tex = self._get_cached_text(label_text, 10, bold=False)
                if tex.width > max_tex_w:
                    max_tex_w = tex.width

            # --- FOIL (Transparentes Band hinter den Ticks, aber über dem Fader) ---
            Color(self.c_bg[0], self.c_bg[1], self.c_bg[2], 0.5)
            # Padding für den Streifen, damit die Zahlen nicht eingezwängt wirken
            pad_x = 4
            # Da die Texte rechtsbündig an meter_x - 12 enden, beginnt der Streifen bei meter_x - 12 - max_tex_w - pad_x
            # Oben und unten leicht einrücken, damit die Separatoren nicht überdeckt werden
            foil_y = geo['fader_y'] + 5
            foil_h = max(0, geo['fader_h'] - 10)
            Rectangle(pos=(meter_x - 12 - max_tex_w - pad_x, foil_y), size=(max_tex_w + 2 * pad_x, foil_h))
            
            # Ticks (Linien zentriert über dem Meter, Zahlen links)
            for db_val, label_text in self.fader_ticks:
                tick_y = self._db_to_y(db_val, geo)
                
                # Linie mittig über den Meter-Schlitz
                Color(*self.c_tick)
                Line(points=[geo['center_x'] - 12, tick_y, geo['center_x'] + 12, tick_y], width=1.0)
                
                # Text links daneben auf der Folie
                tex = self._get_cached_text(label_text, 10, bold=False)
                Color(*self.c_text)
                Rectangle(texture=tex, pos=(meter_x - 12 - tex.width, tick_y - tex.height/2), size=tex.size)

            # --- MUTE OVERLAY (darkens entire channel when muted, drawn LAST to cover everything) ---
            self._mute_overlay_color = Color(0, 0, 0, 0)  # Initially invisible
            self._mute_overlay = Rectangle(pos=self.pos, size=self.size)

        # Precache alle möglichen Pan- und Fader-Werte
        self._precache_texts()
        self._update_dynamic()

    def _precache_texts(self):
        for pan_val in range(-100, 101):
            if pan_val < 0: val_text = f"L{abs(pan_val)}"
            elif pan_val > 0: val_text = f"R{pan_val}"
            else: val_text = "C"
            self._get_cached_text(val_text, self.pan_font_size, bold=True)
            
        for db_int in range(int(self.db_min * 10), int(self.db_max * 10) + 1):
            self._get_cached_text(f"{db_int / 10.0:.1f}", 12, bold=True)
        self._get_cached_text("-\u221e", 12, bold=True)

    def _update_dynamic(self, *args):
        if not self._meter_rect:
            return
            
        geo = self._get_geometry()
        
        # 0. Update Name & Color
        if self._name_rect:
            tex = self._get_cached_text(self.track_name, max(10, geo['lbl_h'] * 0.4), bold=True)
            if tex:
                self._name_rect.texture = tex
                self._name_rect.size = tex.size
                self._name_rect.pos = (geo['center_x'] - tex.width / 2, geo['lbl_y'] + geo['lbl_h'] / 2 - tex.height / 2)
        
        if self._color_fader:
            self._color_fader.rgba = self.track_color
        
        # Mute overlay: darken entire channel
        if self._mute_overlay:
            if self.is_muted:
                self._mute_overlay_color.rgba = (0, 0, 0, 0.65)
                self._mute_overlay.pos = self.pos
                self._mute_overlay.size = self.size
            else:
                self._mute_overlay_color.rgba = (0, 0, 0, 0)
                self._mute_overlay.size = (0, 0)
        
        # 1. Update Pan
        d = geo['pan_h'] * 0.8
        rx = geo['center_x'] - d / 2
        ry = geo['pan_y'] + (geo['pan_h'] - d) / 2
        
        # Pan ist bei uns im Bereich -1.0 bis 1.0 intern
        mapped_pan = self.pan
        
        if mapped_pan <= -900:
            self._pan_line.ellipse = (0, 0, 0, 0, 0, 0, 32)
            self._pan_active_cap1.size = (0, 0)
            self._pan_active_cap2.size = (0, 0)
            self._pan_value_rect.size = (0, 0)
        else:
            rounded_val = 0
            val_text = "C"
            if mapped_pan < 0:
                rounded_val = int(round(abs(mapped_pan) * abs(self.pan_min)))
                if rounded_val > 0: val_text = f"L{rounded_val}"
            elif mapped_pan > 0:
                rounded_val = int(round(mapped_pan * self.pan_max))
                if rounded_val > 0: val_text = f"R{rounded_val}"
                
            if rounded_val > 0:
                total_active_range = 360.0 - self.pan_opening_angle
                target_angle = mapped_pan * (total_active_range / 2.0)
                
                R = d / 2.0
                cx = geo['center_x']
                cy = geo['pan_y'] + geo['pan_h']/2.0
                lw = self.pan_ring_thickness
                
                # Center cap at 0 degrees
                cx0, cy0 = self._get_kivy_arc_point(cx, cy, R, 0.0)
                self._pan_active_cap1.pos = (cx0 - lw, cy0 - lw)
                self._pan_active_cap1.size = (lw*2, lw*2)
                
                if mapped_pan < 0:
                    self._pan_line.ellipse = (rx, ry, d, d, 360.0 + target_angle, 360.0, 128)
                    ax, ay = self._get_kivy_arc_point(cx, cy, R, 360.0 + target_angle)
                else:
                    self._pan_line.ellipse = (rx, ry, d, d, 0.0, target_angle, 128)
                    ax, ay = self._get_kivy_arc_point(cx, cy, R, target_angle)
                    
                self._pan_active_cap2.pos = (ax - lw, ay - lw)
                self._pan_active_cap2.size = (lw*2, lw*2)
            else:
                self._pan_line.ellipse = (rx, ry, d, d, 359.0, 361.0, 32)
                self._pan_active_cap1.size = (0, 0)
                self._pan_active_cap2.size = (0, 0)
                
            tex = self._get_cached_text(val_text, self.pan_font_size, bold=True)
            self._pan_value_rect.texture = tex
            self._pan_value_rect.size = tex.size
            self._pan_value_rect.pos = (geo['center_x'] - tex.width/2, geo['pan_y'] + geo['pan_h']/2 - tex.height/2)

        # 2. Update Fader Kappe (C-Form)
        fy = self._db_to_y(self.value, geo)
        fh = 40
        
        # Kappe reicht von links bis zur rechten Meterkante
        track_w = 12
        meter_x = geo['center_x'] - track_w/2
        
        # Linker Rand der Kappe (schmaler für 12 Kanäle)
        kx = meter_x - 35 
        kw = 35 + track_w + 20  # Kappe schmaler gemacht
        ky = fy - fh/2
        
        # C-Shape mit abgerundeten Ecken auf der linken Seite und runden Enden rechts
        r = 6  # Radius der Ecken
        pts = [kx + kw, ky + fh, kx + r, ky + fh]
        
        # Obere linke Ecke (feiner gerundet mit 15 Segmenten)
        corner_segments = 15
        for i in range(1, corner_segments):
            angle = math.radians(90 + i * (90/corner_segments))
            pts.extend([kx + r + r * math.cos(angle), ky + fh - r + r * math.sin(angle)])
            
        # Untere linke Ecke (feiner gerundet mit 15 Segmenten)
        for i in range(1, corner_segments):
            angle = math.radians(180 + i * (90/corner_segments))
            pts.extend([kx + r + r * math.cos(angle), ky + r + r * math.sin(angle)])
            
        pts.extend([kx + kw, ky])
        self._fader_line.points = pts
        
        # Explizite runde Enden (Caps) an den Linienenden rechts
        # Die Linienbreite ist 2.0 (also Durchmesser 4.0)
        cap_size = 4.0
        # Das obere Ende der Linie liegt bei kx + kw, ky + fh
        self._fader_cap_top.pos = (kx + kw - cap_size/2, ky + fh - cap_size/2)
        # Das untere Ende der Linie liegt bei kx + kw, ky
        self._fader_cap_bot.pos = (kx + kw - cap_size/2, ky - cap_size/2)
        
        # Update Fader Wert (in der Öffnung der C-Form)
        v_text = "-\u221e" if self.value <= self.db_min else f"{self.value:.1f}"
        v_tex = self._get_cached_text(v_text, 12, bold=True)
        self._fader_value_rect.texture = v_tex
        self._fader_value_rect.size = v_tex.size
        # Zahl noch ein kleines bisschen weiter nach rechts geschoben (+18 statt +15)
        self._fader_value_rect.pos = (kx + kw - v_tex.width + 18, fy - v_tex.height/2)
        
        # 3. Update Meter (initial)
        self._update_meter()

    def _update_meter(self, *args):
        """Lightweight meter-only update – only changes the meter rect height."""
        if not self._meter_rect:
            return
        if self.meter_value <= self.db_min:
            self._meter_rect.size = (self._meter_rect.size[0], 0)
            return
        geo = self._get_geometry()
        my_bot = geo['fader_y'] + 10
        my_top = self._db_to_y(self.meter_value, geo)
        self._meter_rect.size = (self._meter_rect.size[0], max(0, my_top - my_bot))

    # --- Touch Handling ---
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
            
        geo = self._get_geometry()
        
        if touch.y >= geo['pan_y']:
            touch.grab(self)
            self.is_touched = True
            touch.ud['active_control'] = 'pan'
            touch.ud['start_y'] = touch.y
            touch.ud['start_pan'] = self.pan
            return True
            
        if touch.y >= geo['fader_y'] and touch.y < geo['pan_y']:
            touch.grab(self)
            self.is_touched = True
            touch.ud['active_control'] = 'fader'
            touch.ud['touch_start_x'] = touch.x
            touch.ud['touch_start_y'] = touch.y
            self._touch_moved = False
            fy = self._db_to_y(self.value, geo)
            touch.ud['offset_y'] = touch.y - fy
            
            # Double-tap detection (Solo)
            now = time.monotonic()
            if now - self._last_tap_time < 0.35:
                self._send_solo_osc()
                self._last_tap_time = 0  # Reset to prevent triple-tap
                touch.ungrab(self)
                self.is_touched = False
                return True
            self._last_tap_time = now
            
            # Long-press detection (Mute) – schedule check
            self._long_press_event = Clock.schedule_once(self._on_long_press, 0.5)
            return True
        
        # --- LABEL AREA (global defeat gestures) ---
        if touch.y < geo['fader_y']:
            touch.grab(self)
            touch.ud['active_control'] = 'label'
            
            # Double-tap detection (Global Solo Defeat)
            now = time.monotonic()
            if now - self._label_last_tap_time < 0.35:
                self._send_solo_defeat_osc()
                self._label_last_tap_time = 0
                touch.ungrab(self)
                return True
            self._label_last_tap_time = now
            
            # Long-press detection (Global Mute Defeat)
            self._label_long_press_event = Clock.schedule_once(self._on_label_long_press, 0.5)
            return True
            
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            geo = self._get_geometry()
            ctrl = touch.ud.get('active_control')
            
            if ctrl == 'pan':
                dy = touch.y - touch.ud.get('start_y', touch.y)
                delta_val = (dy / 150.0) * 2.0
                new_val = touch.ud.get('start_pan', 0.0) + delta_val
                self.pan = max(-1.0, min(1.0, new_val))
                self._send_pan_osc()
            elif ctrl == 'fader':
                # Check if finger moved beyond threshold (10px) before treating as drag
                dx = touch.x - touch.ud.get('touch_start_x', touch.x)
                dy = touch.y - touch.ud.get('touch_start_y', touch.y)
                dist = (dx*dx + dy*dy) ** 0.5
                
                if dist > 10:
                    self._touch_moved = True
                    # Cancel long-press once real movement detected
                    if self._long_press_event:
                        self._long_press_event.cancel()
                        self._long_press_event = None
                    target_y = touch.y - touch.ud.get('offset_y', 0)
                    self.value = self._y_to_db(target_y, geo)
                    self._send_volume_osc()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            ctrl = touch.ud.get('active_control')
            # Cancel any pending long-press
            if self._long_press_event:
                self._long_press_event.cancel()
                self._long_press_event = None
            if self._label_long_press_event:
                self._label_long_press_event.cancel()
                self._label_long_press_event = None
            # Re-send final value to ensure sync with Cubase.
            if ctrl == 'fader' and self._touch_moved:
                self._send_volume_osc()
            elif ctrl == 'pan':
                self._send_pan_osc()
            self.is_touched = False
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def _on_long_press(self, dt):
        """Called when user holds finger on fader for 500ms without moving."""
        if not self._touch_moved:
            self._send_mute_osc()

    def _on_label_long_press(self, dt):
        """Called when user holds finger on label for 500ms → Global Mute Defeat."""
        self._send_mute_defeat_osc()

    # --- OSC Sending ---
    def _send_volume_osc(self):
        """Sendet nur den aktuellen Fader-Wert an den Broker."""
        if self._ignore_osc_send:
            return
        app = App.get_running_app()
        if not app or not getattr(app, 'osc_client', None) or self.channel_id == 0:
            return
        # dB (-60..+6) → 0.0..1.0
        vol = max(0.0, min(1.0, (self.value - self.db_min) / (self.db_max - self.db_min)))
        try:
            app.osc_client.send_message(
                f'/ui/{app.controller_id}/fader/{self.channel_id}/volume', vol
            )
        except Exception:
            pass

    def _send_pan_osc(self):
        """Sendet nur den aktuellen Pan-Wert an den Broker."""
        if self._ignore_osc_send:
            return
        app = App.get_running_app()
        if not app or not getattr(app, 'osc_client', None) or self.channel_id == 0:
            return
        pan = (self.pan + 1.0) / 2.0
        try:
            app.osc_client.send_message(
                f'/ui/{app.controller_id}/fader/{self.channel_id}/pan', pan
            )
        except Exception:
            pass

    def _send_solo_osc(self):
        """Sendet Solo-Toggle an den Broker."""
        app = App.get_running_app()
        if not app or not getattr(app, 'osc_client', None) or self.channel_id == 0:
            return
        try:
            app.osc_client.send_message(
                f'/ui/{app.controller_id}/fader/{self.channel_id}/solo', 1.0
            )
        except Exception:
            pass

    def _send_mute_osc(self):
        """Sendet Mute-Toggle an den Broker."""
        app = App.get_running_app()
        if not app or not getattr(app, 'osc_client', None) or self.channel_id == 0:
            return
        try:
            app.osc_client.send_message(
                f'/ui/{app.controller_id}/fader/{self.channel_id}/mute', 1.0
            )
        except Exception:
            pass

    def _send_solo_defeat_osc(self):
        """Sendet Global Solo Defeat an den Broker."""
        app = App.get_running_app()
        if not app or not getattr(app, 'osc_client', None):
            return
        try:
            app.osc_client.send_message(
                f'/ui/{app.controller_id}/global/solo_defeat', 1.0
            )
        except Exception:
            pass

    def _send_mute_defeat_osc(self):
        """Sendet Global Mute Defeat an den Broker."""
        app = App.get_running_app()
        if not app or not getattr(app, 'osc_client', None):
            return
        try:
            app.osc_client.send_message(
                f'/ui/{app.controller_id}/global/mute_defeat', 1.0
            )
        except Exception:
            pass
