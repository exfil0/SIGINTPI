import subprocess
import sys
import os

# Feel free to reuse your existing run_command or define a minimal version below
def run_command(command, description=None, exit_on_failure=False):
    """
    Run a shell command and optionally exit if the command fails.
    
    :param command: The shell command to run (string).
    :param description: Text describing the command (string).
    :param exit_on_failure: If True, the script will exit if this command fails.
    """
    desc = description or command
    print(f"\n[+] {desc}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout = result.stdout.strip()
        if stdout:
            print("    Output:")
            print("    " + "\n    ".join(stdout.splitlines()))
        print(f"    [SUCCESS] {desc}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip()
        error_msg = stderr if stderr else str(e)
        print(f"    [ERROR] {desc}\n      Reason: {error_msg}")
        if exit_on_failure:
            sys.exit(1)

def get_actual_user():
    """
    Returns the user that invoked sudo, or $USER if not running under sudo.
    If everything else fails, defaults to 'pi'.
    """
    sudo_user = os.getenv("SUDO_USER", "")
    if sudo_user:
        return sudo_user.strip()
    env_user = os.getenv("USER", "pi").strip()
    return env_user if env_user else "pi"

def main():
    print("\n========== RASPBERRY PI & BLADE-RF READINESS ==========")
    print("This script installs bladeRF packages, sets up permissions, and runs a quick test.\n")

    # 1. Ensure the system is updated
    run_command(
        "sudo apt-get update -y && sudo apt-get upgrade -y",
        "Updating & upgrading the system"
    )

    # 2. Install bladeRF
    run_command(
        "sudo apt-get install -y bladerf",
        "Installing bladeRF tools",
        exit_on_failure=True
    )

    # 3. Create a udev rule for bladeRF (Vendor=2cf0, Product=5246)
    print("\n[INFO] Creating udev rule for BladeRF at /etc/udev/rules.d/53-bladerf.rules.")
    bladerf_rule = 'SUBSYSTEM=="usb", ATTR{idVendor}=="2cf0", ATTR{idProduct}=="5246", MODE="0666", GROUP="plugdev"'
    rule_cmd = f'echo \'{bladerf_rule}\' | sudo tee /etc/udev/rules.d/53-bladerf.rules'
    run_command(rule_cmd, "Creating /etc/udev/rules.d/53-bladerf.rules")

    # Reload & trigger udev
    run_command(
        "sudo udevadm control --reload-rules && sudo udevadm trigger",
        "Reloading udev rules"
    )

    # 4. Add current user to plugdev group
    actual_user = get_actual_user()
    print(f"\n[INFO] Adding user '{actual_user}' to 'plugdev' group for BladeRF USB access.")
    run_command(
        f"sudo usermod -aG plugdev {actual_user}",
        f"Adding '{actual_user}' to plugdev group"
    )
    print("\n[WARNING] A log out/in or reboot is typically required for group changes to apply.\n")

    # 5. Basic BladeRF Test
    # We can try “bladeRF-cli -p” to probe the device, or “bladeRF-cli -i” for interactive shell, etc.
    # For a quick test, we do “bladeRF-cli -p”
    print("[TEST] Attempting a quick bladeRF test (non-sudo).")
    test_result = subprocess.run("bladeRF-cli -p", shell=True)
    if test_result.returncode != 0:
        print("[WARN] 'bladeRF-cli -p' returned an error. You may need to log out/in or reboot before testing again.")
    else:
        print("[INFO] 'bladeRF-cli -p' ran successfully. BladeRF is recognized.")

    # 6. Final steps / optional reboot
    reboot_choice = input("\nWould you like to reboot now? [y/N]: ").strip().lower()
    if reboot_choice == "y":
        print("[INFO] Rebooting...")
        run_command("sudo reboot", "Rebooting")
    else:
        print("[INFO] Skipping reboot. Please remember to log out/in or reboot to apply group changes.\n")

    print("========== BLADE-RF SETUP COMPLETE ==========")
    print("bladeRF is installed and a quick test has been performed.")
    print("Use 'bladeRF-cli -p' (non-sudo) after logging back in to confirm everything works.\n")

if __name__ == "__main__":
    main()
