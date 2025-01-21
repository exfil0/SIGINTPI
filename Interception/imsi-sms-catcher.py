#!/usr/bin/env python3
"""
GSM Wizard (Headless) - Hacker-Style UI + MCC/MNC CSV Lookup

This script:
 - Terminates leftover processes on port 4729.
 - Checks/install dependencies (python3, gr-gsm, tshark).
 - Lets you pick SDR device.
 - Optionally provide known freq/ARFCN (e.g., '925.2M' or 'ARFCN=123'), else runs grgsm_scanner with extended fields.
 - Loads MCC/MNC from a huge CSV file 'mcc_mnc_list.csv' to display Country/Network in both scanner and TShark output.
 - Launches grgsm_livemon_headless in the background (or fallback).
 - Runs TShark in the foreground with line-buffered output.
 - Terminates livemon on exit.

Usage:
  sudo python3 exfil0IMSI.py
"""

import csv
import subprocess
import sys
import re
import os
import time

# ANSI color codes
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"


# ---------------------------------------------------------------------
# 1) CSV LOADER for MCC/MNC
# ---------------------------------------------------------------------
def load_mcc_mnc_csv(csv_filename):
    """
    Load a CSV file of MCC/MNC records, returning a dict keyed by (MCC, MNC).
    The CSV must have columns: Country,Network,MCC,MNC
    """
    lookup_dict = {}

    if not os.path.isfile(csv_filename):
        print(f"{RED}CSV file '{csv_filename}' not found!{RESET} Skipping MCC/MNC lookup.\n")
        return lookup_dict

    try:
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    country = row['Country'].strip()
                    network = row['Network'].strip()
                    mcc = row['MCC'].strip()
                    mnc = row['MNC'].strip()
                    lookup_dict[(mcc, mnc)] = (country, network)
                except KeyError:
                    continue  # missing columns, skip
    except Exception as e:
        print(f"{RED}Error reading CSV '{csv_filename}': {e}{RESET}\n")

    return lookup_dict


# ---------------------------------------------------------------------
# 2) Banner & Housekeeping
# ---------------------------------------------------------------------
def print_banner():
    """ Hacker-style ASCII banner. """
    print(f"{BOLD}{GREEN}")
    print("Evade the matrix. Sniff IMSI. Let's go...\n")
    print(RESET, end="")

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


# ---------------------------------------------------------------------
# 3) Device Selection
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# 4) ARFCN/Freq Parsing
# ---------------------------------------------------------------------
def parse_arfcn_or_freq(arfcn_str):
    """
    Parse a user input that may be 'ARFCN=123' or a frequency like '925.2M'.
    Returns (arfcn, freq_str).
    """
    arfcn_pattern = re.compile(r"^ARFCN=(\d+)$", re.IGNORECASE)
    freq_pattern = re.compile(r"^\d+(\.\d+)?[MG]$", re.IGNORECASE)

    match_arfcn = arfcn_pattern.match(arfcn_str)
    if match_arfcn:
        return match_arfcn.group(1), None

    match_freq = freq_pattern.match(arfcn_str)
    if match_freq:
        return None, arfcn_str

    return None, None

def convert_arfcn_to_freq(arfcn):
    """
    Simple, naive ARFCN -> Frequency conversion for demonstration.
    Adjust for a real GSM band plan as needed.
    """
    if arfcn.isdigit():
        freq_mhz = 900.0 + (int(arfcn) * 0.2)
        return f"{freq_mhz}M"
    else:
        raise ValueError(f"Invalid ARFCN: {arfcn}")


