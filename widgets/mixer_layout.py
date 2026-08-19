import time
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

class MixerLayout(BoxLayout):
    """
    MixerLayout – Parent Container aller DAWChannelStrips.
    Erkennt Edge-Entry und Horizontal-Swipes über Kanalgrenzen hinweg
    und löst pro überstrichenem Kanal genau 1 Nudge-Impuls aus.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._highlight_rect = None
        self._highlight_color = None
        self._highlight_event = None

    def start_nudge(self, touch):
        """Wird vom ChannelStrip aufgerufen, wenn eine Nudge-Geste (horizontal swipe) erkannt wurde."""
        ch_idx = self._get_channel_index_at_x(touch.x)
        touch.ud['last_ch_idx'] = ch_idx
        self._highlight_channel(ch_idx)

    def process_nudge_move(self, touch):
        """Wird vom ChannelStrip aufgerufen, während eines Nudge-Swipes."""
        current_ch_idx = self._get_channel_index_at_x(touch.x)
        last_ch_idx = touch.ud.get('last_ch_idx', current_ch_idx)

        if current_ch_idx != last_ch_idx:
            # Invertierte Richtung für natürliches Scrollen (Inhalt folgt dem Finger)
            steps = last_ch_idx - current_ch_idx
            self._trigger_nudge(steps)
            touch.ud['last_ch_idx'] = current_ch_idx
            self._highlight_channel(current_ch_idx)

    def end_nudge(self, touch):
        """Wird vom ChannelStrip aufgerufen, wenn der Nudge-Swipe endet."""
        self._clear_highlight()

    def _get_channel_index_at_x(self, x):
        """Berechnet den 0-basierten Kanal-Index von links nach rechts."""
        num_children = len(self.children)
        if num_children == 0 or self.width <= 0:
            return 0
        rel_x = max(0.0, min(float(self.width - 1), x - self.x))
        ch_width = self.width / float(num_children)
        idx = int(rel_x / ch_width)
        return max(0, min(num_children - 1, idx))

    def _trigger_nudge(self, steps):
        app = App.get_running_app()
        if hasattr(app, 'osc_client') and app.osc_client and getattr(app, 'controller_id', None):
            try:
                app.osc_client.send_message(f"/ui/{app.controller_id}/nudge", steps)
            except Exception as e:
                print(f"Error sending swipe nudge: {e}")

    def _highlight_channel(self, ch_idx):
        """Optisches Feedback: Hebt den aktuell überstrichenen Kanal leicht hervor."""
        # Kivy horizontal BoxLayout speichert children in umgekehrter Reihenfolge (rechts nach links)
        strips = list(reversed(self.children))
        if 0 <= ch_idx < len(strips):
            strip = strips[ch_idx]
            if not self._highlight_rect:
                with self.canvas.after:
                    self._highlight_color = Color(0.0, 0.9, 0.9, 0.25)  # Cyan Schein
                    self._highlight_rect = Rectangle(pos=strip.pos, size=strip.size)
            else:
                self._highlight_color.rgba = (0.0, 0.9, 0.9, 0.25)
                self._highlight_rect.pos = strip.pos
                self._highlight_rect.size = strip.size

            if self._highlight_event:
                self._highlight_event.cancel()
            self._highlight_event = Clock.schedule_once(self._clear_highlight, 0.25)

    def _clear_highlight(self, *args):
        if self._highlight_color:
            self._highlight_color.a = 0.0
