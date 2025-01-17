import subprocess
import sys
import time

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

def prompt_desktop_test(app_name, cli_command=None):
    """
    Prompt the user to verify an application from the desktop or CLI.
    Optionally display a CLI command the user can run.
    
    :param app_name: Name of the application or test (string).
    :param cli_command: Optional CLI command to display for the user.
    """
    print(f"\n[TEST] Please launch '{app_name}' from the Raspberry Pi desktop environment.")
    if cli_command:
        print(f"       Or run this command in a desktop terminal: {cli_command}")
    input("       Once you've tested it and closed it, press ENTER to continue...")

def prompt_confirmation(message):
    """
    Prompt the user for a Y/N confirmation. Return True if user typed 'y', else False.
    
    :param message: The prompt to display.
    :return: Boolean indicating whether user confirmed (y) or not.
    """
    response = input(f"\n{message} [y/N]: ").strip().lower()
    return (response == 'y')

def main():
    print("\n========== RASPBERRY PI 5 AND SOFTWARE READINESS (STAGE 2) ==========")
    print("This script installs and tests GNU Radio, GQRX, GR-GSM, Kalibrate-RTL, etc.\n")

    ########################################################################
    # 1. Install GNU Radio
    ########################################################################
    run_command(
        "sudo apt update -y && sudo apt install -y gnuradio",
        "Installing GNU Radio",
        exit_on_failure=True
    )
    # Prompt user to verify gnuradio-companion (GRC) from Desktop
    prompt_desktop_test("GNU Radio Companion", "gnuradio-companion")

    ########################################################################
    # 2. Install gr-osmosdr
    ########################################################################
    print("\n[INFO] Installing gr-osmosdr (may show xtrx-dkms errors; usually harmless).")
    run_command(
        "sudo apt install -y gr-osmosdr",
        "Installing gr-osmosdr"
    )

    ########################################################################
    # 3. Install gqrx-sdr
    ########################################################################
    print("\n[INFO] Installing gqrx-sdr (may show xtrx-dkms errors; usually harmless).")
    run_command(
        "sudo apt install -y gqrx-sdr",
        "Installing gqrx-sdr"
    )
    # Prompt user to test GQRX on the Desktop
    prompt_desktop_test("GQRX", "gqrx")

    ########################################################################
    # 4. Update & Upgrade, then Cleanup
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
        "Re-running updates to ensure repositories are synced"
    )

    ########################################################################
    # 5. Install GR-GSM
    ########################################################################
    run_command(
        "sudo apt install -y gr-gsm",
        "Installing GR-GSM"
    )
    # Prompt user to test grgsm_livemon from Desktop
    print("\n[INFO] To test GR-GSM, you'll run `grgsm_livemon -f 950400000` from a desktop terminal.")
    prompt_desktop_test("grgsm_livemon", "grgsm_livemon -f 950400000")

    ########################################################################
    # 6. Install Kalibrate-RTL
    ########################################################################
    print("\n[INFO] Installing dependencies and building Kalibrate-RTL from source.")
    
    # Install build dependencies
    run_command(
        "sudo apt install -y git cmake build-essential libtool autoconf automake rtl-sdr pkg-config libfftw3-dev",
        "Installing dependencies for Kalibrate-RTL",
        exit_on_failure=True
    )
    # Clone repo
    run_command(
        "git clone https://github.com/steve-m/kalibrate-rtl.git",
        "Cloning Kalibrate-RTL repository"
    )
    # Enter directory
    run_command(
        "cd kalibrate-rtl",
        "Entering kalibrate-rtl directory"
    )

    # Install librtlsdr-dev
    run_command(
        "sudo apt install -y librtlsdr-dev",
        "Installing librtlsdr-dev"
    )

    # Bootstrap, configure, make, install
    run_command(
        "cd kalibrate-rtl && ./bootstrap",
        "Running bootstrap in kalibrate-rtl"
    )
    run_command(
        "cd kalibrate-rtl && ./configure",
        "Configuring kalibrate-rtl"
    )
    run_command(
        "cd kalibrate-rtl && make",
        "Compiling kalibrate-rtl"
    )
    run_command(
        "cd kalibrate-rtl && sudo make install",
        "Installing kalibrate-rtl"
    )

    # Verify installation
    run_command(
        "kal --help",
        "Testing kalibrate-rtl (kal --help)"
    )

    # Optional quick test
    if prompt_confirmation("Would you like to run kal -s GSM900 now to scan for GSM900 frequencies?"):
        run_command(
            "kal -s GSM900",
            "Scanning GSM900 frequencies with kalibrate-rtl"
        )
    else:
        print("[INFO] Skipping kalibrate-rtl test scan.")

    ########################################################################
    # 7. Create new udev rule for HackRF
    ########################################################################
    print("\n[INFO] Creating udev rule for HackRF at /etc/udev/rules.d/52-hackrf.rules.")
    # We'll echo the rule instead of opening nano manually:
    hackrf_rule = 'SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", MODE="0666", GROUP="plugdev"'
    rule_command = f'echo \'{hackrf_rule}\' | sudo tee /etc/udev/rules.d/52-hackrf.rules'
    run_command(rule_command, "Creating /etc/udev/rules.d/52-hackrf.rules")

    # Reload & trigger udev
    run_command(
        "sudo udevadm control --reload-rules && sudo udevadm trigger",
        "Reloading udev rules"
    )

    ########################################################################
    # 8. Add user to plugdev group
    ########################################################################
    username_command = "echo $USER"
    user_proc = subprocess.run(username_command, shell=True, stdout=subprocess.PIPE, text=True)
    current_user = user_proc.stdout.strip()
    if not current_user:
        current_user = "pi"  # fallback, if somehow $USER wasn't set

    print(f"\n[INFO] Adding user '{current_user}' to 'plugdev' group for HackRF USB access.")
    run_command(
        f"sudo usermod -aG plugdev {current_user}",
        f"Adding '{current_user}' to plugdev group"
    )
    print("\n[WARNING] You must log out and log back in (or reboot) for group changes to take effect.\n")

    ########################################################################
    # 9. Prompt user to test hackrf_info without sudo
    ########################################################################
    print("[TEST] Once you’ve re-logged in (or after a reboot), you should run `hackrf_info` (no sudo).")
    hackrf_info_check = prompt_confirmation("Have you re-logged and tested hackrf_info yet?")
    if hackrf_info_check:
        print("[INFO] Assuming hackrf_info works fine for you as non-root.")
    else:
        print("[WARN] If hackrf_info did NOT work, you may need to reboot or log out/in again.")

    ########################################################################
    # 10. Run a test scan with HackRF + GR-GSM
    ########################################################################
    print("\n[INFO] You can run a GSM scan with HackRF using GR-GSM:")
    print("       grgsm_scanner --args=\"hackrf=0\" -b GSM900")
    test_scanner = prompt_confirmation("Would you like to run it now?")
    if test_scanner:
        run_command(
            "grgsm_scanner --args=\"hackrf=0\" -b GSM900",
            "Scanning GSM900 with HackRF + GR-GSM"
        )
    else:
        print("[INFO] Skipping HackRF + GR-GSM scan test for now.")

    ########################################################################
    # 11. Final Steps / Optional Reboot
    ########################################################################
    print("\n[INFO] Stage 2 software installation and tests completed!")
    do_reboot = prompt_confirmation("Would you like to reboot now?")
    if do_reboot:
        print("[INFO] Rebooting the system...")
        run_command("sudo reboot", "Rebooting")
    else:
        print("[INFO] Skipping reboot. Remember to log out and back in so group changes take effect.")
        print("You can manually reboot later if needed.\n")

    print("========== STAGE 2 COMPLETE ==========")
    print("GNU Radio, GQRX, GR-GSM, Kalibrate-RTL, and related tools are installed.")
    print("Use the scripts and commands above to confirm everything is working. Enjoy!")

if __name__ == "__main__":
    main()
