import threading
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import mainthread, Clock
from kivy.app import App

from utils.wifi import scan_networks, connect_to_wifi

class SettingsScreen(Screen):
    status_text = StringProperty("Bereit.")
    is_scanning = BooleanProperty(False)
    is_connecting = BooleanProperty(False)
    password_visible = BooleanProperty(False)
    networks = ListProperty([])
    
    def on_enter(self, *args):
        # Trigger a scan every time we enter the settings screen
        self.scan_wifi()

    def scan_wifi(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.status_text = "Suche nach WLAN-Netzwerken..."
        self.networks = []
        
        # Run in background thread to avoid blocking Kivy UI
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        results = scan_networks()
        self._update_networks_ui(results)

    @mainthread
    def _update_networks_ui(self, results):
        self.networks = results
        self.is_scanning = False
        if not results:
            self.status_text = "Keine Netzwerke gefunden."
        else:
            self.status_text = f"{len(results)} Netzwerke gefunden."
            # Populate spinner if we have networks
            spinner = self.ids.network_spinner
            spinner.values = [f"{net['ssid']} ({net['signal']}%)" for net in results]
            if spinner.values and spinner.text == "Wähle ein Netzwerk":
                spinner.text = spinner.values[0]

    def on_network_select(self, spinner_text):
        if spinner_text and spinner_text != "Wähle ein Netzwerk":
            # Extract SSID by stripping the signal strength e.g., "MyWifi (85%)" -> "MyWifi"
            ssid = spinner_text.rsplit(' (', 1)[0]
            self.ids.ssid_input.text = ssid

    def connect(self):
        if self.is_connecting:
            return
            
        ssid = self.ids.ssid_input.text.strip()
        password = self.ids.password_input.text.strip()
        
        if not ssid:
            self.status_text = "Bitte ein Netzwerk auswählen oder eingeben."
            return
            
        self.is_connecting = True
        self.status_text = f"Verbinde mit {ssid}..."
        
        # Run in background thread
        threading.Thread(target=self._connect_thread, args=(ssid, password), daemon=True).start()

    def _connect_thread(self, ssid, password):
        success, msg = connect_to_wifi(ssid, password)
        self._update_connect_ui(success, msg)

    @mainthread
    def _update_connect_ui(self, success, msg):
        self.is_connecting = False
        self.status_text = msg
        if success:
            self.ids.password_input.text = ""
            Clock.schedule_once(lambda dt: self.scan_wifi(), 2)

    def close_settings(self):
        # Hide keyboard if open
        import kivy.core.window
        kivy.core.window.Window.release_all_keyboards()
        App.get_running_app().root.current = 'main'
