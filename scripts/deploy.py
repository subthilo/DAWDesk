#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import tarfile
import tempfile

def ensure_dependencies():
    try:
        import paramiko
        import scp
    except ImportError:
        print("Installing required deployment packages (paramiko, scp)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "scp"])
        import paramiko
        import scp
    return paramiko, scp

def create_tarball(source_dir, output_filename):
    print(f"Creating archive of {source_dir}...")
    with tarfile.open(output_filename, "w:gz") as tar:
        # We want to exclude .venv, .git, __pycache__, etc.
        def exclude_filter(tarinfo):
            name = tarinfo.name
            if any(x in name for x in ['.venv', '.git', '__pycache__', '.DS_Store', os.path.basename(output_filename)]):
                return None
            return tarinfo
        tar.add(source_dir, arcname=os.path.basename(source_dir), filter=exclude_filter)
    print(f"Created {output_filename}")

def deploy(host, user, password, port, waveshare, rotate, controller_id, channels):
    paramiko, scp_module = ensure_dependencies()
    from scp import SCPClient
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    project_name = os.path.basename(project_dir)
    
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tar_path = tmp.name
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        create_tarball(project_dir, tar_path)
        
        print(f"Connecting to {user}@{host}:{port}...")
        
        try:
            ssh.connect(host, port=port, username=user, password=password, timeout=10)
        except Exception as e:
            print(f"Failed to connect: {e}")
            return
            
        print("Connected successfully.")
        
        remote_tar_path = f"/home/{user}/{project_name}.tar.gz"
        remote_project_path = f"/home/{user}/{project_name}"
        
        print(f"Uploading archive to {remote_tar_path}...")
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(tar_path, remote_tar_path)
            
        print("Extracting archive on Raspberry Pi...")
        stdin, stdout, stderr = ssh.exec_command(f"tar -xzf {remote_tar_path} -C /home/{user}/")
        stdout.channel.recv_exit_status() # Wait for completion
        
        # Cleanup tarball on remote
        ssh.exec_command(f"rm {remote_tar_path}")
        
        print("\n--- Running setup script on Raspberry Pi ---\n")
        waveshare_flag = "--waveshare" if waveshare else ""
        rotate_flag = f"--rotate {rotate}" if rotate is not None else ""
        controller_id_flag = f"--controller-id {controller_id}" if controller_id else ""
        channels_flag = f"--channels {channels}" if channels else ""
        
        # Note: We use python3 explicitly
        cmd = f"cd {remote_project_path} && chmod +x scripts/setup_rpi.py && python3 scripts/setup_rpi.py {waveshare_flag} {rotate_flag} {controller_id_flag} {channels_flag}"
        
        # get_pty=True provides unbuffered output and allows sudo to prompt for password if needed
        # (Though we're running it with sudo inside the script which might block if it asks for a password on the PTY, 
        # usually on Pi, the pi user has sudo without password, or we can use echo pass | sudo -S). 
        # Assuming standard Raspberry Pi OS where sudo works without password for the main user.
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        
        for line in iter(stdout.readline, ""):
            print(line, end="")
            
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("\n✅ Deployment and setup successful!")
            print(f"The project is now ready at {remote_project_path} on your Raspberry Pi.")
            print(f"To run it manually, SSH into the Pi and run:\n  cd {remote_project_path}\n  source .venv/bin/activate\n  python main.py")
        else:
            print(f"\n❌ Deployment script failed with status {exit_status}")
            
    finally:
        if os.path.exists(tar_path):
            os.remove(tar_path)
        try:
            ssh.close()
        except:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy DAWDesk to Raspberry Pi")
    parser.add_argument("host", help="IP address or hostname of the Raspberry Pi")
    parser.add_argument("user", help="SSH username (e.g., 'pi' or your custom user)")
    parser.add_argument("password", help="SSH password")
    parser.add_argument("-p", "--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--waveshare", action="store_true", help="Pass --waveshare flag to setup script")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], help="Screen rotation angle for the Waveshare display (OS level)")
    
    parser.add_argument("--controller-id", type=str, default=None,
                        help="Eindeutiger Name dieses Controllers (z.B. 'rpi-studio-1'). "
                             "Wird in device_config.json gespeichert und als Discovery-ID verwendet. "
                             "Fallback: Hostname des RPi.")
    parser.add_argument("--channels", type=int, default=12,
                        help="Anzahl der Kanäle auf diesem Controller. Default: 12.")

    args = parser.parse_args()

    deploy(args.host, args.user, args.password, args.port,
           args.waveshare, args.rotate, args.controller_id, args.channels)
