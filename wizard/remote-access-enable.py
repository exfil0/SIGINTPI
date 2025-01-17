import subprocess
import re

def run_command(command, description=None):
    """Run a shell command and display its output."""
    try:
        print(f"Running: {description or command}")
        result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running {command}: {e.stderr}")
        return None

def get_ip_address():
    """Identify the assigned IP address."""
    print("Identifying IP address...")
    try:
        result = subprocess.run("ifconfig", shell=True, text=True, stdout=subprocess.PIPE)
        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", result.stdout)
        if match:
            ip_address = match.group(1)
            print(f"IP Address found: {ip_address}")
            return ip_address
        else:
            print("No IP address found. Ensure the Raspberry Pi is connected to a network.")
            return None
    except Exception as e:
        print(f"Error getting IP address: {e}")
        return None

def update_system():
    """Update the system."""
    run_command("sudo apt update -y && sudo apt upgrade -y", "Updating and upgrading the system")

def activate_ssh():
    """Activate and enable SSH."""
    run_command("sudo systemctl start ssh", "Starting SSH service")
    run_command("sudo systemctl enable ssh", "Enabling SSH service")
    run_command("sudo systemctl status ssh", "Checking SSH service status")

def activate_vnc():
    """Activate and enable VNC."""
    run_command("sudo raspi-config nonint do_vnc 0", "Enabling VNC through raspi-config")
    run_command("sudo systemctl start vncserver-x11-serviced", "Starting VNC service")
    run_command("sudo systemctl enable vncserver-x11-serviced", "Enabling VNC service")

def main():
    print("Raspberry Pi Automation Script\n")

    # Step 1: Identify the IP address
    ip_address = get_ip_address()
    if not ip_address:
        print("Failed to retrieve the IP address. Check your network connection.")
        return

    # Step 2: Update the system
    update_system()

    # Step 3: Activate SSH
    activate_ssh()

    # Step 4: Activate and enable VNC
    activate_vnc()

    # Display remote access details
    print("\nSetup complete!")
    print(f"Remote Access Details:")
    print(f"  SSH: ssh pi@{ip_address}")
    print(f"  VNC Viewer: {ip_address}:1 (default display)")

if __name__ == "__main__":
    main()
