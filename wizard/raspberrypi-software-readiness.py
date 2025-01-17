import subprocess
import sys
import time

def run_command(command, description=None, exit_on_failure=False, has_retried=False):
    """
    Run a shell command and optionally exit if the command fails.

    If we see 'dpkg returned an error code (1)', we:
      1) Purge xtrx-dkms
      2) Attempt standard 'fix-broken install' & 'dpkg --configure -a'
      3) Retry the original command once.

    :param command: The shell command to run (string).
    :param description: Text describing the command (string).
    :param exit_on_failure: If True, exit the script if this command fails eventually.
    :param has_retried: Internal flag to prevent infinite recursion. If True, we won't retry again.
    """
    desc = description or command
    print(f"\n[+] {desc}")
    try:
        # Attempt to run the command
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

        # If dpkg error code (1) and we haven't retried yet, attempt to fix
        if "dpkg returned an error code (1)" in error_msg.lower() and not has_retried:
            print("[WARN] 'dpkg returned an error code (1)'. Attempting to purge xtrx-dkms and fix broken packages.")

            # 1) Remove xtrx-dkms forcibly
            remove_xtrx_dkms()

            # 2) Attempt standard fix steps
            attempt_fix_broken_install()

            # 3) Retry the original command once
            print(f"[INFO] Retrying command: {desc}")
            run_command(command, description=desc, exit_on_failure=exit_on_failure, has_retried=True)
            return

        if exit_on_failure:
            sys.exit(1)


def remove_xtrx_dkms():
    """
    Force-remove xtrx-dkms if it is blocking dpkg from succeeding.
    """
    print("[INFO] Removing xtrx-dkms package via 'apt-get remove --purge -y xtrx-dkms' ...")
    subprocess.run("sudo apt-get remove --purge -y xtrx-dkms", shell=True, check=False)


def attempt_fix_broken_install():
    """
    Attempts to fix a broken dpkg/apt state by running:
      1) sudo apt-get --fix-broken install -y
      2) sudo dpkg --configure -a
    """
    fix_cmds = [
        "sudo apt-get --fix-broken install -y",
        "sudo dpkg --configure -a"
    ]
    for cmd in fix_cmds:
        print(f"[INFO] Running fix command: {cmd}")
        subprocess.run(cmd, shell=True, check=False, text=True)


def prompt_desktop_test(app_name, cli_command=None):
    """
    Prompt the user to verify an application from the desktop or CLI.
    Optionally display a CLI command the user can run.
    """
    print(f"\n[TEST] Please launch '{app_name}' from the Raspberry Pi desktop environment.")
    if cli_command:
        print(f"       Or run this command in a desktop terminal: {cli_command}")
    input("       Once you've tested it and closed it, press ENTER to continue...")


def prompt_confirmation(message):
    """
    Prompt the user for a Y/N confirmation. Return True if user typed 'y', else False.
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
        "sudo apt-get update -y && sudo apt-get install -y gnuradio",
        "Installing GNU Radio",
        exit_on_failure=True
    )
    prompt_desktop_test("GNU Radio Companion", "gnuradio-companion")

    ########################################################################
    # 2. Install gr-osmosdr
    ########################################################################
    print("\n[INFO] Installing gr-osmosdr (may show xtrx-dkms errors; usually harmless).")
    run_command(
        "sudo apt-get install -y gr-osmosdr",
        "Installing gr-osmosdr"
    )

    ########################################################################
    # 3. Install gqrx-sdr
    ########################################################################
    print("\n[INFO] Installing gqrx-sdr (may show xtrx-dkms errors; usually harmless).")
    run_command(
        "sudo apt-get install -y gqrx-sdr",
        "Installing gqrx-sdr"
    )
    prompt_desktop_test("GQRX", "gqrx")

    ########################################################################
    # 4. Update & Upgrade, then Cleanup
    ########################################################################
    run_command(
        "sudo apt-get update -y && sudo apt-get upgrade -y",
        "Updating & upgrading the system"
    )
    run_command(
        "sudo apt-get autoremove -y && sudo apt-get autoclean -y",
        "Cleaning up unnecessary packages"
    )
    run_command(
        "sudo apt-get update -y && sudo apt-get upgrade -y",
        "Re-running updates to ensure repositories are synced"
    )

    ########################################################################
    # 5. Install GR-GSM
    ########################################################################
    run_command(
        "sudo apt-get install -y gr-gsm",
        "Installing GR-GSM"
    )
    print("\n[INFO] To test GR-GSM, you'll run `grgsm_livemon -f 950400000` from a desktop terminal.")
    prompt_desktop_test("grgsm_livemon", "grgsm_livemon -f 950400000")

    ########################################################################
    # 6. Install Kalibrate-RTL
    ########################################################################
    print("\n[INFO] Installing dependencies and building Kalibrate-RTL from source.")

    # Install build dependencies
    run_command(
        "sudo apt-get install -y git cmake build-essential libtool autoconf automake rtl-sdr pkg-config libfftw3-dev",
        "Installing dependencies for Kalibrate-RTL",
        exit_on_failure=True
    )
    run_command(
        "git clone https://github.com/steve-m/kalibrate-rtl.git",
        "Cloning Kalibrate-RTL repository"
    )
    run_command(
        "cd kalibrate-rtl",
        "Entering kalibrate-rtl directory"
    )

    # Install librtlsdr-dev
    run_command(
        "sudo apt-get install -y librtlsdr-dev",
        "Installing librtlsdr-dev"
    )

    # Build & install
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
    hackrf_rule = 'SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTR{idProduct}=="6089", MODE="0666", GROUP="plugdev"'
    rule_command = f'echo \'{hackrf_rule}\' | sudo tee /etc/udev/rules.d/52-hackrf.rules'
    run_command(rule_command, "Creating /etc/udev/rules.d/52-hackrf.rules")

    run_command(
        "sudo udevadm control --reload-rules && sudo udevadm trigger",
        "Reloading udev rules"
    )

    ########################################################################
    # 8. Add user to plugdev group
    ########################################################################
    user_proc = subprocess.run("echo $USER", shell=True, stdout=subprocess.PIPE, text=True)
    current_user = user_proc.stdout.strip() or "pi"

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
        print("[INFO] Assuming hackrf_info works fine as non-root.")
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
