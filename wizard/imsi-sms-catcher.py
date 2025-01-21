#!/usr/bin/env python3
"""
GSM Wizard (Headless) - Hacker-Style UI

Enhanced Script:
 - Includes additional TShark fields for LAC, SMS, IMEI, IMEISV.
 - Terminates leftover processes on port 4729.
 - Checks/install dependencies (python3, gr-gsm, tshark).
 - Lets you pick SDR device.
 - Adds an option to provide a known frequency (e.g., "925.2M") or ARFCN (e.g., "ARFCN=123"), skipping scanner.
 - If no known frequency is provided, runs grgsm_scanner -> parses ARFCN/freq, user picks channel.
 - Launches grgsm_livemon_headless (or fallback) in background.
 - Runs TShark line-buffered in the foreground.
 - Terminates livemon on exit.

Usage:
  sudo python3 exfil0IMSI.py

Examples for manually entering frequency or ARFCN during script execution:
  - Frequency: 925.2M
  - ARFCN: ARFCN=123

If you see "Address already in use", port 4729 is locked.
If no lines appear, phone might not be forced to 2G or is quickly re-assigning TMSI.
"""

import subprocess
import sys
import re
import os
import time

# Hacker-ish ANSI codes (green text on black style).
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"


def print_banner():
    """Prints a hacker-style ASCII banner."""
    print(f"{BOLD}{GREEN}")
    print("Evade the matrix. Sniff IMSI. Let's go...\n")
    print(RESET, end="")  # Reset style for the rest of the output


def kill_leftover_processes():
    """
    Kills leftover processes that bind to port 4729.
    """
    print(f"{GREEN}>>> Checking for leftover processes on port 4729...{RESET}")
    check_cmd = ["lsof", "-i", ":4729"]
    try:
        result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print(f"{RED}lsof not found; cannot check leftover processes. Skipping...{RESET}")
        return

    lines = result.stdout.strip().split("\n")

    # If lsof output has at least one line of actual usage, first line is typically a header with "PID"
    if len(lines) > 1 and "PID" in lines[0]:
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                print(f"{RED}Killing leftover process PID={pid} using port 4729!{RESET}")
                subprocess.run(["sudo", "kill", "-9", pid], check=False)
        print()
    else:
        print("No leftover processes found.\n")


def check_or_install_deps():
    """
    Checks or installs python3, gr-gsm, tshark.
    """
    print(f"{GREEN}>>> Checking Dependencies...{RESET}")
    packages = ["python3", "gr-gsm", "tshark"]
    missing = []

    for pkg in packages:
        cmd = ["dpkg", "-s", pkg]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            missing.append(pkg)

    if missing:
        print(f"{RED}Missing packages:{RESET} {missing}")
        ans = input(f"{BOLD}Install them now via apt-get? [y/N]: {RESET}").strip().lower()
        if ans == "y":
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            install_cmd = ["sudo", "apt-get", "install", "-y"] + missing
            subprocess.run(install_cmd, check=False)
        else:
            print("User declined installation. Exiting.\n")
            sys.exit(1)
    else:
        print("All required packages found!\n")


