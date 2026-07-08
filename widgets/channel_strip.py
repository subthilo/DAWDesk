from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty


class DAWChannelStrip(BoxLayout):
    """Kombinierter DAW-Kanalzug.
    Enthält einen Pan-Bereich (oben), den Lautstärkeregler (mittig)
    und die Spuren-Beschriftung (unten).
    """

    track_name = StringProperty("Spur")
    value = NumericProperty(-60.0)
    meter_value = NumericProperty(-60.0)
    pan = NumericProperty(0.0)  # -1.0 (Links) bis 1.0 (Rechts)
    
    # Konfigurierbare Grenzwerte für die Pan-Anzeige (z. B. L100/R100, L50/R50)
    pan_min = NumericProperty(-100.0)
    pan_max = NumericProperty(100.0)
    
    # Layout-Größen (Basiswerte vor Skalierung)
    pan_knob_size = NumericProperty(135.0)   # Basis-Größe des Pan-Knopfes in Pixel
    label_height = NumericProperty(35.0)     # Basis-Höhe des Spurennamens in Pixel
    
    # Trennstrich-Länge relativ zur Gesamtbreite (z. B. 0.6 = 60% Breite, zentriert)
    divider_width_ratio = NumericProperty(0.6)
    
    reference_height = NumericProperty(600.0)
    reference_width = NumericProperty(180.0)
    scale = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(width=self._update_scale, height=self._update_scale)

    def _update_scale(self, *args):
        """Berechnet den kombinierten Skalierungsfaktor für Beschriftungen und Knobs.
        - Vertikal (Höhe) skaliert fließend mit.
        - Horizontal (Breite) skaliert unter 180px mit, bleibt aber nach oben bei 1.0 gedeckelt.
        """
        scale_x = self.width / self.reference_width if self.reference_width > 0 else 1.0
        scale_y = self.height / self.reference_height if self.reference_height > 0 else 1.0
        scale_x = min(1.0, scale_x)
        self.scale = min(scale_x, scale_y)
