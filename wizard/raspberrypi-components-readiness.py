import subprocess
import sys
import time
import os

# Common Vendor:Product IDs for RTL-SDR & HackRF.
# Adjust if your specific dongles use different IDs.
DEVICE_IDS = {
    "NESDR (RTL-SDR)": ["0bda:2838", "0bda:2832"],  # Realtek chipsets
    "HackRF": ["1d50:6089"],                        # HackRF
}

# Paths to udev rules we'll create if missing
RTLSDR_RULES_PATH = "/etc/udev/rules.d/20-rtl-sdr.rules"
HACKRF_RULES_PATH = "/etc/udev/rules.d/52-hackrf.rules"

def run_command(command, description=None, exit_on_failure=False):
    """
    Run a shell command and optionally exit if the command fails.
    
    :param command: Command to be executed (string).
    :param description: Description shown before running the command (string).
    :param exit_on_failure: If True, the script will exit immediately on command failure.
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

def is_device_plugged(device_id_list):
    """
    Check via lsusb if at least one Vendor:Product ID in device_id_list is currently connected.

    :param device_id_list: List of strings, each in 'vvvv:pppp' format (hex).
    :return: True if any matching device is found, False otherwise.
    """
    try:
        lsusb_output = subprocess.check_output(["lsusb"], text=True).strip().lower()
        for device_id in device_id_list:
            if device_id.lower() in lsusb_output:
                return True
    except Exception:
        pass
    return False

def wait_for_device(device_name, device_id_list):
    """
    Continuously checks for device presence via lsusb every 5 seconds.
    The script waits until the device is detected, or user presses Ctrl+C.
    
    :param device_name: Descriptive name of the device (string).
    :param device_id_list: List of IDs (strings) to look for in lsusb.
    """
    print(f"\n[INFO] Please plug in your {device_name} (if not already).")
    print("       The script will detect it automatically.")
    while True:
        if is_device_plugged(device_id_list):
            print(f"[INFO] {device_name} is now detected via USB.")
            break
        else:
            print(f"    [WAITING] {device_name} not detected yet... Retrying in 5s.")
            time.sleep(5)

def setup_udev_rules_and_permissions():
    """
    Ensures that udev rules for both RTL-SDR and HackRF exist, then reloads them
    and adds the current user to the 'plugdev' group for USB device access.
    """
    print("\n[INFO] Setting up udev rules & permissions for RTL-SDR and HackRF.")

    # 1) Create or overwrite RTL-SDR rule if missing
    if not os.path.isfile(RTLSDR_RULES_PATH):
        rtl_rule = (
            'SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="2838", MODE="0666", GROUP="plugdev"\n'
            'SUBSYSTEM=="usb", ATTR{idVendor}=="0bda", ATTR{idProduct}=="2832", MODE="0666", GROUP="plugdev"\n'
        )
        run_command(
            f'echo "{rtl_rule.strip()}" | sudo tee {RTLSDR_RULES_PATH}',
            f"Creating udev rules for RTL-SDR at {RTLSDR_RULES_PATH}"
        )
    else:
        print(f"[INFO] RTL-SDR rules already exist: {RTLSDR_RULES_PATH}")

    # 2) Create or overwrite HackRF rule if missing
    if not os.path.isfile(HACKRF_RULES_PATH):
        hackrf_rule = 'SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", MODE="0666", GROUP="plugdev"'
        run_command(
            f'echo "{hackrf_rule}" | sudo tee {HACKRF_RULES_PATH}',
            f"Creating udev rules for HackRF at {HACKRF_RULES_PATH}"
        )
    else:
        print(f"[INFO] HackRF rules already exist: {HACKRF_RULES_PATH}")

    # 3) Reload and trigger udev
    run_command(
        "sudo udevadm control --reload-rules && sudo udevadm trigger",
        "Reloading udev rules"
    )

    # 4) Add user to plugdev group
    current_user = os.getenv("USER") or "pi"
    run_command(
        f"sudo usermod -aG plugdev {current_user}",
        f"Adding user '{current_user}' to 'plugdev' group"
    )

    print("[INFO] Permissions setup complete. You may need to log out/in or reboot for changes to take effect.\n")

def main():
    print("\n========== RASPBERRY PI 5 AND COMPONENTS READINESS (STAGE 2) ==========")
    print("This script installs drivers/packages, sets up permissions, and tests NESDR (RTL-SDR) & HackRF devices.\n")

    ########################################################################
    # 1. Ensure development tools and base dependencies are installed
    ########################################################################
    run_command(
        "sudo apt update -y && sudo apt install -y git build-essential cmake libusb-1.0-0-dev",
        "Installing development tools (git, build-essential, cmake, libusb)",
        exit_on_failure=True
    )

    ########################################################################
    # 2. Install RTL-SDR Tools (for the NESDR)
    ########################################################################
    run_command(
        "sudo apt install -y rtl-sdr",
        "Installing RTL-SDR tools",
        exit_on_failure=True
    )

    ########################################################################
    # 3. Install HackRF Tools
    ########################################################################
    run_command(
        "sudo apt install -y hackrf",
        "Installing HackRF tools",
        exit_on_failure=True
    )

    ########################################################################
    # 4. Set up udev rules & permissions
    ########################################################################
    setup_udev_rules_and_permissions()
    print("[INFO] If this is your first time adding these rules, please log out or reboot before testing.")
    print("       However, we will attempt to test immediately. If the tests fail, reboot and try again.\n")

    ########################################################################
    # 5. Wait for and test the NESDR (RTL-SDR) device
    ########################################################################
    wait_for_device("NESDR (RTL-SDR)", DEVICE_IDS["NESDR (RTL-SDR)"])

    # Quick test (rtl_test) to confirm the device is recognized
    run_command(
        "rtl_test -t",
        "Verifying that NESDR is detected (rtl_test -t)"
    )

    # Capture a small sample (-n 5e6 = 5 million samples) so it exits on its own
    run_command(
        "rtl_sdr -f 109000000 -s 2048000 -g 50 -n 5000000 test_nesdr.bin",
        "Capturing a finite sample from NESDR (test_nesdr.bin)"
    )

    ########################################################################
    # 6. Wait for and test the HackRF device
    ########################################################################
    wait_for_device("HackRF", DEVICE_IDS["HackRF"])

    # Quick info check
    run_command(
        "hackrf_info",
        "Verifying HackRF device (hackrf_info)"
    )

    # Capture a small sample (-n 5e6 = 5 million samples) to exit automatically
    run_command(
        "hackrf_transfer -r test_hackrf.bin -f 109000000 -s 20000000 -n 5000000",
        "Capturing a finite sample from HackRF (test_hackrf.bin)"
    )

    ########################################################################
    # 7. Final updates & clean-up
    ########################################################################
    run_command(
        "sudo apt update -y && sudo apt upgrade -y",
        "Updating & upgrading the system"
    )
    run_command(
        "sudo apt autoremove -y && sudo apt autoclean -y",
        "Cleaning up unnecessary packages"
    )
    run_command(
        "sudo apt update -y && sudo apt upgrade -y",
        "Re-running updates to ensure all repositories are synced"
    )

    ########################################################################
    # 8. Reboot recommended
    ########################################################################
    print("\n[INFO] Stage 2 complete. A reboot (or log out/in) is recommended so group membership changes take effect.")
    reboot_choice = input("Would you like to reboot now? [y/N]: ").strip().lower()
    if reboot_choice == "y":
        print("[INFO] Rebooting the system...")
        run_command("sudo reboot", "Rebooting the Raspberry Pi")
    else:
        print("[INFO] Skipping reboot. You can reboot or log out/in manually later if needed.")

    print("\n========== STAGE 2 COMPLETE ==========")
    print("All required drivers, packages, and udev rules for NESDR & HackRF are set up.")
    print("Test files generated (if no errors): test_nesdr.bin, test_hackrf.bin.")
    print("If the device tests failed, please reboot/log out, replug devices, and try again.\n")

if __name__ == "__main__":
    main()
