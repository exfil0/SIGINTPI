import subprocess
import sys
import os

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
    print("This script installs bladeRF, sets up permissions, and performs a quick scan.\n")

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

    # 3. Create a udev rule for bladeRF (Vendor=2cf0, Product=5246).
    #    If your device has different IDs, update them.
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
    print("\n[WARNING] A logout/login or reboot is typically required for group changes to apply.\n")

    # 5. Basic BladeRF Test: 'bladeRF-cli -p' to probe
    print("[TEST] Checking bladeRF with 'bladeRF-cli -p' (probing).")
    test_result = subprocess.run("bladeRF-cli -p", shell=True)
    if test_result.returncode != 0:
        print("[WARN] 'bladeRF-cli -p' returned an error. You may need to log out/in or reboot first.")
    else:
        print("[INFO] 'bladeRF-cli -p' ran successfully. BladeRF is recognized.\n")

    # 6. Optional: Quick frequency scan/capture
    print("[INFO] Let's capture a small sample (scan) on a chosen frequency.\n")
    freq_str = input("Enter a frequency in Hz (e.g. 950000000 for 950 MHz): ").strip()
    if not freq_str.isdigit():
        print("[WARN] Invalid frequency input. Skipping capture.")
    else:
        # We'll do a short 2MHz sample rate, 1.5MHz bandwidth, 2-second capture
        # that writes ~4 million samples to 'test_bladerf_scanner.bin'.
        # Adjust these as needed for your environment.
        sample_cmd = (
            "bladeRF-cli -e '"
            f"set frequency rx {freq_str}; "
            "set samplerate rx 2.0M; "
            "set bandwidth rx 1.5M; "
            "set gain rx 30; "
            "rx config file=test_bladerf_scanner.bin format=bin n=4000000;"
            "rx start; rx wait; rx stop;'"
        )
        run_command(
            sample_cmd,
            f"Capturing ~4M samples at {freq_str} Hz into test_bladerf_scanner.bin"
        )
        print("[INFO] If no error occurred, 'test_bladerf_scanner.bin' was created.")
        print("       You can inspect it with SDR tools (GNU Radio, inspectrum, etc.)\n")

    # 7. Final steps / optional reboot
    reboot_choice = input("Would you like to reboot now? [y/N]: ").strip().lower()
    if reboot_choice == "y":
        print("[INFO] Rebooting...")
        run_command("sudo reboot", "Rebooting")
    else:
        print("[INFO] Skipping reboot. Please remember to log out/in or reboot to apply group changes.\n")

    print("========== BLADE-RF SCAN COMPLETE ==========")
    print("BladeRF is installed, udev rules are set, and a quick sample capture has been performed!")
    print("Use 'bladeRF-cli -p' or load 'test_bladerf_scanner.bin' in an SDR tool to confirm everything works.\n")

if __name__ == "__main__":
    main()
