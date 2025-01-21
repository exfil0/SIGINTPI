#!/usr/bin/env python3
"""
GSM Wizard (Headless) with All Fixes:

1) Kills leftover processes that might occupy port 4729.
2) Checks/install dependencies (python3, gr-gsm, tshark).
3) Lets user pick SDR device (rtl, hackrf, bladerf).
4) Runs grgsm_scanner, parses found ARFCNs.
5) Prompts user which ARFCN/freq to use.
6) Launches grgsm_livemon_headless (or fallback) in background on chosen freq.
7) Runs TShark line-buffered to display IMSI, MCC, MNC, TMSI, SMS text.
8) On exit (Ctrl+C from TShark), kills livemon.

If you see "Address already in use," this script tries to kill leftover processes.
If you see "nothing shows," ensure your phone is forced to 2G and actually re-attaches or sends SMS.

Usage:
  sudo python3 exfil0IMSI.py
"""

import subprocess
import sys
import re
import os
import time

def kill_leftover_processes():
    """
    If something is bound to port 4729, we kill it.
    That often happens if grgsm_livemon or grgsm_scanner
    didn't terminate cleanly. We'll check using lsof or netstat
    and attempt to kill automatically.
    """
    print("=== Checking for leftover processes on port 4729 ===")
    # netstat or lsof approach
    check_cmd = ["lsof", "-i", ":4729"]
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")

    # Example line might be:
    # COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
    # python3  1234 root   4u  IPv4  ...
    # We'll parse for the PID in the second column if lines > 1
    if len(lines) > 1 and "PID" not in lines[0]:
        # We see at least one leftover process
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                print(f"Killing leftover process PID={pid} that uses port 4729")
                try:
                    subprocess.run(["sudo", "kill", "-9", pid])
                except:
                    pass
    else:
        print("No leftover processes found or port 4729 is free.\n")

def check_or_install_deps():
    """
    Checks or installs:
      - python3
      - gr-gsm
      - tshark
    naive dpkg approach
    """
    print("=== Checking Dependencies ===")
    packages = ["python3", "gr-gsm", "tshark"]
    missing = []
    for pkg in packages:
        cmd = ["dpkg", "-s", pkg]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            missing.append(pkg)

    if missing:
        print(f"Missing packages: {missing}")
        ans = input("Install them now via apt-get? [y/N]: ").strip().lower()
        if ans == "y":
            subprocess.run(["sudo", "apt-get", "update"])
            install_cmd = ["sudo", "apt-get", "install", "-y"] + missing
            subprocess.run(install_cmd)
        else:
            print("User declined installation. Exiting.")
            sys.exit(1)
    else:
        print("All required packages found or installed.\n")

def pick_device():
    """
    Choose from [RTL-SDR, HackRF, BladeRF].
    Return device arg for gr-gsm commands: "rtl", "hackrf", "bladerf".
    """
    print("=== Select SDR Device ===")
    devices = [
        ("RTL-SDR",  "rtl"),
        ("HackRF",   "hackrf"),
        ("BladeRF",  "bladerf")
    ]
    for i, (name, dev) in enumerate(devices, start=1):
        print(f"{i}) {name}")

    choice = input("Enter number [1-3]: ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(devices):
            raise ValueError()
    except ValueError:
        print("Invalid choice. Exiting wizard.")
        sys.exit(1)

    selected = devices[idx]
    print(f"Selected: {selected[0]}\n")
    return selected[1]

def scan_for_channels(device_arg):
    """
    Run 'grgsm_scanner --args <device_arg>'.
    Parse lines for ARFCN/freq. If 'Address already in use',
    we exit or handle it. (We already killed leftover processes,
    so hopefully it's free.)
    """
    print("=== Scanning GSM Band ===")
    cmd = ["grgsm_scanner", "--args", device_arg]
    print("Command:", " ".join(cmd))
    print("(Press Ctrl+C to stop scanning early, partial results may appear.)\n")

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
                print("Found:", line_s)
    except KeyboardInterrupt:
        print("Scan interrupted by user.\n")

    process.wait()
    err = process.stderr.read().strip()
    if err:
        print("[grgsm_scanner stderr]:", err)
        # If we see "bind: Address already in use", user might have new leftover
        if "Address already in use" in err:
            print("Port 4729 is still in use or locked. Exiting.")
            sys.exit(1)

    return channels

def pick_channel(channels):
    """
    Let user pick a channel from discovered (arfcn, freq).
    Returns (arfcn, freq).
    """
    if not channels:
        print("\nNo channels found. Exiting wizard.")
        sys.exit(0)

    print("\n=== Available Channels Discovered ===")
    for i, (arfcn, freq) in enumerate(channels, start=1):
        print(f"{i}) ARFCN={arfcn}, Frequency={freq}")

    choice = input("Which channel? (Enter number): ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(channels):
            raise ValueError()
    except ValueError:
        print("Invalid selection. Exiting.")
        sys.exit(1)

    sel = channels[idx]
    print(f"\nSelected ARFCN={sel[0]}, freq={sel[1]}")
    return sel

def run_livemon_headless(device_arg, freq_str):
    """
    Try 'grgsm_livemon_headless'. If not found, fallback to 'grgsm_livemon -p' or another no-gui flag.
    freq_str e.g. "925.2M" -> convert "925.2e6".
    """
    freq_e = freq_str.replace("M", "e6").replace("G", "e9")

    cmd_name = "grgsm_livemon_headless"
    check_cmd = ["which", cmd_name]
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Warning: grgsm_livemon_headless not found, falling back to grgsm_livemon -p.")
        cmd_name = "grgsm_livemon"
        fallback_flags = ["-p"]
        cmd = [cmd_name, "--args", device_arg, "-f", freq_e] + fallback_flags
    else:
        cmd = [cmd_name, "--args", device_arg, "-f", freq_e]

    print("\n=== Starting grgsm_livemon (headless) in Background ===")
    print("Command:", " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setpgrp
    )
    time.sleep(2)
    print("grgsm_livemon started (headless). If signal is weak, no data might appear.\n")
    return proc

def run_tshark_capture():
    """
    TShark line-buffered for frame.time, e212.imsi, e212.mcc, e212.mnc, gsm_a.tmsi, gsm_sms.sms_text
    """
    print("=== Running TShark Capture ===\n")
    cmd = [
        "tshark",
        "-i", "lo",
        "-f", "port 4729 and not icmp and udp",
        "-l",  # line-buffered
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
            print("\nInterrupted TShark.")
            proc.terminate()

        proc.wait()
        err = proc.stderr.read().strip()
        if err:
            print("[TShark stderr]:", err)

def main():
    print("=== GSM Wizard (Headless) ===\n")

    # 1) Kill leftover processes on port 4729
    kill_leftover_processes()

    # 2) Check/install dependencies
    check_or_install_deps()

    # 3) Pick device
    dev_arg = pick_device()

    # 4) Scan channels
    channels = scan_for_channels(dev_arg)

    # 5) Pick channel
    (arfcn, freq) = pick_channel(channels)

    # 6) Launch livemon in background (headless)
    livemon_proc = run_livemon_headless(dev_arg, freq)

    # 7) TShark in foreground
    run_tshark_capture()

    # 8) Stop livemon
    print("\nStopping grgsm_livemon if still running.")
    try:
        livemon_proc.terminate()
    except:
        pass
    print("Wizard done. Exiting.\n")

if __name__ == "__main__":
    main()
