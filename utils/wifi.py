import subprocess
import re
import platform

def is_raspberry_pi():
    """Detect if we are running on Linux where nmcli is expected."""
    return platform.system() == "Linux"

def scan_networks():
    """
    Scans for available Wi-Fi networks using nmcli.
    Returns a list of dicts: [{'ssid': 'MyWifi', 'signal': 85}, ...]
    If nmcli is not available (e.g., testing on Mac), returns mock data.
    """
    if not is_raspberry_pi():
        # Mock data for testing on non-Linux hosts
        return [
            {'ssid': 'StudioNet_5G', 'signal': 95},
            {'ssid': 'GuestWifi', 'signal': 40},
            {'ssid': 'DAWDesk_Direct', 'signal': 80},
        ]

    try:
        # -t: tabular, -f: fields, dev wifi: scan
        # Note: escaping colons in nmcli output can be tricky, using basic split for now
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL', 'dev', 'wifi'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        networks = []
        seen = set()
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            # nmcli -t escapes colons with a backslash. 
            # Easiest way to parse is to split by unescaped colons or just rsplit since SIGNAL is at the end.
            # But let's use rsplit to separate SSID from SIGNAL (which is just a number)
            parts = line.rsplit(':', 1)
            if len(parts) >= 2:
                ssid = parts[0].strip().replace('\\:', ':')
                if not ssid or ssid in seen:
                    continue  # Ignore hidden or duplicate SSIDs
                try:
                    signal = int(parts[1].strip())
                    networks.append({'ssid': ssid, 'signal': signal})
                    seen.add(ssid)
                except ValueError:
                    pass
        # Sort by signal strength descending
        networks.sort(key=lambda x: x['signal'], reverse=True)
        return networks
    except Exception as e:
        print(f"Wi-Fi Scan Error: {e}")
        return []

def connect_to_wifi(ssid, password):
    """
    Attempts to connect to the given Wi-Fi network using nmcli.
    Returns (True, "Connected successfully") on success, or (False, "Error message") on failure.
    """
    if not is_raspberry_pi():
        # Mock connection for testing
        print(f"MOCK: Connecting to {ssid} with password {password}")
        if password == "wrong":
            return False, "Falsches Passwort (MOCK)"
        return True, "Erfolgreich verbunden (MOCK)"

    try:
        # Remove existing connection profile to prevent conflicts or 'already exists' errors
        subprocess.run(
            ['sudo', 'nmcli', 'connection', 'delete', 'id', ssid],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        cmd = ['sudo', 'nmcli', '--ask=no', 'dev', 'wifi', 'connect', ssid]
        if password:
            cmd.extend(['password', password])

        # Using nmcli dev wifi connect
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return True, "Erfolgreich verbunden"
        else:
            err = result.stderr.strip() or result.stdout.strip()
            # Clean up common cryptic nmcli errors
            if "key-mgmt" in err and "missing" in err:
                err = "Passwort fehlt (oder Netzwerk ist versteckt)."
            elif "802-11-wireless-security.psk" in err:
                err = "Ungültiges Passwort (muss mind. 8 Zeichen lang sein)."
            elif "802-11" in err:
                err = "WLAN-Sicherheitsfehler (falsches Passwort oder Verschlüsselung)."
            return False, f"Fehler: {err}"
    except Exception as e:
        return False, f"Systemfehler: {e}"
