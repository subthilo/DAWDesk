# DAWDesk – Dokumentation

DAWDesk ist eine modulare Kivy-basierte DAW-Mixer-Oberfläche. Sie stellt Kanalzüge mit Lautstärkeregler, Pan-Regler und Spurbezeichnung als reaktive, skalierbare Widgets dar.

## Inhaltsverzeichnis

| Dokument | Beschreibung |
|----------|-------------|
| [Architektur](architecture.md) | Projektstruktur, Modul-Verantwortlichkeiten und Design-Patterns |
| [Widgets](widgets.md) | Detaillierte Beschreibung aller Widgets (DAWFader, DAWPanKnob, DAWChannelStrip) |
| [Konfiguration](configuration.md) | Alle konfigurierbaren Properties, wo sie definiert sind und wie man sie ändert |
| [Designentscheidungen](design-decisions.md) | Technische Entscheidungen, Kivy-spezifische Erkenntnisse und Begründungen |

## Schnellstart

```bash
# Virtuelle Umgebung aktivieren und App starten
source .venv/bin/activate
python main.py
```

## Technologie

- **Python 3.9+**
- **Kivy 2.3.1** – Cross-Platform-UI-Framework
- **Keine externen Abhängigkeiten** außer Kivy