def pick_device():
    """
    User picks device from [RTL-SDR, HackRF, BladeRF].
    Returns dev arg: "rtl", "hackrf", "bladerf".
    """
    print(f"{GREEN}>>> Choose your weapon (SDR Device){RESET}")
    devices = [
        ("RTL-SDR",  "rtl"),
        ("HackRF",   "hackrf"),
        ("BladeRF",  "bladerf")
    ]
    for i, (name, dev) in enumerate(devices, start=1):
        print(f"{i}) {name}")

    choice = input("Pick device [1-3]: ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(devices):
            raise ValueError()
    except ValueError:
        print("Invalid device choice. Exiting.\n")
        sys.exit(1)

    selected = devices[idx]
    print(f"{GREEN}Device chosen:{RESET} {selected[0]}\n")
    return selected[1]


def parse_arfcn_or_freq(arfcn_str):
    """
    Parse a user input that may be 'ARFCN=123' or a frequency like '925.2M'.
    Returns:
      (arfcn, freq_str)
      - arfcn: str or None
      - freq_str: str or None
    """
    arfcn_pattern = re.compile(r"^ARFCN=(\d+)$", re.IGNORECASE)
    freq_pattern = re.compile(r"^\d+(\.\d+)?[MG]$", re.IGNORECASE)

    # Check if input matches "ARFCN=<number>"
    match_arfcn = arfcn_pattern.match(arfcn_str)
    if match_arfcn:
        return match_arfcn.group(1), None

    # Check if input matches a frequency pattern (like '925.2M' or '1.8G')
    match_freq = freq_pattern.match(arfcn_str)
    if match_freq:
        return None, arfcn_str

    # If nothing matches, return (None, None)
    return None, None


def convert_arfcn_to_freq(arfcn):
    """
    For simplicity, we won't implement a real ARFCN->Freq map here.
    In real usage, you'd need the specific GSM band plan.

    This function returns a dummy freq string or raises an error if unknown.
    """
    # Hard-coded example or any simple mapping (for demonstration only).
    # In practice, different ARFCNs map to different bands/frequencies.
    # E.g., ARFCN 123 might correspond to 935.6M in certain bands, etc.
    # Please adjust as needed for your actual environment/band plan.
    if arfcn.isdigit():
        # Just a naive example offset: ARFCN * 0.2 + 900
        freq_mhz = 900.0 + (int(arfcn) * 0.2)
        return f"{freq_mhz}M"
    else:
        raise ValueError(f"Invalid ARFCN: {arfcn}")


def pick_frequency_or_scan(device_arg):
    """
    Prompts the user to optionally enter a known frequency or ARFCN.
    If provided, skip scanning. Otherwise, proceed with scanning.
    Returns: freq_str in the format recognized by grgsm_livemon_headless.
    """
    print(f"{GREEN}>>> Frequency/ARFCN override (optional){RESET}")
    print("If you already know the frequency or ARFCN, enter it now (e.g., '925.2M' or 'ARFCN=123').")
    print("Press Enter to skip and perform a full scan.\n")

    user_input = input("Manual frequency/ARFCN (blank for scan): ").strip()

    if not user_input:
        # No manual input, do scanning
        channels = scan_for_channels(device_arg)
        arfcn, freq_found = pick_channel(channels)  # pick_channel returns (arfcn, freq)
        return freq_found

    # If we have user input, parse it
    user_arfcn, user_freq = parse_arfcn_or_freq(user_input)
    if user_arfcn is None and user_freq is None:
        print(f"{RED}Invalid frequency/ARFCN format! Exiting.{RESET}")
        sys.exit(1)

    if user_arfcn:
        # Convert ARFCN to frequency string
        try:
            freq_str = convert_arfcn_to_freq(user_arfcn)
            print(f"{GREEN}Using ARFCN={user_arfcn}, frequency={freq_str}{RESET}\n")
            return freq_str
        except ValueError as ex:
            print(f"{RED}{ex}{RESET}")
            sys.exit(1)
    else:
        # We have a direct frequency
        print(f"{GREEN}Using provided frequency={user_freq}{RESET}\n")
        return user_freq


def scan_for_channels(device_arg):
    """
    Runs 'grgsm_scanner --args <device_arg>'.
    Parse lines for ARFCN/freq.
    """
    print(f"{GREEN}>>> Scanning GSM Band...{RESET}")
    cmd = ["grgsm_scanner", "--args", device_arg]
    print(f"Command: {' '.join(cmd)}")
    print("(Ctrl+C to abort scanning early)\n")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        print(f"{RED}grgsm_scanner not found!{RESET} Is gr-gsm installed properly?")
        sys.exit(1)

    channels = []
    regex = re.compile(r"ARFCN:\s+(\d+),\s+Freq:\s+([\d\.]+[MG])")

    try:
        for line in process.stdout:
            line_s = line.strip()
            match = regex.search(line_s)
            if match:
                arfcn = match.group(1)
                freq  = match.group(2)
                channels.append((arfcn, freq))
                print(f"{GREEN}Found:{RESET} {line_s}")
    except KeyboardInterrupt:
        print("Scan aborted by user.\n")

    process.wait()
    err = process.stderr.read().strip()
    if err:
        print(f"{RED}[grgsm_scanner stderr]:{RESET} {err}")
        if "Address already in use" in err:
            print("Port 4729 locked. Exiting.\n")
            sys.exit(1)

    return channels


def pick_channel(channels):
    """
    Prompt user to pick from discovered ARFCN/freq.
    Returns (arfcn, freq).
    """
    if not channels:
        print("No channels found. Exiting.\n")
        sys.exit(0)

    print(f"{GREEN}\n>>> ARFCNs discovered:{RESET}")
    for i, (arfcn, freq) in enumerate(channels, start=1):
        print(f"{i}) ARFCN={arfcn}, Frequency={freq}")

    choice = input("Which channel? ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(channels):
            raise ValueError()
    except ValueError:
        print("Invalid channel selection. Exiting.\n")
        sys.exit(1)

    sel = channels[idx]
    print(f"{GREEN}Selected ARFCN={sel[0]}, freq={sel[1]}{RESET}\n")
    return sel


def run_livemon_headless(device_arg, freq_str):
    """
    Try 'grgsm_livemon_headless' or fallback to 'grgsm_livemon -p'.
    freq_str "925.2M" -> "925.2e6".
    """
    freq_e = freq_str.replace("M", "e6").replace("G", "e9")

    cmd_name = "grgsm_livemon_headless"
    check_cmd = ["which", cmd_name]
    result = subprocess.run(check_cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        print(f"{RED}grgsm_livemon_headless not found!{RESET} Falling back to 'grgsm_livemon -p'.")
        cmd_name = "grgsm_livemon"
        fallback_flags = ["-p"]
        cmd = [cmd_name, "--args", device_arg, "-f", freq_e] + fallback_flags
    else:
        cmd = [cmd_name, "--args", device_arg, "-f", freq_e]

    print(f"{GREEN}>>> Starting grgsm_livemon (headless) in bg...{RESET}")
    print("Command:", " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp  # run in its own process group
        )
    except FileNotFoundError:
        print(f"{RED}{cmd_name} not found!{RESET} Aborting.")
        sys.exit(1)

    time.sleep(2)
    print("grgsm_livemon launched. If signal is poor, no data might appear.\n")
    return proc


def run_tshark_capture():
    """
    TShark line-buffered capturing IMSI, MCC, MNC, TMSI, SMS, LAC, IMEI, IMEISV.
    """
    print(f"{GREEN}>>> Launching TShark...{RESET}\n")
    cmd = [
        "tshark",
        "-i", "lo",
        "-f", "port 4729 and not icmp and udp",
        "-l",
        "-Y", "(e212.imsi or e212.mcc or e212.mnc or gsm_a.tmsi or gsm_a.lac or gsm_sms.sms_text or gsm_a.imei or gsm_a.imeisv)",
        "-T", "fields",
        "-e", "frame.time",
        "-e", "e212.imsi",
        "-e", "e212.mcc",
        "-e", "e212.mnc",
        "-e", "gsm_a.tmsi",
        "-e", "gsm_a.lac",
        "-e", "gsm_sms.sms_text",
        "-e", "gsm_a.imei",
        "-e", "gsm_a.imeisv",
        "-E", "header=y",
        "-E", "separator=,",
        "-E", "quote=d"
    ]
    print("Command:", " ".join(cmd), "\n")

    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1) as proc:
            try:
                for line in proc.stdout:
                    print(line, end='')
            except KeyboardInterrupt:
                print(f"{RED}\nTShark interrupted by user.{RESET}")
                proc.terminate()

            proc.wait()
            err = proc.stderr.read().strip()
            if err:
                print(f"{RED}[TShark stderr]:{RESET} {err}")

    except FileNotFoundError:
        print(f"{RED}tshark not found!{RESET} Is it installed and in your PATH?")
        sys.exit(1)


def main():
    # 1) Print Banner
    print_banner()

    # 2) Kill leftover processes
    kill_leftover_processes()

    # 3) Check dependencies
    check_or_install_deps()

    # 4) Choose device
    dev_arg = pick_device()

    # 5) Prompt for known frequency/ARFCN or do scanning
    freq_str = pick_frequency_or_scan(dev_arg)

    # 6) Launch livemon headless
    livemon_proc = run_livemon_headless(dev_arg, freq_str)

    # 7) Run TShark in foreground
    run_tshark_capture()

    # 8) Kill livemon
    print(f"{RED}\nTerminating grgsm_livemon...{RESET}")
    try:
        livemon_proc.terminate()
    except Exception:
        pass

    print(f"{GREEN}All done. Stay safe out there!{RESET}\n")


if __name__ == "__main__":
    main()
