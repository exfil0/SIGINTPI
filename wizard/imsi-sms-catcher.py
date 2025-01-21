#!/usr/bin/env python3
"""
Improved GSM capturer script that:

1. Runs TShark on loopback (lo) to capture GSMTAP packets on port 4729.
2. Uses '-l' line-buffering so TShark flushes each line immediately.
3. Outputs CSV columns for:
   - frame.time
   - e212.imsi
   - e212.mcc
   - e212.mnc
   - gsm_a.tmsi
   - gsm_sms.sms_text

If "nothing shows," possible reasons:
- No phone triggered IMSI or SMS traffic yet.
- grgsm_livemon not running or tuned incorrectly.
- The TShark filter is too narrow.

Usage:
  sudo python3 exfil0IMSI.py
  (In another terminal: grgsm_livemon --args "bladerf" -f <frequency>)
"""

import subprocess
import sys

def main():
    # TShark command without 'sudo' (we assume you run this script with sudo if needed)
    tshark_cmd = [
        "tshark",
        "-i", "lo",
        "-f", "port 4729 and not icmp and udp",
        # '-l' ensures line-buffered output, so we see packets in real time
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

    print("=== GSM Capturer ===", file=sys.stderr)
    print("Command:", " ".join(tshark_cmd), file=sys.stderr)
    print("Starting TShark. Press Ctrl+C to stop.\n", file=sys.stderr)

    # Run TShark in a subprocess
    with subprocess.Popen(
            tshark_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        ) as proc:

        try:
            # Read CSV lines as they are produced
            for line in proc.stdout:
                # Print them to our console (or store them if desired)
                print(line, end='')
        except KeyboardInterrupt:
            print("\nInterrupted by user (Ctrl+C).", file=sys.stderr)

        proc.wait()

        # Show any final stderr messages TShark produced
        err_output = proc.stderr.read().strip()
        if err_output:
            print("[TShark stderr]:", err_output, file=sys.stderr)

if __name__ == "__main__":
    main()
