import os
os.environ["KIVY_NO_ARGS"] = "1"
import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen

kv = """
<DAWDeskRoot@ScreenManager>:
    MainScreen:
        name: 'main'

<MainScreen@Screen>:
    BoxLayout:
        Label:
            id: my_label
            text: 'Hello'
"""

class TestApp(App):
    def build(self):
        return Builder.load_string(kv)

    def on_start(self):
        main_screen = self.root.get_screen('main')
        print("IDS_DUMP:", main_screen.ids)
        App.get_running_app().stop()

if __name__ == '__main__':
    TestApp().run()
