import subprocess
import sys
import time

# Common Vendor:Product IDs for RTL-SDR & HackRF
# Adjust if your specific dongles use different IDs.
DEVICE_IDS = {
    "NESDR (RTL-SDR)": ["0bda:2838", "0bda:2832"],  # Realtek chipsets
    "HackRF": ["1d50:6089"],                        # HackRF
}

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
    :param device_id_list: List of strings, each in the format 'vvvv:pppp' (hex).
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
    Continuously check for device presence via lsusb every 5 seconds.
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

def main():
    print("\n========== RASPBERRY PI 5 AND COMPONENTS READINESS (STAGE 2) ==========")
    print("This script installs drivers/packages and tests NESDR (RTL-SDR) & HackRF devices.\n")

    ########################################################################
    # 1. Ensure development tools and base dependencies are installed
    ########################################################################
    run_command(
        "sudo apt update -y && sudo apt install -y git build-essential cmake libusb-1.0-0-dev",
        "Installing development tools (git, build-essential, cmake, libusb)",
        exit_on_failure=True
    )

    ########################################################################
    # 2. Install RTL-SDR Tools (for the NESDR Smart)
    ########################################################################
    run_command(
        "sudo apt install -y rtl-sdr",
        "Installing RTL-SDR tools",
        exit_on_failure=True
    )

    ########################################################################
    # 3. Reboot recommended — but let's do it at the end for a single-run flow
    ########################################################################
    # You could prompt here, but we'll do it once after everything is set up.
    # If you want to forcibly reboot now, uncomment the section below:
    #
    # reboot_choice = input("Would you like to reboot now? [y/N]: ").strip().lower()
    # if reboot_choice == "y":
    #     print("[INFO] Rebooting the system...")
    #     run_command("sudo reboot", "Rebooting the Raspberry Pi")
    #     sys.exit(0)

    ########################################################################
    # 4. Wait for and test the NESDR (RTL-SDR) device
    ########################################################################
    wait_for_device("NESDR (RTL-SDR)", DEVICE_IDS["NESDR (RTL-SDR)"])

    # Quick test to see if device is recognized
    run_command(
        "rtl_test -t",
        "Verifying that NESDR is detected (rtl_test -t)"
    )

    # Optional: More thorough test capturing a small sample
    run_command(
        "rtl_sdr -f 109000000 -s 2048000 -g 50 test_nesdr.bin",
        "Capturing a sample from NESDR (test_nesdr.bin)"
    )

    ########################################################################
    # 5. Install HackRF tools
    ########################################################################
    run_command(
        "sudo apt install -y hackrf",
        "Installing HackRF tools",
        exit_on_failure=True
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

    # Optional: More thorough test capturing a small sample
    run_command(
        "hackrf_transfer -r test_hackrf.bin -f 109000000 -s 20000000",
        "Capturing a sample from HackRF (test_hackrf.bin)"
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
    print("\n[INFO] Stage 2 complete. A reboot is recommended.")
    reboot_choice = input("Would you like to reboot now? [y/N]: ").strip().lower()
    if reboot_choice == "y":
        print("[INFO] Rebooting the system...")
        run_command("sudo reboot", "Rebooting the Raspberry Pi")
    else:
        print("[INFO] Skipping reboot. You can reboot manually later if needed.")

    print("\n========== STAGE 2 COMPLETE ==========")
    print("All required drivers and packages for NESDR Smart & HackRF are installed.")
    print("Test files generated (if no errors): test_nesdr.bin, test_hackrf.bin.")
    print("Enjoy your Raspberry Pi 5 setup!\n")

if __name__ == "__main__":
    main()
