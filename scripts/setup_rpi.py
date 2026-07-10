#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys

def run_command(cmd, shell=False, check=True):
    print(f"==> Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    subprocess.run(cmd, shell=shell, check=check)

def install_system_dependencies():
    print("\n--- Installing System Dependencies ---")
    run_command(["sudo", "apt-get", "update"])
    
    deps = [
        "python3-dev",
        "python3-pip",
        "python3-venv",
        "libsdl2-dev",
        "libsdl2-image-dev",
        "libsdl2-mixer-dev",
        "libsdl2-ttf-dev",
        "pkg-config",
        "libgl1-mesa-dev",
        "libgles2-mesa-dev",
        "python3-setuptools",
        "mtdev-tools"  # Often useful for Kivy touch
    ]
    
    run_command(["sudo", "apt-get", "install", "-y"] + deps)

def setup_python_env(project_dir):
    print("\n--- Setting up Python Environment ---")
    venv_dir = os.path.join(project_dir, ".venv")
    
    if not os.path.exists(venv_dir):
        print(f"Creating virtual environment in {venv_dir}")
        run_command(["python3", "-m", "venv", venv_dir])
    else:
        print(f"Virtual environment {venv_dir} already exists.")
        
    pip_exe = os.path.join(venv_dir, "bin", "pip")
    req_file = os.path.join(project_dir, "requirements.txt")
    
    if os.path.exists(req_file):
        print("Installing requirements.txt...")
        run_command([pip_exe, "install", "--upgrade", "pip", "setuptools"])
        run_command([pip_exe, "install", "-r", req_file])
    else:
        print(f"Warning: {req_file} not found!")

def configure_waveshare(rotation=None):
    print("\n--- Configuring Waveshare Display ---")
    config_file = "/boot/firmware/config.txt"
    cmdline_file = "/boot/firmware/cmdline.txt"
    overlay = "dtoverlay=vc4-kms-dsi-waveshare-panel-v2,10_1_inch_a"
    
    # Check if the file exists (some older RPi OS use /boot/config.txt)
    if not os.path.exists(config_file):
        alt_config = "/boot/config.txt"
        if os.path.exists(alt_config):
            config_file = alt_config
            cmdline_file = "/boot/cmdline.txt"
        else:
            print("Error: Could not find config.txt in /boot/firmware or /boot")
            return

    try:
        with open(config_file, "r") as f:
            content = f.read()
            
        if overlay in content:
            print(f"[{config_file}] Overlay already present. Skipping.")
        else:
            print(f"[{config_file}] Adding {overlay}...")
            # Use sudo tee to append
            cmd = f"echo '{overlay}' | sudo tee -a {config_file}"
            run_command(cmd, shell=True)
            print("NOTE: You will need to reboot for the display changes to take effect.")
            
    except PermissionError:
        print(f"Permission denied reading {config_file}. Try running with sudo if needed.")
    except Exception as e:
        print(f"Error configuring display: {e}")
        
    if rotation is not None:
        try:
            # Statt OS-Rotation (die unzuverlässig ist), schreiben wir eine config,
            # die Kivy beim Start ausliest.
            config_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "device_config.json")
            import json
            config_data = {"rotation": str(rotation)}
            
            with open(config_json_path, "w") as f:
                json.dump(config_data, f)
            print(f"[{config_json_path}] Saved Kivy rotation setting ({rotation} degrees).")
            
            # Wir räumen eventuelle alte cmdline.txt Einträge auf
            cmdline_file = "/boot/firmware/cmdline.txt"
            if not os.path.exists(cmdline_file) and os.path.exists("/boot/cmdline.txt"):
                cmdline_file = "/boot/cmdline.txt"
                
            if os.path.exists(cmdline_file):
                with open(cmdline_file, "r") as f:
                    content = f.read().strip()
                import re
                new_content = re.sub(r'\s?video=DSI-1:[^\s]+', '', content).strip()
                new_content = re.sub(r'\s?fbcon=rotate:[0-3]', '', new_content).strip()
                if new_content != content:
                    cmd = f"echo '{new_content}' | sudo tee {cmdline_file}"
                    run_command(cmd, shell=True)
                    print("Cleaned up old OS rotation settings from cmdline.txt.")
        except Exception as e:
            print(f"Error configuring rotation: {e}")

def setup_autostart(project_dir):
    print("\n--- Configuring Autostart (systemd) ---")
    current_user = os.environ.get("USER", "pi")
    service_content = f"""[Unit]
Description=DAWDesk Kivy App
After=network.target

[Service]
User={current_user}
WorkingDirectory={project_dir}
Environment="PATH={project_dir}/.venv/bin:/usr/bin:/bin"
ExecStart={project_dir}/.venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    service_path = "/tmp/dawdesk.service"
    with open(service_path, "w") as f:
        f.write(service_content)
        
    try:
        run_command(["sudo", "mv", service_path, "/etc/systemd/system/dawdesk.service"])
        run_command(["sudo", "systemctl", "daemon-reload"])
        run_command(["sudo", "systemctl", "enable", "dawdesk.service"])
        run_command(["sudo", "systemctl", "restart", "--no-block", "dawdesk.service"])
        print("Systemd service 'dawdesk.service' created, enabled and restarted.")
        print("The app will start automatically on the next boot.")
    except Exception as e:
        print(f"Failed to setup autostart: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup DAWDesk environment on Raspberry Pi")
    parser.add_argument("--waveshare", action="store_true", help="Configure /boot/firmware/config.txt for Waveshare 10.1 display")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], help="Screen rotation angle for the Waveshare display")
    parser.add_argument("--controller-id", type=str, default=None,
                        help="Eindeutiger Name dieses Controllers (z.B. 'rpi-studio-1')")
    parser.add_argument("--channels", type=int, default=12,
                        help="Anzahl der Kanäle auf diesem Controller. Default: 12.")
    
    args = parser.parse_args()
    
    # Get the directory where setup_rpi.py is located, then go one level up to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    install_system_dependencies()
    setup_python_env(project_dir)
    
    if args.waveshare:
        configure_waveshare(args.rotate)
    elif args.rotate is not None:
        # Rotation ohne Waveshare-Display-Konfiguration (nur device_config.json)
        configure_waveshare(args.rotate)

    # Controller-ID in device_config.json schreiben (ergänzend zu Rotation)
    if args.controller_id:
        print(f"\n--- Setting Controller ID: '{args.controller_id}' ---")
        import json as _json
        config_json_path = os.path.join(project_dir, 'device_config.json')
        config_data = {}
        if os.path.exists(config_json_path):
            try:
                with open(config_json_path, 'r') as _f:
                    config_data = _json.load(_f)
            except Exception:
                pass
        config_data['controller_id'] = args.controller_id
        config_data['channels'] = args.channels
        with open(config_json_path, 'w') as _f:
            _json.dump(config_data, _f, indent=2)
        print(f"  Saved controller_id='{args.controller_id}', channels={args.channels} to {config_json_path}")

    setup_autostart(project_dir)
        
    print("\n--- Setup Complete ---")
    print("To run DAWDesk manually:")
    print(f"  cd {project_dir}")
    print("  source .venv/bin/activate")
    print("  python main.py")
