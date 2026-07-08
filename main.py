import kivy
from kivy.app import App
from widgets.channel_strip import DAWChannelStrip

kivy.require('2.0.0')


class DAWDeskApp(App):
    def on_start(self):
        # Dynamisches Hinzufügen von 3 Kanalzügen beim Start der App
        mixer = self.root.ids.mixer_layout
        # Erzeuge 8 Kanäle in einer Schleife
        for i in range(1, 9):
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
