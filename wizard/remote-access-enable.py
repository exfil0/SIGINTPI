import subprocess
import re
import sys

def run_command(command, description=None, exit_on_failure=False):
    """
    Run a shell command and optionally exit if the command fails.
    
    :param command: Command to be executed.
    :param description: Text to display before running the command (optional).
    :param exit_on_failure: If True, the script will exit on failure of this command.
    :return: The command's stdout as a string, or None if an error occurred.
    """
    try:
        print(f"\n[+] Running: {description or command}")
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Print command output for visibility
        if result.stdout.strip():
            print(f"    Output:\n{result.stdout.strip()}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[!] ERROR: Failed to run: {command}\n    Reason: {e.stderr.strip() or str(e)}")
        if exit_on_failure:
            sys.exit(1)  # Stop the script
        return None


def get_ip_address():
    """
    Identify the assigned IP address by parsing ifconfig output.
    
    :return: IP address as a string, or None if not found.
    """
    print("\n[+] Identifying IP address...")
    try:
        result = subprocess.run("ifconfig", shell=True, text=True, stdout=subprocess.PIPE)
        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", result.stdout)
        if match:
            ip_address = match.group(1)
            print(f"    IP Address found: {ip_address}")
            return ip_address
        else:
            print("    [!] No IP address found. Ensure the Raspberry Pi is connected to a network.")
            return None
    except Exception as e:
        print(f"[!] ERROR getting IP address: {e}")
        return None


def update_system():
    """
    Update and upgrade the system.
    """
    print("\n[+] Updating and upgrading the system...")
    # Exit immediately if the update/upgrade fails
    run_command("sudo apt update -y && sudo apt upgrade -y", 
                "Updating & Upgrading System", 
                exit_on_failure=True)


def activate_ssh():
    """
    Activate and enable SSH service, then verify status.
    """
    print("\n[+] Activating SSH service...")
    run_command("sudo systemctl start ssh", "Starting SSH service", exit_on_failure=True)
    run_command("sudo systemctl enable ssh", "Enabling SSH service", exit_on_failure=True)

    # Verify that SSH is active
    status_output = run_command("sudo systemctl is-active ssh", "Verifying SSH service status")
    if status_output and status_output.strip() == "active":
        print("    SSH is active and running.")
    else:
        print("    [!] SSH is not active. Please investigate.")


def activate_vnc():
    """
    Enable and start the VNC service via raspi-config and systemd, then verify status.
    """
    print("\n[+] Activating VNC service...")
    # 0 => enable, 1 => disable (for raspi-config nonint do_vnc)
    run_command("sudo raspi-config nonint do_vnc 0", "Enabling VNC via raspi-config", exit_on_failure=True)
    run_command("sudo systemctl start vncserver-x11-serviced", "Starting VNC service", exit_on_failure=True)
    run_command("sudo systemctl enable vncserver-x11-serviced", "Enabling VNC service", exit_on_failure=True)

    # Verify that VNC is active
    status_output = run_command("sudo systemctl is-active vncserver-x11-serviced", "Verifying VNC service status")
    if status_output and status_output.strip() == "active":
        print("    VNC is active and running.")
    else:
        print("    [!] VNC is not active. Please investigate.")


def main():
    print("========== Raspberry Pi Automation Script ==========")

    # Step 1: Identify the IP address
    ip_address = get_ip_address()
    if not ip_address:
        print("[!] Failed to retrieve the IP address. Check your network connection.")
        sys.exit(1)  # Stop execution here if no IP address is found

    # Step 2: Update the system
    update_system()

    # Step 3: Activate SSH
    activate_ssh()

    # Step 4: Activate and enable VNC
    activate_vnc()

    # Final Info
    print("\n========== Setup Complete! ==========")
    print("Remote Access Details:")
    print(f"  SSH:       ssh pi@{ip_address}")
    print("             (Default credentials: user = pi, password = raspberry)")
    print(f"  VNC:       Use a VNC viewer to connect to: {ip_address}:1")


if __name__ == "__main__":
    main()
