from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle

class AutoRepeatButton(Button):
    def __init__(self, steps=1, action_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.steps = steps
        self.action_callback = action_callback
        self._repeat_event = None
        
        # Style
        self.background_normal = ''
        self.background_color = (0.2, 0.25, 0.3, 1)
        self.color = (0.9, 0.9, 0.9, 1)
        self.font_size = 20
        self.bold = True
        
        # Bind native Kivy events for touch
        self.bind(on_press=self.start_action)
        self.bind(on_release=self.stop_action)

    def start_action(self, *args):
        self.background_color = (0.3, 0.4, 0.5, 1)
        if self.action_callback:
            self.action_callback(self.steps)
        self._repeat_event = Clock.schedule_once(self.start_repeat, 0.4)

    def start_repeat(self, dt):
        self._repeat_event = Clock.schedule_interval(lambda d: self.action_callback(self.steps), 0.25)

    def stop_action(self, *args):
        if self._repeat_event:
            self._repeat_event.cancel()
            self._repeat_event = None
        self.background_color = (0.2, 0.25, 0.3, 1)

class TransportButton(Button):
    def __init__(self, text, cmd, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.cmd = cmd
        self.background_normal = ''
        self.background_color = (0.15, 0.2, 0.25, 1)
        self.color = (0.9, 0.9, 0.9, 1)
        self.font_size = 20
        self.bold = True
        self.is_active = False
        
        self.bind(on_press=self.send_press)

    def send_press(self, *args):
        app = App.get_running_app()
        if hasattr(app, 'osc_client') and app.osc_client:
            new_val = 0.0 if self.is_active else 1.0
            self.set_active(new_val > 0.5)  # Toggle locally immediately
            app.osc_client.send_message(f"/ui/{app.controller_id}/transport/{self.cmd}", new_val)

    def set_active(self, active: bool):
        self.is_active = active
        if active:
            if self.cmd == 'rec':
                self.background_color = (0.9, 0.2, 0.2, 1)
            elif self.cmd == 'play':
                self.background_color = (0.2, 0.8, 0.3, 1)
            elif self.cmd == 'loop':
                self.background_color = (0.8, 0.7, 0.1, 1)
        else:
            self.background_color = (0.15, 0.2, 0.25, 1)

class ActionRow(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 70
        self.padding = 10
        self.spacing = 15
        
        with self.canvas.before:
            Color(0.08, 0.1, 0.13, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        self.build_nudge_mode()

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def trigger_nudge(self, steps):
        app = App.get_running_app()
        if hasattr(app, 'osc_client') and app.osc_client:
            app.osc_client.send_message(f"/ui/{app.controller_id}/nudge", steps)

    def build_nudge_mode(self):
        self.clear_widgets()
        
        # Zone 1: Nudge Left
        zone_left = BoxLayout(orientation='horizontal', size_hint_x=0.33, spacing=10)
        zone_left.add_widget(AutoRepeatButton(text="< 8", steps=-8, action_callback=self.trigger_nudge))
        zone_left.add_widget(AutoRepeatButton(text="< 4", steps=-4, action_callback=self.trigger_nudge))
        zone_left.add_widget(AutoRepeatButton(text="< 1", steps=-1, action_callback=self.trigger_nudge))
        self.add_widget(zone_left)
        
        # Zone 2: Transport
        zone_center = BoxLayout(orientation='horizontal', size_hint_x=0.33, spacing=10)
        self.btn_loop = TransportButton("LOOP", "loop")
        self.btn_play = TransportButton("PLAY/PAUSE", "play")
        self.btn_rec = TransportButton("REC", "rec")
        zone_center.add_widget(self.btn_loop)
        zone_center.add_widget(self.btn_play)
        zone_center.add_widget(self.btn_rec)
        self.add_widget(zone_center)
        
        # Zone 3: Nudge Right
        zone_right = BoxLayout(orientation='horizontal', size_hint_x=0.33, spacing=10)
        zone_right.add_widget(AutoRepeatButton(text="1 >", steps=1, action_callback=self.trigger_nudge))
        zone_right.add_widget(AutoRepeatButton(text="4 >", steps=4, action_callback=self.trigger_nudge))
        zone_right.add_widget(AutoRepeatButton(text="8 >", steps=8, action_callback=self.trigger_nudge))
        self.add_widget(zone_right)

    def update_transport_state(self, cmd: str, val: float):
        is_active = (val >= 0.5)
        if cmd == 'play' and hasattr(self, 'btn_play'):
            self.btn_play.set_active(is_active)
        elif cmd == 'rec' and hasattr(self, 'btn_rec'):
            self.btn_rec.set_active(is_active)
        elif cmd == 'loop' and hasattr(self, 'btn_loop'):
            self.btn_loop.set_active(is_active)
