import os
import json
from kivy.config import Config

# Lade die gerätespezifische Konfiguration (z.B. vom Deployment-Skript erstellt)
config_path = os.path.join(os.path.dirname(__file__), 'device_config.json')
if os.path.exists(config_path):
    try:
        with open(config_path, 'r') as f:
            dev_conf = json.load(f)
            if 'rotation' in dev_conf:
                Config.set('graphics', 'rotation', dev_conf['rotation'])
    except Exception as e:
        print(f"Warning: Could not read device config: {e}")

# Kivy-Konfiguration VOR allen anderen Imports
# Verhindert, dass Kivy beim Wischen auf Touchscreens das Fenster verschiebt/rotiert
Config.set('graphics', 'multisamples', '0')
# -------------------------------------------------------------------------
# RASPBERRY PI ZERO-LATENCY TOUCH HACK
# Deaktiviere alle Kivy-internen Verzögerungen/Filter für Touch-Events
# -------------------------------------------------------------------------
Config.set('postproc', 'retain_time', '0')
Config.set('postproc', 'retain_distance', '0')
Config.set('postproc', 'jitter_distance', '0')
Config.set('postproc', 'jitter_ignore', '1')

# FPS-Monitor aktivieren, um zu prüfen ob die Framerate das Problem ist
Config.set('modules', 'monitor', '')

import kivy
from kivy.app import App
from widgets.channel_strip import DAWChannelStrip

kivy.require('2.0.0')


NUM_CHANNELS = 12


class DAWDeskApp(App):
    def on_start(self):
        # Dynamisches Hinzufügen von Kanalzügen beim Start der App
        mixer = self.root.ids.mixer_layout
        for i in range(1, NUM_CHANNELS + 1):
            channel = DAWChannelStrip(
                track_name=f"Ch {i}",
                value=-60.0,
                meter_value=-60.0,
                pan=0.0,
                pan_min=-100.0,
                pan_max=100.0
            )
            mixer.add_widget(channel)


if __name__ == '__main__':
    DAWDeskApp().run()