# ---------------------------------------------------------------------
# 5) Scanning with Extended Regex & CSV Lookup
# ---------------------------------------------------------------------
def scan_for_channels(device_arg, mcc_mnc_dict):
    """
    Runs 'grgsm_scanner --args <device_arg>' and parses lines including
    ARFCN, Freq, CID, LAC, MCC, MNC, Pwr. Also does a CSV lookup to display
    Country/Network if (MCC, MNC) is in mcc_mnc_dict.

    Returns a list of (arfcn, freq).
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

    # Matches lines like:
    #   Found: ARFCN:  975, Freq:  925.2M, CID: 38001, LAC: 30412, MCC: 655, MNC:  10, Pwr: -26
    regex = re.compile(
        r"ARFCN:\s+(\d+),\s+Freq:\s+([\d\.]+[MG]),\s+CID:\s+(\d+),"
        r"\s+LAC:\s+(\d+),\s+MCC:\s+(\d+),\s+MNC:\s+(\d+),\s+Pwr:\s+(-?\d+)"
    )

    try:
        for line in process.stdout:
            line_s = line.strip()
            match = regex.search(line_s)
            if match:
                arfcn = match.group(1)
                freq  = match.group(2)
                cid   = match.group(3)
                lac   = match.group(4)
                mcc   = match.group(5)
                mnc   = match.group(6)
                pwr   = match.group(7)

                channels.append((arfcn, freq))

                # Lookup in CSV
                country_str, network_str = ("", "")
                if (mcc, mnc) in mcc_mnc_dict:
                    country_str, network_str = mcc_mnc_dict[(mcc, mnc)]

                # Print extended info
                print(
                    f"{GREEN}Found:{RESET} "
                    f"ARFCN: {arfcn}, Freq: {freq}, CID: {cid}, LAC: {lac}, "
                    f"MCC: {mcc}, MNC: {mnc}, Pwr: {pwr}, "
                    f"[Country={country_str}, Network={network_str}]"
                )
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


def pick_frequency_or_scan(device_arg, mcc_mnc_dict):
    """
    Prompt for manual freq or ARFCN override. If blank, run scan_for_channels().
    Return the final frequency string.
    """
    print(f"{GREEN}>>> Frequency/ARFCN override (optional){RESET}")
    print("If you already know the frequency or ARFCN, enter it now (e.g., '925.2M' or 'ARFCN=123').")
    print("Press Enter to skip and perform a full scan.\n")

    user_input = input("Manual frequency/ARFCN (blank for scan): ").strip()

    if not user_input:
        # No manual input -> scanning
        channels = scan_for_channels(device_arg, mcc_mnc_dict)
        arfcn, freq_found = pick_channel(channels)
        return freq_found

    # parse
    user_arfcn, user_freq = parse_arfcn_or_freq(user_input)
    if user_arfcn is None and user_freq is None:
        print(f"{RED}Invalid frequency/ARFCN format! Exiting.{RESET}")
        sys.exit(1)

    if user_arfcn:
        try:
            freq_str = convert_arfcn_to_freq(user_arfcn)
            print(f"{GREEN}Using ARFCN={user_arfcn}, frequency={freq_str}{RESET}\n")
            return freq_str
        except ValueError as ex:
            print(f"{RED}{ex}{RESET}")
            sys.exit(1)
    else:
        print(f"{GREEN}Using provided frequency={user_freq}{RESET}\n")
        return user_freq


# ---------------------------------------------------------------------
# 6) grgsm_livemon
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# 7) TShark + CSV Lookup
# ---------------------------------------------------------------------
def parse_tshark_csv_line(tshark_line):
    """
    Parse a CSV line from TShark using Python's csv module.
    """
    import io
    reader = csv.reader(io.StringIO(tshark_line), quotechar='"', delimiter=',')
    for row in reader:
        return row
    return []


def run_tshark_capture(mcc_mnc_dict):
    """
    TShark line-buffered capturing IMSI, MCC, MNC, TMSI, LAC, SMS, IMEI, IMEISV.
    Append country/network if MCC/MNC found in mcc_mnc_dict.
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
            # Print header with appended columns
            header_line = proc.stdout.readline().rstrip('\n')
            if header_line:
                print(f"{header_line},\"Country\",\"Network\"")

            try:
                for line in proc.stdout:
                    line_str = line.strip('\n')
                    if not line_str:
                        continue

                    csv_fields = parse_tshark_csv_line(line_str)
                    # Indices:
                    # 0: frame.time
                    # 1: e212.imsi
                    # 2: e212.mcc
                    # 3: e212.mnc
                    # 4: gsm_a.tmsi
                    # 5: gsm_a.lac
                    # 6: gsm_sms.sms_text
                    # 7: gsm_a.imei
                    # 8: gsm_a.imeisv

                    mcc_val = csv_fields[2] if len(csv_fields) > 2 else ""
                    mnc_val = csv_fields[3] if len(csv_fields) > 3 else ""

                    country_str = ""
                    network_str = ""

                    if mcc_val and mnc_val and (mcc_val, mnc_val) in mcc_mnc_dict:
                        country_str, network_str = mcc_mnc_dict[(mcc_val, mnc_val)]

                    # Print original line + appended CSV
                    print(f"{line_str},\"{country_str}\",\"{network_str}\"")

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


# ---------------------------------------------------------------------
# 8) Main
# ---------------------------------------------------------------------
def main():
    # 1) Banner
    print_banner()

    # 2) Kill leftover processes
    kill_leftover_processes()

    # 3) Check dependencies
    check_or_install_deps()

    # 4) Pick device
    dev_arg = pick_device()

    # 5) Load MCC/MNC CSV
    mcc_mnc_dict = load_mcc_mnc_csv("mcc_mnc_list.csv")  # Adjust if CSV is named differently

    # 6) Pick frequency or do scanning
    freq_str = pick_frequency_or_scan(dev_arg, mcc_mnc_dict)

    # 7) Launch grgsm_livemon
    livemon_proc = run_livemon_headless(dev_arg, freq_str)

    # 8) Run TShark capture
    run_tshark_capture(mcc_mnc_dict)

    # 9) Kill livemon
    print(f"{RED}\nTerminating grgsm_livemon...{RESET}")
    try:
        livemon_proc.terminate()
    except Exception:
        pass

    print(f"{GREEN}All done. Stay safe out there!{RESET}\n")


if __name__ == "__main__":
    main()
