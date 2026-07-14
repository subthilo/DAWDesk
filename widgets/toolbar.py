import time
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App

class Toolbar(BoxLayout):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            touch.ud['swipe_start_x'] = touch.x
            touch.ud['accum_dx'] = 0.0
            touch.ud['last_nudge_time'] = time.time()
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.dx
            touch.ud['accum_dx'] += dx
            threshold = 80
            current_time = time.time()
            if current_time - touch.ud['last_nudge_time'] > 0.15:
                if touch.ud['accum_dx'] > threshold:
                    self._nudge(-1)
                    touch.ud['accum_dx'] = 0
                    touch.ud['last_nudge_time'] = current_time
                elif touch.ud['accum_dx'] < -threshold:
                    self._nudge(1)
                    touch.ud['accum_dx'] = 0
                    touch.ud['last_nudge_time'] = current_time
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def _nudge(self, direction):
        app = App.get_running_app()
        if hasattr(app, 'osc_client') and app.osc_client:
            try:
                app.osc_client.send_message(f'/ui/{app.controller_id}/nudge', direction)
            except Exception:
                pass
